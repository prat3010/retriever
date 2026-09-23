"""Automated test suite for Document-Level Access Control List (ACL) Inheritance & Pre-Retrieval Enforcement (M125)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.vector.filter_builder import build_filter_clause
from src.domain.abstractions.retrieval import SearchQuery
from src.domain.retrieval.search_service import HybridSearchService

# ==============================================================================
# Filter Builder ACL Clause Tests
# ==============================================================================


def test_filter_builder_acl_disabled_by_default():
    """Verify that when enable_acl_filter is False, no ACL clause is injected."""
    clause, params, _ = build_filter_clause(
        filters=None,
        tags=None,
        collection_id=None,
        user_id="user_42",
        user_role="member",
        user_groups=["engineering"],
        enable_acl_filter=False,
    )
    assert "allowed_users" not in clause
    assert "allowed_groups" not in clause
    assert "acl_user_id" not in params
    assert "acl_user_groups" not in params


def test_filter_builder_acl_admin_bypass():
    """Verify that user_role == 'admin' bypasses ACL filtering even if enable_acl_filter is True."""
    clause, params, _ = build_filter_clause(
        filters=None,
        tags=None,
        collection_id=None,
        user_id="admin_1",
        user_role="admin",
        user_groups=["admins"],
        enable_acl_filter=True,
    )
    assert "allowed_users" not in clause
    assert "allowed_groups" not in clause
    assert "acl_user_id" not in params


def test_filter_builder_acl_user_and_groups():
    """Verify that user_id and user_groups create an OR clause with public access."""
    clause, params, _ = build_filter_clause(
        filters=None,
        tags=None,
        collection_id=None,
        user_id="alice@corp.internal",
        user_role="member",
        user_groups=["security-team", "engineering"],
        enable_acl_filter=True,
    )
    assert "is_public')::boolean = true" in clause
    assert "allowed_users') ? :acl_user_id" in clause
    assert "allowed_groups') ?| :acl_user_groups" in clause
    assert params["acl_user_id"] == "alice@corp.internal"
    assert params["acl_user_groups"] == ["security-team", "engineering"]


def test_filter_builder_acl_anonymous_only_public():
    """Verify that an anonymous query with enable_acl_filter=True only matches public chunks."""
    clause, params, _ = build_filter_clause(
        filters=None,
        tags=None,
        collection_id=None,
        user_id=None,
        user_role=None,
        user_groups=None,
        enable_acl_filter=True,
    )
    assert "is_public')::boolean = true" in clause
    assert "acl_user_id" not in params
    assert "acl_user_groups" not in params


def test_filter_builder_combines_tags_and_acl():
    """Verify that tags, dict filters, and ACL conditions are properly conjoined."""
    clause, params, join = build_filter_clause(
        filters={"department": "rnd"},
        tags=["prod", "v2"],
        collection_id="col_123",
        user_id="bob@corp.internal",
        user_role="member",
        user_groups=["rnd-staff"],
        enable_acl_filter=True,
    )
    assert "d.tags @> ARRAY[:tag_filters]::varchar[]" in clause
    assert "collection_id = CAST(:collection_id AS uuid)" in clause
    assert "meta_data ->> 'department' = :f_0" in clause
    assert params["f_0"] == "rnd"
    assert "allowed_users') ? :acl_user_id" in clause
    assert "allowed_groups') ?| :acl_user_groups" in clause
    assert clause.startswith(" AND ")
    assert "JOIN documents" in join


# ==============================================================================
# SearchQuery Model Validation & Propagation
# ==============================================================================


def test_search_query_acl_fields():
    q = SearchQuery(
        tenant_id="tn_test_001",
        query="What is the OAuth token expiration?",
        user_id="user_777",
        user_role="member",
        user_groups=["security", "compliance"],
        enable_acl_filter=True,
    )
    assert q.user_groups == ["security", "compliance"]
    assert q.enable_acl_filter is True


@pytest.mark.asyncio
async def test_search_service_fan_out_forwards_acl_parameters():
    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = []
    mock_keyword = AsyncMock()
    mock_keyword.search_keywords.return_value = []
    mock_embedder = AsyncMock()
    mock_embedder.embed_query.return_value = [0.1] * 768
    mock_reranker = AsyncMock()

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=mock_keyword,
        embedder=mock_embedder,
        reranker=mock_reranker,
    )

    query = SearchQuery(
        tenant_id="tn_acl_test",
        query="Confidential financial report",
        user_id="cfo@corp.internal",
        user_role="member",
        user_groups=["finance-execs"],
        enable_acl_filter=True,
        enable_hybrid=True,
    )

    await service._fan_out_search(query=query, query_embedding=[0.1] * 768, search_k=10)

    # Check vector search call kwargs
    mock_vector.search_similar.assert_awaited_once()
    _, vector_kwargs = mock_vector.search_similar.call_args
    assert vector_kwargs["user_id"] == "cfo@corp.internal"
    assert vector_kwargs["user_role"] == "member"
    assert vector_kwargs["user_groups"] == ["finance-execs"]
    assert vector_kwargs["enable_acl_filter"] is True

    # Check keyword search call kwargs
    mock_keyword.search_keywords.assert_awaited_once()
    _, kw_kwargs = mock_keyword.search_keywords.call_args
    assert kw_kwargs["user_id"] == "cfo@corp.internal"
    assert kw_kwargs["user_role"] == "member"
    assert kw_kwargs["user_groups"] == ["finance-execs"]
    assert kw_kwargs["enable_acl_filter"] is True


# ==============================================================================
# Ingestion Service ACL Metadata Propagation
# ==============================================================================


@pytest.mark.asyncio
async def test_ingest_file_sync_preserves_acl_metadata():
    from src.adapters.ingestion.sync_ingestion_service import ingest_file_sync

    doc_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    mock_embedder = AsyncMock()
    mock_embedder.embed_batch = AsyncMock(side_effect=lambda texts: [[0.05] * 768 for _ in texts])

    # Mock session
    mock_session = AsyncMock()
    mock_exec = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_exec.return_value = mock_result
    mock_session.execute = mock_exec

    added_objects = []

    def fake_add(obj):
        added_objects.append(obj)

    mock_session.add = fake_add

    class FakeTenantSession:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc, tb):
            pass

    with patch("src.adapters.ingestion.sync_ingestion_service.tenant_session", return_value=FakeTenantSession()):
        count = await ingest_file_sync(
            tenant_id=tenant_id,
            document_id=doc_id,
            filename="confidential_sow.txt",
            content_bytes=b"Standard scope of work agreement with pricing details.",
            embedder=mock_embedder,
            doc_metadata={
                "allowed_users": ["client_owner@enterprise.internal"],
                "allowed_groups": ["procurement-executives"],
                "is_public": False,
            },
        )

        assert count > 0
        from src.adapters.database.models import DocumentChunkDb

        chunk_records = [o for o in added_objects if isinstance(o, DocumentChunkDb)]
        assert len(chunk_records) > 0
        for chunk in chunk_records:
            assert chunk.meta_data["allowed_users"] == ["client_owner@enterprise.internal"]
            assert chunk.meta_data["allowed_groups"] == ["procurement-executives"]
            assert chunk.meta_data["is_public"] is False
