import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.adapters.telemetry.rate_limiter import RateLimitResult
from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.inference import ChatMessageInfo
from src.domain.abstractions.ingestion import Document
from src.domain.abstractions.tenant import Tenant
from src.main import app

client = TestClient(app)


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.document_repository.create_document", new_callable=AsyncMock)
@patch("src.main.document_repository.find_by_hash", new_callable=AsyncMock)
@patch("src.adapters.broker.celery_publisher.celery_app.send_task", autospec=True)
@patch("src.main.redis_client.get", new_callable=AsyncMock)
@patch("src.main.redis_client.setex", new_callable=AsyncMock)
def test_idempotency_keys(mock_setex, mock_get, mock_send_task, mock_find_by_hash, mock_create, mock_validate) -> None:
    """Verify that specifying an Idempotency-Key caches upload responses and prevents duplicates."""
    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )
    mock_find_by_hash.return_value = None

    headers = {
        "Authorization": "Bearer ret_live_validtoken.secret",
        "Idempotency-Key": "unique-req-123"
    }
    file_content = b"Sample text contents to parse and chunk."

    # First request: not cached
    mock_get.return_value = None
    response1 = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("sample.txt", file_content, "text/plain")},
        headers=headers,
    )
    assert response1.status_code == 202
    body1 = response1.json()
    assert "documentId" in body1

    # Second request: mock returns cached payload
    mock_get.return_value = json.dumps(body1).encode("utf-8")
    response2 = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("sample.txt", file_content, "text/plain")},
        headers=headers,
    )
    assert response2.status_code == 202
    body2 = response2.json()
    assert body2["documentId"] == body1["documentId"]
    assert mock_get.called


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.tenant_registry.list_tenants_cursor", new_callable=AsyncMock)
def test_admin_list_tenants_cursor(mock_list_cursor, mock_validate) -> None:
    """GET /v1/admin/tenants returns cursor paginated list when offset is None."""
    mock_validate.return_value = UserContext(
        user_id="admin_123",
        tenant_id="system",
        roles=["admin"],
        scopes=["admin:*"],
    )
    mock_list_cursor.return_value = (
        [
            Tenant(
                tenant_id="t1", name="Tenant 1", status="active",
                tier="standard", created_at="2026-01-01T00:00:00",
            )
        ],
        "next-cursor-xyz",
        True
    )

    headers = {"X-Admin-Master-Key": "dev-admin-master-key-change-in-production"}
    response = client.get("/v1/admin/tenants?cursor=", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "pagination" in body
    assert body["pagination"]["nextCursor"] == "next-cursor-xyz"
    assert body["pagination"]["hasMore"] is True
    assert len(body["items"]) == 1


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.document_repository.list_documents_cursor", new_callable=AsyncMock)
def test_list_documents_cursor(mock_list_cursor, mock_validate) -> None:
    """GET /v1/tenants/{tenantId}/documents returns cursor paginated list when limit/cursor is specified."""
    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )
    mock_list_cursor.return_value = (
        [
            Document(
                document_id="doc-123",
                tenant_id=tenant_id,
                filename="sample.txt",
                file_hash="hash123",
                storage_path="/path",
                file_size=100,
                mime_type="text/plain",
                status="READY",
                created_at="2026-01-01T00:00:00",
                updated_at="2026-01-01T00:00:00",
            )
        ],
        "cursor-next",
        True
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.get(f"/v1/tenants/{tenant_id}/documents?limit=10", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "pagination" in body
    assert body["pagination"]["nextCursor"] == "cursor-next"
    assert body["pagination"]["hasMore"] is True
    assert len(body["items"]) == 1


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.inference_orchestrator.get_session", new_callable=AsyncMock)
@patch("src.main.session_repo.get_messages_cursor", new_callable=AsyncMock)
def test_list_messages_cursor(mock_get_messages_cursor, mock_get_session, mock_validate) -> None:
    """GET /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages returns cursor paginated chat history."""
    tenant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    user_uuid = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id=user_uuid,
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )
    mock_get_session.return_value = MagicMock()
    mock_get_messages_cursor.return_value = (
        [
            ChatMessageInfo(
                message_id="msg-1",
                session_id=session_id,
                tenant_id=tenant_id,
                role="user",
                content="Hello",
                name=None,
                created_at="2026-01-01T00:00:00"
            )
        ],
        "next-msg-cursor",
        True
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": user_uuid}
    response = client.get(f"/v1/tenants/{tenant_id}/chat/sessions/{session_id}/messages?limit=10", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "pagination" in body
    assert body["pagination"]["nextCursor"] == "next-msg-cursor"
    assert body["pagination"]["hasMore"] is True
    assert len(body["items"]) == 1


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.search_service.search", new_callable=AsyncMock)
@patch("src.main.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.adapters.telemetry.rate_limiter_dep.get_rate_limiter")
def test_rate_limit_headers(mock_get_limiter, mock_get_config, mock_search, mock_validate) -> None:
    """Verify that requests set X-RateLimit headers based on rate limiter metrics."""
    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )

    from src.domain.abstractions.retrieval import SearchMeta, SearchResponse
    mock_search.return_value = SearchResponse(
        query="test",
        results=[],
        search_meta=SearchMeta(
            strategy="dense",
            total_candidates=0,
            returned_results=0,
            duration_ms=10.0
        )
    )

    mock_config = MagicMock()
    mock_config.feature_flags.enable_hybrid_search = False
    mock_config.feature_flags.enable_reranking = False
    mock_config.retrieval_settings.rrf_k = 60
    mock_config.retrieval_settings.reranking_threshold = 0.5
    mock_config.retrieval_settings.web_search_provider = "tavily"
    mock_config.retrieval_settings.web_search_api_key = None
    mock_get_config.return_value = mock_config

    mock_limiter = AsyncMock()
    mock_limiter.acquire.return_value = RateLimitResult(
        allowed=True,
        limit=100,
        remaining=99,
        reset_after=30
    )
    mock_get_limiter.return_value = mock_limiter

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/search",
        json={"query": "test", "limit": 5},
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "100"
    assert response.headers["X-RateLimit-Remaining"] == "99"
    assert response.headers["X-RateLimit-Reset"] == "30"
