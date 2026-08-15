"""Tests for Milestone 43: Dynamic Multi-Embedding Vector Schemas & Index Scaling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.database.models import (
    VectorRecord1536Db,
    VectorRecord3072Db,
    VectorRecordDb,
    get_vector_table_name,
)
from src.adapters.vector.vector_repository import PgVectorSearchAdapter


def test_get_vector_table_name_resolution() -> None:
    assert get_vector_table_name(768) == "vector_records"
    assert get_vector_table_name(1536) == "vector_records_1536"
    assert get_vector_table_name(3072) == "vector_records_3072"
    assert get_vector_table_name(512) == "vector_records"


def test_vector_model_classes_attributes() -> None:
    assert VectorRecordDb.__tablename__ == "vector_records"
    assert VectorRecord1536Db.__tablename__ == "vector_records_1536"
    assert VectorRecord3072Db.__tablename__ == "vector_records_3072"


@pytest.mark.asyncio
async def test_search_similar_routes_to_1536_table() -> None:
    adapter = PgVectorSearchAdapter()
    embedding_1536 = [0.1] * 1536

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result

    with patch("src.adapters.vector.vector_repository.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_session

        results = await adapter.search_similar(
            tenant_id="00000000-0000-0000-0000-000000000001",
            embedding=embedding_1536,
            top_k=5,
            filters=[],
            tags=[],
        )

        assert results == []
        assert mock_session.execute.called
        query_text = str(mock_session.execute.call_args[0][0])
        assert "FROM vector_records_1536 vr" in query_text


@pytest.mark.asyncio
async def test_search_similar_routes_to_3072_table() -> None:
    adapter = PgVectorSearchAdapter()
    embedding_3072 = [0.1] * 3072

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result

    with patch("src.adapters.vector.vector_repository.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_session

        results = await adapter.search_similar(
            tenant_id="00000000-0000-0000-0000-000000000001",
            embedding=embedding_3072,
            top_k=5,
            filters=[],
            tags=[],
        )

        assert results == []
        assert mock_session.execute.called
        query_text = str(mock_session.execute.call_args[0][0])
        assert "FROM vector_records_3072 vr" in query_text
