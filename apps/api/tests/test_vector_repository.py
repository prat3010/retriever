"""Tests for PgVectorSearchAdapter (M5: Vector Search Repository)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.vector.vector_repository import PgVectorSearchAdapter
from src.domain.abstractions.retrieval import MetadataFilter, SearchResult


@pytest.fixture
def adapter() -> PgVectorSearchAdapter:
    return PgVectorSearchAdapter()


def _mock_row(chunk_id="chunk_1", doc_id="doc_1",
              content="text", score=0.95,
              metadata=None):
    return (chunk_id, doc_id, content, metadata or {}, score)


@pytest.mark.asyncio
@patch("src.adapters.vector.vector_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.vector_repository.build_filter_clause", autospec=True)
async def test_search_similar_happy_path(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = ("", {}, "")
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        _mock_row("c1", "d1", "hello", 0.95, {"source": "doc"}),
        _mock_row("c2", "d1", "world", 0.85, {"source": "doc"}),
    ]
    mock_db_session.execute.return_value = mock_result

    results = await adapter.search_similar(
        tenant_id="tnt_001",
        embedding=[0.1, 0.2, 0.3],
        top_k=10,
        filters=[],
        tags=[],
    )

    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)
    assert results[0].chunk_id == "c1"
    assert results[0].score == 0.95
    assert results[0].metadata == {"source": "doc"}
    mock_session_ctx.assert_called_once_with(tenant_id="tnt_001")


@pytest.mark.asyncio
@patch("src.adapters.vector.vector_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.vector_repository.build_filter_clause", autospec=True)
async def test_search_similar_empty_results(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = ("", {}, "")
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    results = await adapter.search_similar(
        tenant_id="tnt_001", embedding=[0.1], top_k=10, filters=[], tags=[],
    )
    assert results == []


@pytest.mark.asyncio
@patch("src.adapters.vector.vector_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.vector_repository.build_filter_clause", autospec=True)
async def test_search_similar_with_filters(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = (
        " AND dc.meta_data ->> 'dept' = :f_0",
        {"f_0": "legal"},
        "",
    )
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    flt = [MetadataFilter(field="dept", operator="eq", value="legal")]
    await adapter.search_similar(
        tenant_id="tnt_001", embedding=[0.1], top_k=10, filters=flt, tags=[],
    )

    mock_build_filter.assert_called_once_with(flt, [], "dc")
    call_params = mock_db_session.execute.call_args[0][1]
    assert call_params["f_0"] == "legal"


@pytest.mark.asyncio
@patch("src.adapters.vector.vector_repository.tenant_session", autospec=True)
@patch("src.adapters.vector.vector_repository.build_filter_clause", autospec=True)
async def test_search_similar_with_tags(mock_build_filter, mock_session_ctx, adapter):
    mock_build_filter.return_value = (
        " AND d.tags @> ARRAY[:tag_filters]::varchar[]",
        {"tag_filters": ["finance"]},
        " JOIN documents d ON dc.document_id = d.document_id",
    )
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    await adapter.search_similar(
        tenant_id="tnt_001", embedding=[0.1], top_k=10, filters=[], tags=["finance"],
    )

    call_sql = mock_db_session.execute.call_args[0][0].text
    assert "JOIN documents d ON" in call_sql
    assert "tag_filters" in call_sql
