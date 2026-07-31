"""Unit tests for Milestone 27: Multi-Workspace Collections."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.adapters.vector.filter_builder import build_filter_clause
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.inference import ChatSessionInfo
from src.domain.abstractions.ingestion import Document
from src.domain.retrieval.query_builder import build_search_query
from src.main import app

client = TestClient(app)


# ── 1. Filter Builder Collection Scoping ─────────────────────────────────────


def test_build_filter_clause_with_collection_id() -> None:
    """Verify build_filter_clause includes collection_id SQL filter when provided."""
    coll_id = str(uuid.uuid4())
    clause, params, _join_sql = build_filter_clause([], [], chunk_alias="dc", collection_id=coll_id)

    assert "dc.collection_id = CAST(:collection_id AS uuid)" in clause
    assert params["collection_id"] == coll_id


def test_build_filter_clause_without_collection_id() -> None:
    """Verify build_filter_clause omits collection_id when None."""
    clause, params, _join_sql = build_filter_clause([], [], chunk_alias="dc", collection_id=None)

    assert "collection_id" not in clause
    assert "collection_id" not in params


# ── 2. Query Builder Collection Propagation ─────────────────────────────────


def test_query_builder_propagates_collection_id() -> None:
    """Verify build_search_query copies collection_id from request payload."""
    coll_id = str(uuid.uuid4())
    payload = MagicMock(query="Python RAG", filters=[], tags=[], collection_id=coll_id)
    config = TenantConfiguration()

    search_query = build_search_query("tenant_123", config, payload)
    assert search_query.collection_id == coll_id


# ── 3. Document Router Collection Upload & List ──────────────────────────────


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.routers.document.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.routers.document.quota_service.check_storage_quota", new_callable=AsyncMock)
@patch("src.routers.document.document_repository.find_by_hash", new_callable=AsyncMock)
@patch("src.routers.document.document_repository.create_document", new_callable=AsyncMock)
@patch("src.routers.document.local_storage.save_file", new_callable=AsyncMock)
def test_upload_document_with_collection_id(
    mock_save_file,
    mock_create_doc,
    mock_find_by_hash,
    mock_check_quota,
    mock_get_config,
    mock_validate,
) -> None:
    """Verify document upload respects collectionId query parameter."""
    coll_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id="tenant_123",
        roles=["client"],
        scopes=["document:write"],
    )
    mock_get_config.return_value = TenantConfiguration()
    mock_check_quota.return_value = None
    mock_find_by_hash.return_value = None
    mock_save_file.return_value = "/storage/path/doc.pdf"

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    files = {"file": ("doc.pdf", b"Hello Collection A", "application/pdf")}

    response = client.post(
        f"/v1/tenants/tenant_123/documents?collectionId={coll_id}",
        headers=headers,
        files=files,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["collectionId"] == coll_id
    mock_create_doc.assert_called_once()
    created_doc: Document = mock_create_doc.call_args[0][1]
    assert created_doc.collection_id == coll_id


# ── 4. Search Router Collection Isolation ────────────────────────────────────


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.routers.search.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.routers.search.search_service.search", new_callable=AsyncMock)
def test_search_documents_passes_collection_id(
    mock_search,
    mock_get_config,
    mock_validate,
) -> None:
    """Verify POST /v1/tenants/{tenantId}/search forwards collectionId to SearchQuery."""
    coll_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id="tenant_123",
        roles=["client"],
        scopes=["document:read"],
    )
    mock_get_config.return_value = TenantConfiguration()
    mock_search.return_value = MagicMock(
        query="Vector test",
        results=[],
        search_meta=MagicMock(strategy="hybrid", total_candidates=0, returned_results=0, duration_ms=1.5),
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    payload = {"query": "Vector test", "collectionId": coll_id}

    response = client.post(
        "/v1/tenants/tenant_123/search",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    mock_search.assert_called_once()
    passed_query = mock_search.call_args[0][0]
    assert passed_query.collection_id == coll_id


# ── 5. Chat Router Collection Scoped Message Inference ────────────────────────


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.routers.chat.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.routers.chat.quota_service.check_inference_quota", new_callable=AsyncMock)
@patch("src.routers.chat.inference_orchestrator.get_session", new_callable=AsyncMock)
@patch("src.routers.chat.search_service.search", new_callable=AsyncMock)
@patch("src.routers.chat.inference_orchestrator.generate", new_callable=AsyncMock)
def test_chat_message_passes_collection_id(
    mock_generate,
    mock_search,
    mock_get_session,
    mock_check_quota,
    mock_get_config,
    mock_validate,
) -> None:
    """Verify POST chat/messages passes collectionId to retrieval engine."""
    coll_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id=user_id,
        tenant_id="tenant_123",
        roles=["client"],
        scopes=["document:write"],
    )
    mock_get_session.return_value = ChatSessionInfo(
        session_id="sess_workspace_1",
        tenant_id="tenant_123",
        user_id=user_id,
        created_at="2026-07-31T00:00:00Z",
    )
    mock_get_config.return_value = TenantConfiguration()
    mock_check_quota.return_value = None
    mock_search.return_value = MagicMock(results=[])
    mock_generate.return_value = MagicMock(
        content="Collection A response",
        usage=MagicMock(input_tokens=10, output_tokens=5, total_tokens=15),
        finish_reason="stop",
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": user_id}
    payload = {"query": "Tell me about Workspace A", "stream": False, "collectionId": coll_id}

    response = client.post(
        "/v1/tenants/tenant_123/chat/sessions/sess_workspace_1/messages",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    mock_search.assert_called_once()
    passed_query = mock_search.call_args[0][0]
    assert passed_query.collection_id == coll_id
