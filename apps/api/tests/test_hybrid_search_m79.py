from unittest.mock import AsyncMock

import pytest

from src.domain.abstractions.retrieval import SearchResult
from src.domain.retrieval.search_service import HybridSearchService


@pytest.fixture
def mock_search_deps():
    vector_search = AsyncMock()
    keyword_search = AsyncMock()
    embedder = AsyncMock()
    reranker = AsyncMock()
    return vector_search, keyword_search, embedder, reranker


@pytest.mark.asyncio
async def test_convex_hybrid_fusion(mock_search_deps):
    vec_mock, kw_mock, embedder, reranker = mock_search_deps
    service = HybridSearchService(
        vector_search=vec_mock,
        keyword_search=kw_mock,
        embedder=embedder,
        reranker=reranker,
    )

    vec_results = [
        SearchResult(chunk_id="chunk-1", document_id="doc-1", content="dense hit 1", score=0.9),
        SearchResult(chunk_id="chunk-2", document_id="doc-2", content="dense hit 2", score=0.5),
    ]
    kw_results = [
        SearchResult(chunk_id="chunk-2", document_id="doc-2", content="dense hit 2", score=10.0),
        SearchResult(chunk_id="chunk-3", document_id="doc-3", content="sparse hit 3", score=8.0),
    ]

    # Test alpha = 1.0 (pure dense priority)
    fused_dense = service._fuse_convex_hybrid(vec_results, kw_results, alpha=1.0)
    assert fused_dense[0].chunk_id == "chunk-1"

    # Test alpha = 0.0 (pure sparse priority)
    fused_sparse = service._fuse_convex_hybrid(vec_results, kw_results, alpha=0.0)
    assert fused_sparse[0].chunk_id == "chunk-2"

    # Test alpha = 0.7 (convex mixture)
    fused_hybrid = service._fuse_convex_hybrid(vec_results, kw_results, alpha=0.7)
    assert len(fused_hybrid) == 3
    assert all(0.0 <= r.score <= 1.0 for r in fused_hybrid)
