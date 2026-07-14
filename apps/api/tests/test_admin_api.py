"""Admin API endpoint tests.

Verifies all admin endpoints under /v1/admin/:
- Tenant CRUD (list, get, deactivate)
- User management (list, create with conflict)
- API key management (list, create, revoke with 404)
- Config management (get, update)
- Document listing
- Prompt templates CRUD + preview
- Audit log listing
"""

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.domain.abstractions.exceptions import PromptTemplateNotFoundError
from src.domain.abstractions.identity import UserInfo
from src.domain.abstractions.inference import PromptTemplate
from src.domain.abstractions.tenant import Tenant
from src.main import app

client = TestClient(app)

ADMIN_KEY = "dev-admin-master-key-change-in-production"
auth_header = {"X-Admin-Master-Key": ADMIN_KEY}

tenant_id = str(uuid.uuid4())
key_id = str(uuid.uuid4())


def test_admin_master_key_required() -> None:
    """Verify admin endpoints reject requests without X-Admin-Master-Key."""
    response = client.get("/v1/admin/tenants")
    assert response.status_code == 422  # FastAPI required header validation


# ── Tenant Endpoints ──────────────────────────────────────────────────────────


@patch("src.main.tenant_registry.list_tenants")
def test_admin_list_tenants(mock_list) -> None:
    """GET /v1/admin/tenants returns paginated tenant list."""
    mock_list.return_value = (
        [
            Tenant(
                tenant_id="t1", name="Test", status="active",
                tier="standard", created_at="2026-01-01T00:00:00",
            )
        ],
        1,
    )
    response = client.get("/v1/admin/tenants", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["tenantId"] == "t1"
    assert body["items"][0]["createdAt"] == "2026-01-01T00:00:00"


@patch("src.main.tenant_registry.list_tenants")
def test_admin_list_tenants_empty(mock_list) -> None:
    """GET /v1/admin/tenants returns empty list when no tenants."""
    mock_list.return_value = ([], 0)
    response = client.get("/v1/admin/tenants", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


@patch("src.main.tenant_registry.get_tenant")
def test_admin_get_tenant(mock_get) -> None:
    """GET /v1/admin/tenants/{id} returns tenant details."""
    mock_get.return_value = Tenant(
        tenant_id=tenant_id, name="Test", status="active",
        tier="standard", created_at="2026-01-01T00:00:00",
    )
    response = client.get(f"/v1/admin/tenants/{tenant_id}", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["tenantId"] == tenant_id
    assert body["createdAt"] == "2026-01-01T00:00:00"


@patch("src.main.tenant_registry.get_tenant")
def test_admin_get_tenant_not_found(mock_get) -> None:
    """GET /v1/admin/tenants/{id} returns 404 when tenant missing."""
    mock_get.return_value = None
    response = client.get(f"/v1/admin/tenants/{uuid.uuid4()}", headers=auth_header)
    assert response.status_code == 404


@patch("src.main.tenant_registry.deactivate_tenant")
def test_admin_deactivate_tenant(mock_deactivate) -> None:
    """DELETE /v1/admin/tenants/{id} deactivates and returns status."""
    mock_deactivate.return_value = True
    response = client.delete(f"/v1/admin/tenants/{tenant_id}", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == {"status": "deactivated", "tenantId": tenant_id}


@patch("src.main.tenant_registry.deactivate_tenant")
def test_admin_deactivate_tenant_not_found(mock_deactivate) -> None:
    """DELETE /v1/admin/tenants/{id} returns 404 for missing tenant."""
    mock_deactivate.return_value = False
    response = client.delete(f"/v1/admin/tenants/{uuid.uuid4()}", headers=auth_header)
    assert response.status_code == 404


# ── User Endpoints ────────────────────────────────────────────────────────────


@patch("src.main.user_repository.list_users")
def test_admin_list_users(mock_list) -> None:
    """GET /v1/admin/tenants/{id}/users returns user list."""
    mock_list.return_value = [
        UserInfo(
            user_id="u1", tenant_id=tenant_id,
            external_id="ext1", display_name="Alice", is_active=True,
            created_at="2026-01-01T00:00:00",
        )
    ]
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/users", headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["userId"] == "u1"


@patch("src.main.user_repository.create_user")
def test_admin_create_user(mock_create) -> None:
    """POST /v1/admin/tenants/{id}/users creates and returns 201."""
    mock_create.return_value = UserInfo(
        user_id="u1", tenant_id=tenant_id,
        external_id="new_ext", display_name="Bob", is_active=True,
        created_at="2026-01-01T00:00:00",
    )
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/users",
        json={"external_id": "new_ext", "display_name": "Bob"},
        headers=auth_header,
    )
    assert response.status_code == 201
    assert response.json()["userId"] == "u1"


@patch("src.main.user_repository.create_user")
def test_admin_create_user_duplicate(mock_create) -> None:
    """POST /v1/admin/tenants/{id}/users returns 409 on duplicate external_id."""
    mock_create.side_effect = ValueError(
        "User with external_id 'dup' already exists in tenant"
    )
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/users",
        json={"external_id": "dup"},
        headers=auth_header,
    )
    assert response.status_code == 409


# ── API Key Endpoints ─────────────────────────────────────────────────────────


@patch("src.main.identity_provider.list_api_keys")
def test_admin_list_api_keys(mock_list) -> None:
    """GET /v1/admin/tenants/{id}/api-keys returns key list."""
    from src.domain.abstractions.identity import ApiKeyMetadata
    mock_list.return_value = [
        ApiKeyMetadata(
            key_id="k1", tenant_id=tenant_id, name="my-key",
            prefix="ret_live_abc", role="client", status="active",
            created_at="2026-01-01T00:00:00",
        )
    ]
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/api-keys", headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["keyId"] == "k1"
    assert body[0]["role"] == "client"


@patch("src.main.identity_provider.create_api_key")
def test_admin_create_api_key(mock_create) -> None:
    """POST /v1/admin/tenants/{id}/api-keys creates and returns 201."""
    from src.domain.abstractions.identity import ApiKeyMetadata
    mock_create.return_value = (
        "ret_live_abc.secret123",
        ApiKeyMetadata(
            key_id="k1", tenant_id=tenant_id, name="new-key",
            prefix="ret_live_abc", role="admin", status="active",
            created_at="2026-01-01T00:00:00",
        ),
    )
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/api-keys",
        json={"name": "new-key", "role": "admin"},
        headers=auth_header,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["keyId"] == "k1"
    assert body["role"] == "admin"


@patch("src.main.identity_provider.revoke_api_key")
def test_admin_revoke_api_key(mock_revoke) -> None:
    """DELETE /v1/admin/tenants/{id}/api-keys/{keyId} revokes and returns status."""
    mock_revoke.return_value = True
    response = client.delete(
        f"/v1/admin/tenants/{tenant_id}/api-keys/{key_id}", headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "revoked", "keyId": key_id}


@patch("src.main.identity_provider.revoke_api_key")
def test_admin_revoke_api_key_not_found(mock_revoke) -> None:
    """DELETE returns 404 when API key not found."""
    mock_revoke.return_value = False
    response = client.delete(
        f"/v1/admin/tenants/{tenant_id}/api-keys/{uuid.uuid4()}", headers=auth_header,
    )
    assert response.status_code == 404


# ── Config Endpoints ──────────────────────────────────────────────────────────


@patch("src.main.config_service.get_tenant_config")
def test_admin_get_tenant_config(mock_get) -> None:
    """GET /v1/admin/tenants/{id}/config returns config."""
    from src.domain.abstractions.config import TenantConfiguration
    mock_get.return_value = TenantConfiguration(tenant_id=tenant_id)
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/config", headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == tenant_id  # snake_case in response model


@patch("src.main.config_service.update_tenant_config")
def test_admin_update_tenant_config(mock_update) -> None:
    """PUT /v1/admin/tenants/{id}/config updates and returns status."""
    mock_update.return_value = None
    response = client.put(
        f"/v1/admin/tenants/{tenant_id}/config",
        json={"tenantId": tenant_id, "activeModel": "claude-3"},
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


# ── Document Endpoints ─────────────────────────────────────────────────────


@patch("src.main.tenant_session")
def test_admin_list_documents(mock_ts) -> None:
    """GET /v1/admin/tenants/{id}/documents returns document list."""
    db_session = AsyncMock()
    mock_ts.return_value.__aenter__.return_value = db_session
    mock_result = MagicMock()
    now = datetime.now()
    mock_result.scalars.return_value.all.return_value = [
        SimpleNamespace(
            document_id=uuid.uuid4(),
            filename="report.pdf",
            file_size=2048,
            mime_type="application/pdf",
            status="completed",
            created_at=now,
            updated_at=now,
        )
    ]
    db_session.execute = AsyncMock(return_value=mock_result)
    response = client.get(f"/v1/admin/tenants/{tenant_id}/documents", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["filename"] == "report.pdf"
    assert body[0]["fileSize"] == 2048
    assert body[0]["status"] == "completed"


@patch("src.main.tenant_session")
def test_admin_list_documents_empty(mock_ts) -> None:
    """GET /v1/admin/tenants/{id}/documents returns empty list."""
    db_session = AsyncMock()
    mock_ts.return_value.__aenter__.return_value = db_session
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db_session.execute = AsyncMock(return_value=mock_result)
    response = client.get(f"/v1/admin/tenants/{tenant_id}/documents", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == []


# ── Prompt Template Endpoints ──────────────────────────────────────────────


@patch("src.main.template_registry.list_templates")
def test_admin_list_prompts(mock_list) -> None:
    """GET /v1/admin/tenants/{id}/prompts returns prompt list."""
    mock_list.return_value = [
        PromptTemplate(name="qa", content="Answer the question.", is_system_prompt=True),
        PromptTemplate(name="chat", content="Chat with user.", is_system_prompt=False),
    ]
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/prompts", headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["name"] == "qa"
    assert body[0]["isSystemPrompt"] is True


@patch("src.main.template_registry.list_templates")
def test_admin_list_prompts_empty(mock_list) -> None:
    """GET /v1/admin/tenants/{id}/prompts returns empty list."""
    mock_list.return_value = []
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/prompts", headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json() == []


@patch("src.main.template_registry.get_template")
@patch("src.main.template_registry.save_template")
def test_admin_create_prompt(mock_save, mock_get) -> None:
    """POST /v1/admin/tenants/{id}/prompts creates and returns 201."""
    mock_get.return_value = None
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/prompts",
        json={"name": "my-prompt", "content": "Hello {name}", "is_system_prompt": False},
        headers=auth_header,
    )
    assert response.status_code == 201
    assert response.json() == {"name": "my-prompt", "status": "created"}
    mock_save.assert_awaited_once()


@patch("src.main.template_registry.get_template")
def test_admin_create_prompt_duplicate(mock_get) -> None:
    """POST /v1/admin/tenants/{id}/prompts returns 409 on duplicate name."""
    mock_get.return_value = PromptTemplate(name="dup", content="exists")
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/prompts",
        json={"name": "dup", "content": "anything"},
        headers=auth_header,
    )
    assert response.status_code == 409


@patch("src.main.template_registry.get_template")
def test_admin_get_prompt(mock_get) -> None:
    """GET /v1/admin/tenants/{id}/prompts/{name} returns prompt."""
    mock_get.return_value = PromptTemplate(
        name="greeting", content="Hi {name}!", is_system_prompt=False,
    )
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/prompts/greeting", headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "greeting"
    assert body["content"] == "Hi {name}!"
    assert body["isSystemPrompt"] is False


@patch("src.main.template_registry.get_template")
def test_admin_get_prompt_not_found(mock_get) -> None:
    """GET /v1/admin/tenants/{id}/prompts/{name} returns 404."""
    mock_get.return_value = None
    response = client.get(
        f"/v1/admin/tenants/{tenant_id}/prompts/missing", headers=auth_header,
    )
    assert response.status_code == 404


@patch("src.main.template_registry.get_template")
@patch("src.main.template_registry.save_template")
def test_admin_update_prompt(mock_save, mock_get) -> None:
    """PUT /v1/admin/tenants/{id}/prompts/{name} updates and returns status."""
    mock_get.return_value = PromptTemplate(name="old", content="old")
    response = client.put(
        f"/v1/admin/tenants/{tenant_id}/prompts/old",
        json={"name": "old", "content": "new content", "is_system_prompt": False},
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json() == {"name": "old", "status": "updated"}
    mock_save.assert_awaited_once()


@patch("src.main.template_registry.get_template")
def test_admin_update_prompt_not_found(mock_get) -> None:
    """PUT /v1/admin/tenants/{id}/prompts/{name} returns 404."""
    mock_get.return_value = None
    response = client.put(
        f"/v1/admin/tenants/{tenant_id}/prompts/missing",
        json={"name": "missing", "content": "nope"},
        headers=auth_header,
    )
    assert response.status_code == 404


@patch("src.main.template_registry.delete_template")
def test_admin_delete_prompt(mock_delete) -> None:
    """DELETE /v1/admin/tenants/{id}/prompts/{name} deletes and returns status."""
    mock_delete.return_value = True
    response = client.delete(
        f"/v1/admin/tenants/{tenant_id}/prompts/to-delete", headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json() == {"name": "to-delete", "status": "deleted"}


@patch("src.main.template_registry.delete_template")
def test_admin_delete_prompt_not_found(mock_delete) -> None:
    """DELETE /v1/admin/tenants/{id}/prompts/{name} returns 404."""
    mock_delete.return_value = False
    response = client.delete(
        f"/v1/admin/tenants/{tenant_id}/prompts/missing", headers=auth_header,
    )
    assert response.status_code == 404


@patch("src.main.inference_orchestrator.prompt_builder.build_messages")
def test_admin_preview_prompt(mock_build) -> None:
    """POST /v1/admin/tenants/{id}/prompts/preview returns rendered messages."""
    mock_build.return_value = [
        SimpleNamespace(role="system", content="You are a helpful assistant."),
        SimpleNamespace(role="user", content="What is Paris?"),
    ]
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/prompts/preview",
        json={"name": "default", "query": "What is Paris?"},
        headers=auth_header,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["content"] == "What is Paris?"


@patch("src.main.inference_orchestrator.prompt_builder.build_messages")
def test_admin_preview_prompt_not_found(mock_build) -> None:
    """POST /v1/admin/tenants/{id}/prompts/preview returns 404 for missing template."""
    mock_build.side_effect = PromptTemplateNotFoundError(tenant_id, "missing")
    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/prompts/preview",
        json={"name": "missing", "query": "hello"},
        headers=auth_header,
    )
    assert response.status_code == 404


# ── Audit Log Endpoints ────────────────────────────────────────────────────


@patch("src.main.audit_logger.list")
def test_admin_list_audit_logs(mock_list) -> None:
    """GET /v1/admin/audit-logs returns paginated audit entries."""
    mock_list.return_value = (
        [
            {
                "logId": "l1",
                "tenantId": tenant_id,
                "action": "tenant.created",
                "details": "Tenant created",
                "createdAt": "2026-01-01T00:00:00",
            }
        ],
        1,
    )
    response = client.get("/v1/admin/audit-logs", headers=auth_header)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["action"] == "tenant.created"


@patch("src.main.audit_logger.list")
def test_admin_list_audit_logs_empty(mock_list) -> None:
    """GET /v1/admin/audit-logs returns empty list."""
    mock_list.return_value = ([], 0)
    response = client.get("/v1/admin/audit-logs", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


@patch("src.main.audit_logger.list")
def test_admin_list_audit_logs_filtered(mock_list) -> None:
    """GET /v1/admin/audit-logs passes query params to repository."""
    mock_list.return_value = ([], 0)
    client.get(
        f"/v1/admin/audit-logs?tenantId={tenant_id}&action=tenant.created&limit=10&offset=5",
        headers=auth_header,
    )
    mock_list.assert_awaited_once_with(
        tenant_id=tenant_id, action="tenant.created", limit=10, offset=5,
    )
