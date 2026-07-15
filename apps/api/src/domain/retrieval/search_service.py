"""Hybrid Search Service.

Orchestrates parallel dense vector and sparse keyword searches, merges results
using Reciprocal Rank Fusion (RRF), and optionally refines via cross-encoder
reranking. Depends only on domain abstractions — no infrastructure imports.
"""

import time

from uuid import uuid4

from src.domain.abstractions.retrieval import (
    EmbeddingProvider,
    KeywordSearchProvider,
    MetadataFilter,
    RerankerProvider,
    SearchMeta,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SelfQueryProvider,
    VectorSearchProvider,
    SemanticCacheProvider,
)
from src.domain.abstractions.web_search import WebSearchProvider


class HybridSearchService:
    """Core retrieval engine implementing hybrid search with RRF fusion."""

    def __init__(
        self,
        vector_search: VectorSearchProvider,
        keyword_search: KeywordSearchProvider,
        embedder: EmbeddingProvider,
        reranker: RerankerProvider,
        cache_provider: SemanticCacheProvider = None,
        web_search: WebSearchProvider | None = None,
        self_query: SelfQueryProvider | None = None,
    ) -> None:
        self.vector_search = vector_search
        self.keyword_search = keyword_search
        self.embedder = embedder
        self.reranker = reranker
        self.cache_provider = cache_provider
        self.web_search = web_search
        self.self_query = self_query

    async def search(self, query: SearchQuery) -> SearchResponse:
        """Execute the full hybrid search pipeline."""
        start_time = time.monotonic()

        # 0. Self-query: parse NL query into structured filters
        if query.enable_self_query and self.self_query:
            parsed = await self._parse_self_query(query.query)
            query.filters = query.filters + parsed

        # 1. Generate query embedding
        query_embedding = await self.embedder.embed_text(query.query)

        # 2. Check semantic cache table if cache provider is set
        if self.cache_provider is not None:
            try:
                cached_results = await self.cache_provider.get_cached_search(query.tenant_id, query_embedding)
                if cached_results is not None:
                    return SearchResponse(
                        query=query.query,
                        results=cached_results,
                        search_meta=SearchMeta(
                            strategy="semantic_cache_hit",
                            total_candidates=len(cached_results),
                            returned_results=len(cached_results),
                            duration_ms=0.0
                        )
                    )
            except Exception:
                pass

        # 3. Fan-out: parallel dense + sparse searches
        vector_results, keyword_results = await self._fan_out_search(
            query, query_embedding
        )

        # 4. Determine strategy and fuse results
        strategy = self._determine_strategy(
            query, vector_results, keyword_results
        )
        fused = self._fuse_results(
            query, strategy, vector_results, keyword_results
        )

        # 5. Optional reranking pass
        if query.enable_reranking and fused:
            fused, strategy = await self._apply_reranking(
                query, fused, strategy
            )

        # 6. Trim to requested limit
        final_results = fused[: query.top_k]

        # 7. Web search fallback if scores are low
        if (
            query.enable_web_search
            and self.web_search is not None
            and final_results
            and final_results[0].score < query.web_search_threshold
        ):
            final_results = await self._apply_web_search_fallback(query, final_results)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        response = SearchResponse(
            query=query.query,
            results=final_results,
            search_meta=SearchMeta(
                strategy=strategy,
                total_candidates=len(vector_results) + len(keyword_results),
                returned_results=len(final_results),
                duration_ms=round(elapsed_ms, 2),
            ),
        )

        # 7. Save results to semantic cache if cache provider is set
        if self.cache_provider is not None:
            try:
                await self.cache_provider.cache_search(
                    tenant_id=query.tenant_id,
                    query_text=query.query,
                    query_embedding=query_embedding,
                    results=response.results
                )
            except Exception:
                pass

        return response

    async def _apply_web_search_fallback(
        self,
        query: SearchQuery,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        try:
            web_results = await self.web_search.search(query.query, query.web_search_max_results)
            max_local = max(r.score for r in results)
            for i, wr in enumerate(web_results):
                results.append(SearchResult(
                    chunk_id=f"web_{uuid4().hex[:12]}",
                    document_id="__web__",
                    content=f"[Web: {wr.title}]({wr.url})\n{wr.content}",
                    score=max(0.001, max_local * (0.9 - i * 0.1)),
                ))
            results.sort(key=lambda r: r.score, reverse=True)
            return results[: query.top_k]
        except Exception:
            return results

    async def _parse_self_query(self, query: str) -> list[MetadataFilter]:
        try:
            return await self.self_query.parse_query(query)
        except Exception:
            return []

    async def _fan_out_search(
        self,
        query: SearchQuery,
        query_embedding: list[float],
    ) -> tuple[list[SearchResult], list[SearchResult]]:
        """Execute vector and keyword searches with graceful degradation."""
        vector_results: list[SearchResult] = []
        keyword_results: list[SearchResult] = []

        try:
            vector_results = await self.vector_search.search_similar(
                tenant_id=query.tenant_id,
                embedding=query_embedding,
                top_k=query.top_k,
                filters=query.filters,
                tags=query.tags,
            )
        except Exception:
            pass

        if query.enable_hybrid:
            try:
                keyword_results = await self.keyword_search.search_keywords(
                    tenant_id=query.tenant_id,
                    query_text=query.query,
                    top_k=query.top_k,
                    filters=query.filters,
                    tags=query.tags,
                )
            except Exception:
                pass

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
