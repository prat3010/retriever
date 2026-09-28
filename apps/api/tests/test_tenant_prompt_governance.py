"""Tests for Tenant-Scoped Master System Prompt & Governance Policy Lock."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.adapters.api.security import verify_tenant_isolation
from src.config import settings
from src.domain.abstractions.inference import PromptTemplate
from src.main import app

client = TestClient(app)

ADMIN_KEY = settings.ADMIN_MASTER_KEY
admin_header = {"X-Admin-Master-Key": ADMIN_KEY}


@pytest.fixture
def test_tenant_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def override_tenant_isolation():
    app.dependency_overrides[verify_tenant_isolation] = lambda: None
    yield
    app.dependency_overrides.pop(verify_tenant_isolation, None)


def test_get_tenant_default_prompt_returns_fallback_if_missing(test_tenant_id: str):
    """If no prompt exists yet, get default prompt returns fallback prompt with isLocked=False."""
    with patch("src.routers.tenant.template_registry.get_template", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        response = client.get(f"/v1/tenants/{test_tenant_id}/prompts/default")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "default"
        assert "enterprise AI assistant" in data["content"]
        assert data["isLocked"] is False
        assert data["isSystemPrompt"] is True


def test_get_tenant_default_prompt_returns_existing(test_tenant_id: str):
    """Returns the existing prompt and its isLocked status."""
    mock_template = PromptTemplate(
        prompt_id=str(uuid.uuid4()),
        tenant_id=test_tenant_id,
        name="default",
        content="You are a strict compliance auditor.",
        is_system_prompt=True,
        is_locked=True,
    )
    with patch("src.routers.tenant.template_registry.get_template", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_template

        response = client.get(f"/v1/tenants/{test_tenant_id}/prompts/default")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "default"
        assert data["content"] == "You are a strict compliance auditor."
        assert data["isLocked"] is True


def test_update_tenant_default_prompt_unlocked_succeeds(test_tenant_id: str):
    """When is_locked is False, tenant can successfully update master system prompt."""
    existing_template = PromptTemplate(
        prompt_id=str(uuid.uuid4()),
        tenant_id=test_tenant_id,
        name="default",
        content="Original prompt",
        is_system_prompt=True,
        is_locked=False,
    )
    with (
        patch("src.routers.tenant.template_registry.get_template", new_callable=AsyncMock) as mock_get,
        patch("src.routers.tenant.template_registry.save_template", new_callable=AsyncMock) as mock_save,
        patch("src.routers.tenant.audit_logger.write", new_callable=AsyncMock) as mock_audit,
    ):
        mock_get.return_value = existing_template

        new_content = "You are a friendly e-commerce support concierge."
        response = client.put(
            f"/v1/tenants/{test_tenant_id}/prompts/default",
            json={"content": new_content},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "default"
        assert data["content"] == new_content
        assert data["isLocked"] is False

        mock_save.assert_called_once()
        saved_template = mock_save.call_args[0][1]
        assert saved_template.content == new_content
        assert saved_template.is_locked is False
        mock_audit.assert_called_once()


def test_update_tenant_default_prompt_locked_rejected_403(test_tenant_id: str):
    """When is_locked is True, tenant update is rejected with HTTP 403 Forbidden."""
    existing_locked_template = PromptTemplate(
        prompt_id=str(uuid.uuid4()),
        tenant_id=test_tenant_id,
        name="default",
        content="Locked enterprise prompt",
        is_system_prompt=True,
        is_locked=True,
    )
    with (
        patch("src.routers.tenant.template_registry.get_template", new_callable=AsyncMock) as mock_get,
        patch("src.routers.tenant.template_registry.save_template", new_callable=AsyncMock) as mock_save,
    ):
        mock_get.return_value = existing_locked_template

        response = client.put(
            f"/v1/tenants/{test_tenant_id}/prompts/default",
            json={"content": "Attempting unauthorized prompt overwrite"},
        )
        assert response.status_code == 403
        assert "locked by cluster administrator policy" in response.json()["detail"]
        mock_save.assert_not_called()


def test_admin_can_lock_and_unlock_prompts(test_tenant_id: str):
    """Cluster admin can update prompt and toggle is_locked status."""
    existing_template = PromptTemplate(
        prompt_id=str(uuid.uuid4()),
        tenant_id=test_tenant_id,
        name="default",
        content="Default prompt",
        is_system_prompt=True,
        is_locked=False,
    )
    with (
        patch("src.routers.admin.template_registry.get_template", new_callable=AsyncMock) as mock_get,
        patch("src.routers.admin.template_registry.save_template", new_callable=AsyncMock) as mock_save,
    ):
        mock_get.return_value = existing_template

        # Admin locks prompt
        res = client.put(
            f"/v1/admin/tenants/{test_tenant_id}/prompts/default",
            headers=admin_header,
            json={
                "name": "default",
                "content": "Administrator locked prompt",
                "is_system_prompt": True,
                "is_locked": True,
            },
        )
        assert res.status_code == 200
        assert res.json() == {"name": "default", "status": "updated"}
        saved = mock_save.call_args[0][1]
        assert saved.is_locked is True
