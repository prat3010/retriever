"""Unit tests for LocalRerankerAdapter."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.cognitive.local_reranker_adapter import LocalRerankerAdapter
from src.domain.abstractions.retrieval import SearchResult


@pytest.mark.asyncio
async def test_local_reranker_success() -> None:
    adapter = LocalRerankerAdapter(model_name="test-model")

    candidates = [
        SearchResult(chunk_id="c1", document_id="d1", content="apple pie recipe", score=0.5),
        SearchResult(chunk_id="c2", document_id="d1", content="quantum computing physics", score=0.9),
    ]

    mock_cross_encoder = MagicMock()
    mock_cross_encoder.predict.return_value = [0.95, 0.10]

    with patch.object(adapter, "_get_model", return_value=mock_cross_encoder):
        reranked = await adapter.rerank("recipe for baking apple pie", candidates, top_n=2, threshold=0.3)

    assert len(reranked) == 1
    assert reranked[0].chunk_id == "c1"
    assert reranked[0].score == 0.95


@pytest.mark.asyncio
async def test_local_reranker_fallback_on_missing_model() -> None:
    adapter = LocalRerankerAdapter(model_name="missing-model")

    candidates = [
        SearchResult(chunk_id="c1", document_id="d1", content="doc 1", score=0.8),
        SearchResult(chunk_id="c2", document_id="d1", content="doc 2", score=0.6),
    ]

    with patch.object(adapter, "_get_model", return_value=None):
        reranked = await adapter.rerank("query", candidates, top_n=2, threshold=0.5)

    assert len(reranked) == 2
    assert reranked[0].chunk_id == "c1"
