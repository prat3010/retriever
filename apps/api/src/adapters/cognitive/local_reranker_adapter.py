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
                    original = candidates[idx]
                    reranked.append(
                        original.model_copy(update={"score": round(score, 6)})
                    )
            return reranked if reranked else candidates[:top_n]
        except Exception:
            return candidates[:top_n]
