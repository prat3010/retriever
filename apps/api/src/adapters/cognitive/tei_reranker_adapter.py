"""TEI (Text Embeddings Inference) Reranker Adapter.

Implements the RerankerProvider port using an external TEI or microservice HTTP endpoint.
Gracefully degrades on API or connection failure by returning original candidates.
"""

import logging
from typing import Any

import httpx

from src.domain.abstractions.retrieval import RerankerProvider, SearchResult

logger = logging.getLogger(__name__)


class TeiRerankerAdapter(RerankerProvider):
    """Concrete adapter for offloading cross-encoder reranking to a TEI microservice."""

    def __init__(
        self,
        endpoint_url: str,
        timeout_seconds: float = 5.0,
        api_key: str | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
        threshold: float,
    ) -> list[SearchResult]:
        """Re-score candidates via external TEI reranker HTTP endpoint."""
        if not candidates or not query:
            return candidates[:top_n]

        documents = [c.content for c in candidates]
        payload: dict[str, Any] = {
            "query": query,
            "texts": documents,
            "raw_scores": False,
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        target_url = (
            self.endpoint_url
            if self.endpoint_url.endswith("/rerank") or self.endpoint_url.endswith("/predict")
            else f"{self.endpoint_url}/rerank"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(target_url, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()

            # Parse TEI response format: [{"index": int, "score": float}, ...]
            results_data = data if isinstance(data, list) else data.get("results", [])
            reranked: list[SearchResult] = []

            for item in results_data:
                idx = item.get("index")
                score = float(item.get("score", 0.0))
                if idx is not None and 0 <= idx < len(candidates):
                    if score >= threshold:
                        original = candidates[idx]
                        reranked.append(
                            original.model_copy(update={"score": round(score, 6)})
                        )

            return reranked[:top_n] if reranked else candidates[:top_n]
        except Exception as err:
            logger.warning(
                f"TEI Reranker endpoint call failed ({err}). Falling back to local ColBERT MaxSim."
            )
            try:
                from src.domain.retrieval.colbert_engine import score_colbert_maxsim
                return score_colbert_maxsim(query, candidates, top_n=top_n, threshold=threshold)
            except Exception:
                return candidates[:top_n]
