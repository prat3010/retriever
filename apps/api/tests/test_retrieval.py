"""Retrieval, Fusion & Rerank Tests.

Comprehensive mock-based tests verifying:
- HybridSearchService RRF fusion math
- Graceful degradation on search leg failure
- Reranker integration and fallback behavior
- Search API endpoint auth, tenant isolation, and response shape
- RLS enforcement on vector and keyword repository adapters
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.retrieval import SearchQuery, SearchResult
from src.domain.retrieval.search_service import HybridSearchService
from src.main import app

client = TestClient(app)


def _make_result(chunk_id: str, score: float, content: str = "text") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=str(uuid.uuid4()),
        content=content,
        score=score,
        metadata={},
    )


# --- 1. RRF Fusion Logic ---

def test_rrf_fusion_logic() -> None:
    """Verify RRF score computation and merged sort order."""
    service = HybridSearchService(
        vector_search=MagicMock(),
        keyword_search=MagicMock(),
        embedder=MagicMock(),
        reranker=MagicMock(),
    )

    # Chunk A appears rank 1 in vector, rank 2 in keyword
    # Chunk B appears rank 2 in vector, rank 1 in keyword
    # Chunk C appears rank 3 in vector only
    rrf_k = 60
    vector_results = [
        _make_result("chunk_a", 0.95),
        _make_result("chunk_b", 0.85),
        _make_result("chunk_c", 0.70),
    ]
    keyword_results = [
        _make_result("chunk_b", 0.90),
        _make_result("chunk_a", 0.80),
    ]

    fused = service._fuse_rrf(vector_results, keyword_results, rrf_k)

    # Verify all chunks are present
    ids = [r.chunk_id for r in fused]
    assert "chunk_a" in ids
    assert "chunk_b" in ids
    assert "chunk_c" in ids

    # Chunks A and B appear in both lists so should have higher RRF scores than C
    scores = {r.chunk_id: r.score for r in fused}

    # chunk_a: 1/(60+1) + 1/(60+2) = ~0.01639 + ~0.01613 = ~0.03253
    # chunk_b: 1/(60+2) + 1/(60+1) = ~0.01613 + ~0.01639 = ~0.03253
    # chunk_c: 1/(60+3) = ~0.01587
    assert scores["chunk_a"] > scores["chunk_c"]
    assert scores["chunk_b"] > scores["chunk_c"]

    # A and B should be tied (symmetric ranks)
    assert abs(scores["chunk_a"] - scores["chunk_b"]) < 1e-6

    # Results should be sorted descending
    score_list = [r.score for r in fused]
    assert score_list == sorted(score_list, reverse=True)


def test_rrf_handles_empty_results() -> None:
    """Verify RRF gracefully handles empty input lists."""
    service = HybridSearchService(
        vector_search=MagicMock(),
        keyword_search=MagicMock(),
        embedder=MagicMock(),
        reranker=MagicMock(),
    )

    # Both empty
    assert service._fuse_rrf([], [], 60) == []

    # One empty
    results = [_make_result("chunk_x", 0.9)]
    fused = service._fuse_rrf(results, [], 60)
    assert len(fused) == 1
    assert fused[0].chunk_id == "chunk_x"


# --- 2. Reranker Integration ---

@pytest.mark.asyncio
async def test_reranker_integration() -> None:
    """Verify reranker filters by threshold and remaps scores."""
    mock_reranker = AsyncMock()
    mock_reranker.rerank.return_value = [
        _make_result("chunk_high", 0.95),
        # chunk_low is below threshold — already filtered by reranker
    ]

    service = HybridSearchService(
        vector_search=MagicMock(),
        keyword_search=MagicMock(),
        embedder=MagicMock(),
        reranker=mock_reranker,
    )

    candidates = [
        _make_result("chunk_high", 0.5),
        _make_result("chunk_low", 0.3),
    ]

    reranked, strategy = await service._apply_reranking(
        query=SearchQuery(query="test", tenant_id="t1"),
        candidates=candidates,
        strategy="hybrid_rrf",
    )

    assert len(reranked) == 1
    assert reranked[0].chunk_id == "chunk_high"
    assert reranked[0].score == 0.95
    assert strategy == "hybrid_rrf_reranked"


@pytest.mark.asyncio
async def test_reranker_graceful_degradation() -> None:
    """Verify search service falls back to RRF results when reranker fails."""
    mock_reranker = AsyncMock()
    mock_reranker.rerank.side_effect = Exception("Cohere API timeout")

    service = HybridSearchService(
        vector_search=MagicMock(),
        keyword_search=MagicMock(),
        embedder=MagicMock(),
        reranker=mock_reranker,
    )

    candidates = [_make_result("chunk_1", 0.8)]

    reranked, strategy = await service._apply_reranking(
        query=SearchQuery(query="test", tenant_id="t1"),
        candidates=candidates,
        strategy="hybrid_rrf",
    )

    # Should return original candidates without crashing
    assert len(reranked) == 1
    assert reranked[0].chunk_id == "chunk_1"
    assert strategy == "hybrid_rrf"  # Not appended with _reranked


# --- 3. Vector-Only When Hybrid Disabled ---

@pytest.mark.asyncio
async def test_search_vector_only_when_hybrid_disabled() -> None:
    """Verify only vector search is invoked when hybrid is disabled."""
    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = [_make_result("v1", 0.9)]

    mock_keyword = AsyncMock()
    mock_keyword.search_keywords.return_value = []

    mock_embedder = AsyncMock()
    mock_embedder.embed_text.return_value = [0.1] * 1536

    mock_reranker = AsyncMock()
    mock_reranker.rerank.return_value = [_make_result("v1", 0.9)]

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=mock_keyword,
        embedder=mock_embedder,
        reranker=mock_reranker,
    )

    query = SearchQuery(
        query="test",
        tenant_id="t1",
        enable_hybrid=False,
        enable_reranking=False,
    )
    response = await service.search(query)

    # Vector search should have been called
    mock_vector.search_similar.assert_called_once()

    # Keyword search should NOT have been called (hybrid disabled)
    mock_keyword.search_keywords.assert_not_called()

    assert response.search_meta.strategy == "vector_only"


# --- 4. Search API Endpoint ---

@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.search_service.search", new_callable=AsyncMock)
@patch("src.main.config_service.get_tenant_config", new_callable=AsyncMock)
def test_search_endpoint_success(
    mock_get_config, mock_search, mock_validate
) -> None:
    """Verify POST /v1/tenants/{tenantId}/search returns correct response."""
    from src.domain.abstractions.config import TenantConfiguration
    from src.domain.abstractions.retrieval import SearchMeta, SearchResponse

    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )
    mock_get_config.return_value = TenantConfiguration(tenant_id=tenant_id)

    mock_search.return_value = SearchResponse(
        query="test query",
        results=[
            SearchResult(
                chunk_id="chk_001",
                document_id="doc_001",
                content="Budget is $450k.",
                score=0.92,
                metadata={"page": 12},
            )
        ],
        search_meta=SearchMeta(
            strategy="hybrid_rrf_reranked",
            total_candidates=20,
            returned_results=1,
            duration_ms=87.5,
        ),
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/search",
        json={"query": "test query", "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "test query"
    assert len(body["results"]) == 1
    assert body["results"][0]["chunkId"] == "chk_001"
    assert body["results"][0]["score"] == 0.92
    assert body["searchMeta"]["strategy"] == "hybrid_rrf_reranked"
    assert body["searchMeta"]["totalCandidates"] == 20


# --- 5. Auth & Tenant Isolation ---

def test_search_requires_auth() -> None:
    """Verify search endpoint rejects requests without authorization."""
    tenant_id = str(uuid.uuid4())
    response = client.post(
        f"/v1/tenants/{tenant_id}/search",
        json={"query": "test"},
    )
    assert response.status_code == 401


@patch("src.adapters.api.security.tenant_session")
@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
def test_search_requires_tenant_isolation(mock_validate, mock_tenant_session) -> None:
    """Verify search endpoint rejects cross-tenant access attempts."""
    authenticated_tenant = str(uuid.uuid4())
    target_tenant = str(uuid.uuid4())

    # Set up mock session context manager
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=authenticated_tenant,
        roles=["integrator"],
        scopes=["document:read"],
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.post(
        f"/v1/tenants/{target_tenant}/search",
        json={"query": "test"},
        headers=headers,
    )
    assert response.status_code == 403


# --- 6. Adapter RLS Verification ---

@pytest.mark.asyncio
@patch("src.adapters.vector.vector_repository.tenant_session")
async def test_vector_repository_sets_rls(mock_session_ctx) -> None:
    """Verify PgVectorSearchAdapter calls tenant_session with tenant_id."""
    from src.adapters.vector.vector_repository import PgVectorSearchAdapter

    mock_db_session = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    adapter = PgVectorSearchAdapter()
    tenant_id = str(uuid.uuid4())
    await adapter.search_similar(
        tenant_id=tenant_id,
        embedding=[0.1] * 1536,
        top_k=5,
        filters={},
    )

    mock_session_ctx.assert_called_once_with(tenant_id=tenant_id)


@pytest.mark.asyncio
@patch("src.adapters.vector.keyword_repository.tenant_session")
async def test_keyword_repository_sets_rls(mock_session_ctx) -> None:
    """Verify PgKeywordSearchAdapter calls tenant_session with tenant_id."""
    from src.adapters.vector.keyword_repository import PgKeywordSearchAdapter

    mock_db_session = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    adapter = PgKeywordSearchAdapter()
    tenant_id = str(uuid.uuid4())
    await adapter.search_keywords(
        tenant_id=tenant_id,
        query_text="budget report",
        top_k=5,
        filters={},
    )

    mock_session_ctx.assert_called_once_with(tenant_id=tenant_id)
