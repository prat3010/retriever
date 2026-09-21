"""Tests for Dual-Channel Full Corpus Retrieval (Dense HNSW + Sparse Keyword BM25/FTS)."""

from unittest.mock import AsyncMock

import pytest

from src.domain.abstractions.retrieval import SearchQuery, SearchResult
from src.domain.retrieval.search_service import HybridSearchService


@pytest.mark.asyncio
async def test_dual_channel_search_fan_out() -> None:
    """Verify enable_hybrid=True executes both vector and keyword search concurrently."""
    vec_mock = AsyncMock()
    kw_mock = AsyncMock()
    embedder_mock = AsyncMock()
    reranker_mock = AsyncMock()

    embedder_mock.embed_text = AsyncMock(return_value=[0.1] * 768)

    vec_results = [
        SearchResult(
            chunk_id="chk-v1",
            document_id="doc-1",
            content="Vector semantic candidate on PostgreSQL partitioning.",
            score=0.88,
        )
    ]
    kw_results = [
        SearchResult(
            chunk_id="chk-k1",
            document_id="doc-2",
            content="Keyword BM25 candidate with exact match on table partition syntax.",
            score=12.4,
        )
    ]

    vec_mock.search_similar = AsyncMock(return_value=vec_results)
    kw_mock.search_keywords = AsyncMock(return_value=kw_results)

    service = HybridSearchService(
        vector_search=vec_mock,
        keyword_search=kw_mock,
        embedder=embedder_mock,
        reranker=reranker_mock,
    )

    query = SearchQuery(
        tenant_id="tenant-dual-1",
        query="PostgreSQL table partition syntax",
        enable_hybrid=True,
        enable_reranking=False,
    )

    response = await service.search(query)

    # Both channels must have been called
    assert vec_mock.search_similar.called
    assert kw_mock.search_keywords.called

    # Results fused from both channels
    assert len(response.results) >= 2
    assert "hybrid" in response.search_meta.strategy


@pytest.mark.asyncio
async def test_dense_only_search_bypasses_keyword_channel() -> None:
    """Verify enable_hybrid=False and enable_bm25=False bypasses keyword search."""
    vec_mock = AsyncMock()
    kw_mock = AsyncMock()
    embedder_mock = AsyncMock()
    reranker_mock = AsyncMock()

    embedder_mock.embed_text = AsyncMock(return_value=[0.2] * 768)

    vec_results = [
        SearchResult(
            chunk_id="chk-v2",
            document_id="doc-3",
            content="Pure vector semantic search hit.",
            score=0.91,
        )
    ]
    vec_mock.search_similar = AsyncMock(return_value=vec_results)

    service = HybridSearchService(
        vector_search=vec_mock,
        keyword_search=kw_mock,
        embedder=embedder_mock,
        reranker=reranker_mock,
    )

    query = SearchQuery(
        tenant_id="tenant-dual-2",
        query="Semantic vector retrieval query",
        enable_hybrid=False,
        enable_bm25=False,
        enable_reranking=False,
    )

    response = await service.search(query)

    # Vector called, keyword bypassed
    assert vec_mock.search_similar.called
    assert not kw_mock.search_keywords.called

    assert len(response.results) == 1
    assert response.search_meta.strategy == "vector_only"
