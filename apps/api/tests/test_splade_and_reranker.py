"""Unit tests for Milestone 45: Learned Sparse Retrieval (SPLADE) & Reranker Microservice."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.cognitive.tei_reranker_adapter import TeiRerankerAdapter
from src.adapters.vector.splade_sparse_adapter import SpladeSparseSearchAdapter
from src.domain.abstractions.retrieval import SearchResult

# ── 1. Unit Test: TeiRerankerAdapter HTTP Endpoint Calling & Filtering ──────

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_tei_reranker_adapter_success(mock_post):
    """Verify TeiRerankerAdapter sends HTTP POST to TEI service and re-scores candidates."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.raise_for_status = MagicMock()
    mock_res.json.return_value = [
        {"index": 1, "score": 0.92},
        {"index": 0, "score": 0.45},
    ]
    mock_post.return_value = mock_res

    adapter = TeiRerankerAdapter(endpoint_url="http://localhost:8080")
    candidates = [
        SearchResult(chunk_id="c0", document_id="d0", content="Text zero", score=0.5),
        SearchResult(chunk_id="c1", document_id="d1", content="Text one", score=0.6),
    ]

    reranked = await adapter.rerank(
        query="test query", candidates=candidates, top_n=2, threshold=0.7
    )

    assert len(reranked) == 1
    assert reranked[0].chunk_id == "c1"
    assert reranked[0].score == 0.92
    assert mock_post.called


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_tei_reranker_adapter_fallback_on_error(mock_post):
    """Verify TeiRerankerAdapter falls back to original candidates when TEI endpoint fails."""
    mock_post.side_effect = Exception("Connection refused")

    adapter = TeiRerankerAdapter(endpoint_url="http://localhost:8080")
    candidates = [
        SearchResult(chunk_id="c0", document_id="d0", content="Text zero", score=0.5),
    ]

    reranked = await adapter.rerank(
        query="test query", candidates=candidates, top_n=1, threshold=0.7
    )

    assert len(reranked) == 1
    assert reranked[0].chunk_id == "c0"


# ── 2. Unit Test: SpladeSparseSearchAdapter Weight Expansion ─────────────────

def test_splade_sparse_adapter_weight_expansion():
    """Verify SpladeSparseSearchAdapter expands queries with domain token weights."""
    adapter = SpladeSparseSearchAdapter()
    weights = adapter.extract_sparse_weights("physician database rag")

    assert "physician" in weights
    assert "doctor" in weights
    assert "database" in weights
    assert "db" in weights
    assert "rag" in weights
    assert "retrieval" in weights

    expanded = adapter.build_expanded_query_string("physician")
    assert "physician" in expanded
    assert "doctor" in expanded or "medical" in expanded or "OR" in expanded


@pytest.mark.asyncio
@patch("src.adapters.vector.splade_sparse_adapter.tenant_session")
async def test_splade_sparse_search_execution(mock_tenant_session):
    """Verify SpladeSparseSearchAdapter executes expanded tsquery search."""
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_exec_res = MagicMock()

    mock_row = (
        uuid.uuid4(),
        uuid.uuid4(),
        "Doctor specializes in internal medicine.",
        {},
        0.88,
    )
    mock_exec_res.fetchall.return_value = [mock_row]

    mock_db_session.execute.return_value = mock_exec_res
    mock_tenant_session.return_value.__aenter__.return_value = mock_db_session

    adapter = SpladeSparseSearchAdapter()
    tenant_id = str(uuid.uuid4())
    results = await adapter.search_keywords(
        tenant_id=tenant_id, query_text="physician", top_k=5, filters=[], tags=[]
    )

    assert len(results) == 1
    assert "Doctor" in results[0].content
