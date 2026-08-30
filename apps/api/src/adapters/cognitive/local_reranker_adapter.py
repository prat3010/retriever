"""Local Cross-Encoder Reranker Adapter.

Implements the RerankerProvider port using local cross-encoder models via sentence-transformers.
Gracefully degrades on missing dependency or model load failure by returning candidates.
"""

import asyncio

from src.domain.abstractions.retrieval import RerankerProvider, SearchResult


class LocalRerankerAdapter(RerankerProvider):
    """Local cross-encoder reranker for Apple Silicon M4 / CPU offline execution."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self.model_name = model_name
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            self._initialized = True
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
            except Exception:
                self._model = None
        return self._model

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
        threshold: float,
    ) -> list[SearchResult]:
        """Re-score candidates via local cross-encoder model."""
        if not candidates:
            return []

        def _score_candidates() -> list[tuple[int, float]]:
            model = self._get_model()
            if model is None:
                return [(i, c.score) for i, c in enumerate(candidates)]

            pairs = [[query, c.content] for c in candidates]
            scores = model.predict(pairs)
            return list(enumerate([float(s) for s in scores]))

        try:
            scored_indices = await asyncio.to_thread(_score_candidates)
            scored_indices.sort(key=lambda x: x[1], reverse=True)

            reranked: list[SearchResult] = []
            for idx, score in scored_indices[:top_n]:
                if score >= threshold or score == candidates[idx].score:
                    reranked.append(
                        candidates[idx].model_copy(update={"score": round(score, 6)})
                    )
            return reranked if reranked else candidates[:top_n]
        except Exception:
            return candidates[:top_n]


class ColBertMaxSimRerankerAdapter(RerankerProvider):
    """Token-level late interaction MaxSim reranker adapter for fast sub-15ms candidate re-scoring."""

    def __init__(
        self,
        model_name: str = "colbert-ir/colbertv2.0",
        initial_weight: float = 0.4,
        maxsim_weight: float = 0.6,
    ) -> None:
        self.model_name = model_name
        self.initial_weight = initial_weight
        self.maxsim_weight = maxsim_weight

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
        threshold: float,
    ) -> list[SearchResult]:
        """Re-score candidates via ColBERT token-level MaxSim late interaction."""
        if not candidates or not query.strip():
            return candidates[:top_n]

        try:
            from src.domain.retrieval.colbert_engine import score_colbert_maxsim

            return await asyncio.to_thread(
                score_colbert_maxsim,
                query=query,
                candidates=candidates,
                top_n=top_n,
                threshold=threshold,
                initial_weight=self.initial_weight,
                maxsim_weight=self.maxsim_weight,
            )
        except Exception:
            return candidates[:top_n]

