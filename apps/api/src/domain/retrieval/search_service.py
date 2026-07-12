"""Hybrid Search Service.

Orchestrates parallel dense vector and sparse keyword searches, merges results
using Reciprocal Rank Fusion (RRF), and optionally refines via cross-encoder
reranking. Depends only on domain abstractions — no infrastructure imports.
"""

import time
from src.domain.abstractions.retrieval import (
    SearchQuery,
    SearchResult,
    SearchResponse,
    SearchMeta,
    VectorSearchProvider,
    KeywordSearchProvider,
    EmbeddingProvider,
    RerankerProvider,
)


class HybridSearchService:
    """Core retrieval engine implementing hybrid search with RRF fusion."""

    def __init__(
        self,
        vector_search: VectorSearchProvider,
        keyword_search: KeywordSearchProvider,
        embedder: EmbeddingProvider,
        reranker: RerankerProvider,
    ) -> None:
        self.vector_search = vector_search
        self.keyword_search = keyword_search
        self.embedder = embedder
        self.reranker = reranker

    async def search(self, query: SearchQuery) -> SearchResponse:
        """Execute the full hybrid search pipeline."""
        start_time = time.monotonic()

        # 1. Generate query embedding
        query_embedding = await self.embedder.embed_text(query.query)

        # 2. Fan-out: parallel dense + sparse searches
        vector_results, keyword_results = await self._fan_out_search(
            query, query_embedding
        )

        # 3. Determine strategy and fuse results
        strategy = self._determine_strategy(
            query, vector_results, keyword_results
        )
        fused = self._fuse_results(
            query, strategy, vector_results, keyword_results
        )

        # 4. Optional reranking pass
        if query.enable_reranking and fused:
            fused, strategy = await self._apply_reranking(
                query, fused, strategy
            )

        # 5. Trim to requested limit
        final_results = fused[: query.top_k]

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return SearchResponse(
            query=query.query,
            results=final_results,
            search_meta=SearchMeta(
                strategy=strategy,
                total_candidates=len(vector_results) + len(keyword_results),
                returned_results=len(final_results),
                duration_ms=round(elapsed_ms, 2),
            ),
        )

    async def _fan_out_search(
        self,
        query: SearchQuery,
        query_embedding: list[float],
    ) -> tuple[list[SearchResult], list[SearchResult]]:
        """Execute vector and keyword searches with graceful degradation."""
        vector_results: list[SearchResult] = []
        keyword_results: list[SearchResult] = []

        # Dense vector search
        try:
            vector_results = await self.vector_search.search_similar(
                tenant_id=query.tenant_id,
                embedding=query_embedding,
                top_k=query.top_k,
                filters=query.filters,
            )
        except Exception:
            pass  # Graceful degradation: proceed with keyword-only

        # Sparse keyword search (only if hybrid enabled)
        if query.enable_hybrid:
            try:
                keyword_results = await self.keyword_search.search_keywords(
                    tenant_id=query.tenant_id,
                    query_text=query.query,
                    top_k=query.top_k,
                    filters=query.filters,
                )
            except Exception:
                pass  # Graceful degradation: proceed with vector-only

        return vector_results, keyword_results

    def _determine_strategy(
        self,
        query: SearchQuery,
        vector_results: list[SearchResult],
        keyword_results: list[SearchResult],
    ) -> str:
        """Label the search strategy based on which legs succeeded."""
        if not query.enable_hybrid:
            return "vector_only"
        if vector_results and keyword_results:
            return "hybrid_rrf"
        if vector_results:
            return "vector_only_degraded"
        if keyword_results:
            return "keyword_only_degraded"
        return "no_results"

    def _fuse_results(
        self,
        query: SearchQuery,
        strategy: str,
        vector_results: list[SearchResult],
        keyword_results: list[SearchResult],
    ) -> list[SearchResult]:
        """Merge result sets using the appropriate fusion strategy."""
        if strategy == "hybrid_rrf":
            return self._fuse_rrf(
                vector_results, keyword_results, query.rrf_k
            )
        if strategy in ("vector_only", "vector_only_degraded"):
            return vector_results
        if strategy == "keyword_only_degraded":
            return keyword_results
        return []

    def _fuse_rrf(
        self,
        vector_results: list[SearchResult],
        keyword_results: list[SearchResult],
        rrf_k: int,
    ) -> list[SearchResult]:
        """Apply Reciprocal Rank Fusion across two ranked lists.

        RRF(d) = Σ  1 / (k + rank_r(d))  for each ranking r
        """
        scores: dict[str, float] = {}
        best_result: dict[str, SearchResult] = {}

        for rank, result in enumerate(vector_results):
            rrf_score = 1.0 / (rrf_k + rank + 1)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + rrf_score
            if result.chunk_id not in best_result:
                best_result[result.chunk_id] = result

        for rank, result in enumerate(keyword_results):
            rrf_score = 1.0 / (rrf_k + rank + 1)
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + rrf_score
            if result.chunk_id not in best_result:
                best_result[result.chunk_id] = result

        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

        return [
            best_result[cid].model_copy(update={"score": round(scores[cid], 6)})
            for cid in sorted_ids
        ]

    async def _apply_reranking(
        self,
        query: SearchQuery,
        candidates: list[SearchResult],
        strategy: str,
    ) -> tuple[list[SearchResult], str]:
        """Apply cross-encoder reranking with graceful fallback."""
        try:
            reranked = await self.reranker.rerank(
                query=query.query,
                candidates=candidates,
                top_n=query.top_k,
                threshold=query.reranking_threshold,
            )
            return reranked, strategy + "_reranked"
        except Exception:
            return candidates, strategy
