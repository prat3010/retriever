from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.tenant import Tenant
from src.main import app

client = TestClient(app)


def test_create_tenant_success() -> None:
    mock_tenant = Tenant(
        tenant_id="tnt_abc123",
        name="Test Corporate Workspace",
        status="active",
        tier="enterprise",
        created_at="2026-07-12T07:56:14Z",
    )

    with patch("src.main.tenant_registry.create_tenant", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_tenant
        headers = {"X-Admin-Master-Key": "dev-admin-master-key-change-in-production"}
        response = client.post(
            "/v1/tenants",
            json={"name": "Test Corporate Workspace", "tier": "enterprise", "isolation_level": "logical"},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["tenant_id"] == "tnt_abc123"
        mock_create.assert_called_once_with(name="Test Corporate Workspace", tier="enterprise", isolation_level="logical")


def test_create_tenant_unauthorized() -> None:
    headers = {"X-Admin-Master-Key": "incorrect-key"}
    response = client.post(
        "/v1/tenants",
        json={"name": "Acme Corp"},
        headers=headers,
    )
    assert response.status_code == 401
    assert "Invalid administrative master key" in response.json()["detail"]


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
def test_verify_tenant_isolation_breach(mock_validate) -> None:
    # Key belongs to Tenant A
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id="tenant_A",
        roles=["integrator"],
        scopes=["query:execute", "document:read"],
    )

    # Key deactivation check
    with patch("src.adapters.api.security.tenant_session") as mock_session:
        mock_db_session = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db_session

        headers = {"Authorization": "Bearer ret_live_badkey.secretpart"}
        # Accessing Tenant B config
        response = client.get("/v1/tenants/tenant_B/config", headers=headers)
        
        assert response.status_code == 403
        assert "boundary violation" in response.json()["detail"]
        # Confirm deactivation update was executed on db
        mock_db_session.execute.assert_called()
