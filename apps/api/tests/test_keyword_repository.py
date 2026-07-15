"""Tests for PgKeywordSearchAdapter (M5: Keyword Search Repository)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.vector.keyword_repository import PgKeywordSearchAdapter
from src.domain.abstractions.retrieval import MetadataFilter, SearchResult


@pytest.fixture
def adapter() -> PgKeywordSearchAdapter:
    return PgKeywordSearchAdapter()


def _mock_row(chunk_id="chunk_1", doc_id="doc_1",
              content="text", score=0.75,
              metadata=None):
    return (chunk_id, doc_id, content, metadata or {}, score)


@pytest.mark.asyncio
@patch("src.adapters.vector.keyword_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.keyword_repository.build_filter_clause", autospec=True)
async def test_search_keywords_happy_path(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = ("", {}, "")
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        _mock_row("c1", "d1", "legal document", 0.75, {"type": "contract"}),
    ]
    mock_db_session.execute.return_value = mock_result

    results = await adapter.search_keywords(
        tenant_id="tnt_001",
        query_text="legal",
        top_k=10,
        filters=[],
        tags=[],
    )

    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].chunk_id == "c1"
    assert results[0].score == 0.75
    assert results[0].metadata == {"type": "contract"}
    mock_session_ctx.assert_called_once_with(tenant_id="tnt_001")


@pytest.mark.asyncio
@patch("src.adapters.vector.keyword_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.keyword_repository.build_filter_clause", autospec=True)
async def test_search_keywords_empty(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = ("", {}, "")
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    results = await adapter.search_keywords(
        tenant_id="tnt_001", query_text="unknown", top_k=10, filters=[], tags=[],
    )
    assert results == []


@pytest.mark.asyncio
@patch("src.adapters.vector.keyword_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.keyword_repository.build_filter_clause", autospec=True)
async def test_search_keywords_with_filters(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = (
        " AND dc.meta_data ->> 'status' = :f_0",
        {"f_0": "active"},
        "",
    )
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    flt = [MetadataFilter(field="status", operator="eq", value="active")]
    await adapter.search_keywords(
        tenant_id="tnt_001", query_text="test", top_k=10, filters=flt, tags=[],
    )

    mock_build_filter.assert_called_once_with(flt, [], "dc")
    call_params = mock_db_session.execute.call_args[0][1]
    assert call_params["f_0"] == "active"


@pytest.mark.asyncio
@patch("src.adapters.vector.keyword_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.keyword_repository.build_filter_clause", autospec=True)
async def test_search_keywords_passes_query_text(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = ("", {}, "")
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    await adapter.search_keywords(
        tenant_id="tnt_001", query_text="confidential agreement",
        top_k=5, filters=[], tags=[],
    )

    call_params = mock_db_session.execute.call_args[0][1]
    assert call_params["query"] == "confidential agreement"
    assert call_params["top_k"] == 5
