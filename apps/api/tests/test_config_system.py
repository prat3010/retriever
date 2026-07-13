import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.domain.abstractions.config import FeatureFlags, TenantConfiguration
from src.domain.abstractions.identity import UserContext
from src.main import app

client = TestClient(app)


def test_global_config_crud_admin_auth() -> None:
    # 1. Update Global Config
    mock_payload = TenantConfiguration(
        feature_flags=FeatureFlags(enable_hybrid_search=False)
    )
    with patch("src.main.config_service.update_global_config", new_callable=AsyncMock) as mock_update:
        headers = {"X-Admin-Master-Key": "dev-admin-master-key-change-in-production"}
        response = client.put("/v1/config/global", json=mock_payload.model_dump(), headers=headers)
        assert response.status_code == 200
        assert response.json()["scope"] == "global"
        mock_update.assert_called_once()

    # 2. Get Global Config
    mock_config = TenantConfiguration(
        feature_flags=FeatureFlags(enable_hybrid_search=False)
    )
    mock_config.ai_provider.api_key = "supersecretkey"

    with patch("src.main.config_service.get_global_config", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_config
        headers = {"X-Admin-Master-Key": "dev-admin-master-key-change-in-production"}
        response = client.get("/v1/config/global", headers=headers)
        assert response.status_code == 200
        # Assert secrets are redacted
        assert response.json()["ai_provider"]["api_key"] == "********"
        assert response.json()["feature_flags"]["enable_hybrid_search"] is False


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
def test_tenant_config_inheritance_override(mock_validate) -> None:
    tenant_id = "tnt_999"
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )

    mock_merged_config = TenantConfiguration(
        tenant_id=tenant_id,
        feature_flags=FeatureFlags(enable_hybrid_search=False)  # overridden value
    )
    mock_merged_config.ai_provider.api_key = "secret_key"

    with patch("src.main.config_service.get_tenant_config", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_merged_config
        headers = {"Authorization": "Bearer ret_live_somekey.secretpart"}
        response = client.get(f"/v1/tenants/{tenant_id}/config", headers=headers)
        assert response.status_code == 200
        assert response.json()["feature_flags"]["enable_hybrid_search"] is False
        # Verify secret redaction
        assert response.json()["ai_provider"]["api_key"] == "********"


def test_env_resolution_fallback_logic() -> None:
    from unittest.mock import MagicMock

    from src.domain.config.config_service import ConfigurationService
    service = ConfigurationService(registry=MagicMock(), cache=MagicMock())

    config = TenantConfiguration()
    config.ai_provider.provider_name = "openai"
    config.ai_provider.api_key = "********"  # placeholder

    # Inject mock environment key
    with patch.dict(os.environ, {"OPENAI_API_KEY": "env-resolved-key-value"}):
        resolved = service._resolve_env_variables(config)
        assert resolved.ai_provider.api_key == "env-resolved-key-value"


def test_merge_configurations_overlay() -> None:
    from unittest.mock import MagicMock

    from src.domain.config.config_service import ConfigurationService
    service = ConfigurationService(registry=MagicMock(), cache=MagicMock())

    base_config = TenantConfiguration(
        feature_flags=FeatureFlags(enable_hybrid_search=True, enable_reranking=True)
    )
    # Tenant only overrides enable_hybrid_search to False
    override_config = TenantConfiguration(
        feature_flags=FeatureFlags(enable_hybrid_search=False)
    )

    merged = service._merge_configurations(base_config, override_config)
    assert merged.feature_flags.enable_hybrid_search is False
    # enable_reranking should inherit True from base
    assert merged.feature_flags.enable_reranking is True
