"""Tests for CohereRerankerAdapter (M5: Reranker Integration)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.cognitive.reranker_adapter import CohereRerankerAdapter
from src.domain.abstractions.retrieval import SearchResult


@pytest.fixture
def adapter():
    return CohereRerankerAdapter(api_key="test-key")


def _result(chunk_id="c1", score=0.5, content="text"):
    return SearchResult(
        chunk_id=chunk_id, document_id="d1", content=content, score=score, metadata={},
    )


def _mock_rerank_response(results_data):
    """Build a mock rerank response with result objects."""
    mock_results = []
    for idx, score in results_data:
        item = MagicMock()
        item.index = idx
        item.relevance_score = score
        mock_results.append(item)
    mock_response = MagicMock()
    mock_response.results = mock_results
    return mock_response


def _patch_client(adapter):
    """Set up a mock client on the adapter (client is a read-only property)."""
    mock_client = MagicMock()
    mock_client.rerank = AsyncMock()
    adapter._client = mock_client
    return mock_client


def test_lazy_client_not_created_at_init(adapter):
    assert adapter._client is None


def test_lazy_client_created_on_access(adapter):
    with patch("src.adapters.cognitive.reranker_adapter.cohere.AsyncClientV2") as mock_cls:
        _ = adapter.client
        mock_cls.assert_called_once_with(api_key="test-key")


@pytest.mark.asyncio
async def test_rerank_empty_candidates(adapter):
    result = await adapter.rerank(query="test", candidates=[], top_n=5, threshold=0.0)
    assert result == []


@pytest.mark.asyncio
async def test_rerank_basic(adapter):
    candidates = [_result("c1", 0.5, "first"), _result("c2", 0.5, "second")]
    mock_resp = _mock_rerank_response([(0, 0.95), (1, 0.85)])
    mock_client = _patch_client(adapter)
    mock_client.rerank.return_value = mock_resp

    result = await adapter.rerank(
        query="test query", candidates=candidates, top_n=5, threshold=0.0,
    )

    assert len(result) == 2
    assert result[0].chunk_id == "c1"
    assert result[0].score == 0.95
    assert result[1].chunk_id == "c2"
    assert result[1].score == 0.85

    mock_client.rerank.assert_called_once_with(
        model="rerank-v3.5",
        query="test query",
        documents=["first", "second"],
        top_n=2,
    )


@pytest.mark.asyncio
async def test_rerank_threshold_filtering(adapter):
    candidates = [_result("c1", 0.5, "a"), _result("c2", 0.5, "b")]
    mock_resp = _mock_rerank_response([(0, 0.95), (1, 0.30)])
    mock_client = _patch_client(adapter)
    mock_client.rerank.return_value = mock_resp

    result = await adapter.rerank(
        query="test", candidates=candidates, top_n=5, threshold=0.5,
    )

    assert len(result) == 1
    assert result[0].chunk_id == "c1"


@pytest.mark.asyncio
async def test_rerank_score_remapped(adapter):
    candidates = [_result("c1", 0.5, "a")]
    mock_resp = _mock_rerank_response([(0, 0.987654)])
    mock_client = _patch_client(adapter)
    mock_client.rerank.return_value = mock_resp

    result = await adapter.rerank(
        query="test", candidates=candidates, top_n=5, threshold=0.0,
    )

    assert result[0].score == 0.987654


@pytest.mark.asyncio
async def test_rerank_model_overrides_default(adapter):
    candidates = [_result("c1", 0.5, "a")]
    mock_resp = _mock_rerank_response([(0, 0.9)])
    mock_client = _patch_client(adapter)
    mock_client.rerank.return_value = mock_resp

    adapter.model = "rerank-v2"
    await adapter.rerank(
        query="test", candidates=candidates, top_n=5, threshold=0.0,
    )

    assert mock_client.rerank.call_args[1]["model"] == "rerank-v2"
