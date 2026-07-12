from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.domain.abstractions.identity import UserContext, ApiKeyMetadata
from src.domain.abstractions.tenant import Tenant, TenantConfig

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


@patch("src.domain.identity.security.identity_provider.validate_token", new_callable=AsyncMock)
def test_get_config_cache_hit(mock_validate) -> None:
    tenant_id = "tnt_800f72a0-0a20-475f-b2e2-f1eaeffc2a58"
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["query:execute"],
    )

    mock_config = TenantConfig(
        tenant_id=tenant_id,
        active_model="claude-3-5-sonnet",
        temperature=0.2,
        chunk_size=500,
        chunk_overlap=100,
        system_prompt_template="Test instruction set",
    )

    with patch("src.main.config_cache.get_cached_config", new_callable=AsyncMock) as mock_cache_get, \
         patch("src.main.tenant_registry.get_config", new_callable=AsyncMock) as mock_db_get:
        
        mock_cache_get.return_value = mock_config
        
        headers = {"Authorization": "Bearer ret_live_validkey.secretpart"}
        response = client.get(f"/v1/tenants/{tenant_id}/config", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["active_model"] == "claude-3-5-sonnet"
        mock_cache_get.assert_called_once_with(tenant_id)
        mock_db_get.assert_not_called()


@patch("src.domain.identity.security.identity_provider.validate_token", new_callable=AsyncMock)
def test_get_config_cache_miss(mock_validate) -> None:
    tenant_id = "tnt_800f72a0-0a20-475f-b2e2-f1eaeffc2a58"
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["query:execute"],
    )

    mock_config = TenantConfig(
        tenant_id=tenant_id,
        active_model="claude-3-5-sonnet",
        temperature=0.2,
        chunk_size=500,
        chunk_overlap=100,
        system_prompt_template="Test instruction set",
    )

    with patch("src.main.config_cache.get_cached_config", new_callable=AsyncMock) as mock_cache_get, \
         patch("src.main.tenant_registry.get_config", new_callable=AsyncMock) as mock_db_get, \
         patch("src.main.config_cache.set_cached_config", new_callable=AsyncMock) as mock_cache_set:
        
        mock_cache_get.return_value = None
        mock_db_get.return_value = mock_config
        
        headers = {"Authorization": "Bearer ret_live_validkey.secretpart"}
        response = client.get(f"/v1/tenants/{tenant_id}/config", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["system_prompt_template"] == "Test instruction set"
        mock_cache_get.assert_called_once_with(tenant_id)
        mock_db_get.assert_called_once_with(tenant_id)
        mock_cache_set.assert_called_once_with(tenant_id, mock_config)


@patch("src.domain.identity.security.identity_provider.validate_token", new_callable=AsyncMock)
def test_verify_tenant_isolation_breach(mock_validate) -> None:
    # Key belongs to Tenant A
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id="tenant_A",
        roles=["integrator"],
        scopes=["query:execute"],
    )

    # Key deactivation check
    with patch("src.domain.identity.security.tenant_session") as mock_session:
        mock_db_session = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db_session

        headers = {"Authorization": "Bearer ret_live_badkey.secretpart"}
        # Accessing Tenant B config
        response = client.get("/v1/tenants/tenant_B/config", headers=headers)
        
        assert response.status_code == 403
        assert "boundary violation" in response.json()["detail"]
        # Confirm deactivation update was executed on db
        mock_db_session.execute.assert_called()
