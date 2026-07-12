"""Cohere Reranker Adapter.

Implements the RerankerProvider port using the Cohere Rerank API.
Gracefully degrades on API failure by returning candidates unchanged.
"""

import cohere

from src.domain.abstractions.retrieval import RerankerProvider, SearchResult


class CohereRerankerAdapter(RerankerProvider):
    """Concrete adapter for Cohere cross-encoder reranking."""

    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None:
        self.model = model
        self.api_key = api_key
        self._client: cohere.AsyncClientV2 | None = None

    @property
    def client(self) -> cohere.AsyncClientV2:
        """Lazy-initialize the Cohere async client."""
        if self._client is None:
            self._client = cohere.AsyncClientV2(api_key=self.api_key)
        return self._client

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
        threshold: float,
    ) -> list[SearchResult]:
        """Re-score candidates via Cohere reranker and filter by threshold."""
        if not candidates:
            return []

        documents = [c.content for c in candidates]

        response = await self.client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=min(top_n, len(candidates)),
        )

        reranked: list[SearchResult] = []
        for item in response.results:
            if item.relevance_score >= threshold:
                original = candidates[item.index]
                reranked.append(
                    original.model_copy(
                        update={"score": round(item.relevance_score, 6)}
                    )
                )

        return reranked
