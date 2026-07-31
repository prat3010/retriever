"""Unit tests for Milestone 29: A/B Testing Platform."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.abstractions.experiment import ExperimentConfig, VariantConfig
from src.domain.retrieval.experiment_service import assign_variant
from src.main import app

client = TestClient(app)


# ── 1. Experiment Status Filtering ───────────────────────────────────────────


def test_assign_variant_status_filtering() -> None:
    """Verify assign_variant only assigns variants for active experiments."""
    variant_a = VariantConfig(id="var_a", name="Variant A", traffic_pct=50.0)
    variant_b = VariantConfig(id="var_b", name="Variant B", traffic_pct=50.0)

    # Draft status -> None
    draft_exp = ExperimentConfig(
        id="exp_1", name="Test Exp", status="draft", variants=[variant_a, variant_b]
    )
    assert assign_variant("user_1", draft_exp) is None

    # Paused status -> None
    paused_exp = ExperimentConfig(
        id="exp_1", name="Test Exp", status="paused", variants=[variant_a, variant_b]
    )
    assert assign_variant("user_1", paused_exp) is None

    # Active status -> Returns a variant
    active_exp = ExperimentConfig(
        id="exp_1", name="Test Exp", status="active", variants=[variant_a, variant_b]
    )
    assigned = assign_variant("user_1", active_exp)
    assert assigned is not None
    assert assigned.id in ["var_a", "var_b"]


# ── 2. Admin Experiment Lifecycle CRUD APIs ───────────────────────────────────


@patch("src.config.settings.ADMIN_MASTER_KEY", "test-admin-secret-key")
@patch("src.routers.admin.audit_logger")
@patch("src.routers.admin.config_service")
def test_admin_experiment_lifecycle_crud(mock_config_service, mock_audit) -> None:
    """Verify Admin CRUD endpoints: create, list, get, update, status change, delete."""
    headers = {"X-Admin-Master-Key": "test-admin-secret-key"}
    tenant_id = "tenant_ab_test"

    from unittest.mock import AsyncMock

    from src.domain.abstractions.config import TenantConfiguration

    fake_config = TenantConfiguration(tenant_id=tenant_id)
    mock_config_service.get_tenant_config = AsyncMock(return_value=fake_config)
    mock_config_service.update_tenant_config = AsyncMock(return_value=None)
    mock_audit.write = AsyncMock(return_value=None)

    # Create Experiment
    create_payload = {
        "name": "LLM Provider Comparison",
        "description": "Comparing GPT-4o-mini vs Gemini-2.5-flash",
        "variants": [
            {"id": "var_gpt", "name": "GPT-4o Mini", "traffic_pct": 50.0, "overrides": {}},
            {"id": "var_gemini", "name": "Gemini 2.5 Flash", "traffic_pct": 50.0, "overrides": {}},
        ],
    }

    create_res = client.post(
        f"/v1/admin/tenants/{tenant_id}/experiments",
        headers=headers,
        json=create_payload,
    )
    assert create_res.status_code == 201
    exp_data = create_res.json()
    exp_id = exp_data["id"]
    assert exp_data["name"] == "LLM Provider Comparison"
    assert exp_data["status"] == "draft"

    # List Experiments
    list_res = client.get(f"/v1/admin/tenants/{tenant_id}/experiments", headers=headers)
    assert list_res.status_code == 200
    assert any(e["id"] == exp_id for e in list_res.json())

    # Get Single Experiment
    get_res = client.get(f"/v1/admin/tenants/{tenant_id}/experiments/{exp_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == exp_id

    # Update Experiment
    update_res = client.put(
        f"/v1/admin/tenants/{tenant_id}/experiments/{exp_id}",
        headers=headers,
        json={"name": "Updated Provider Comparison"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Provider Comparison"

    # Activate Experiment
    status_res = client.post(
        f"/v1/admin/tenants/{tenant_id}/experiments/{exp_id}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "active"

    # Delete Experiment
    del_res = client.delete(f"/v1/admin/tenants/{tenant_id}/experiments/{exp_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify Deletion
    get_del_res = client.get(f"/v1/admin/tenants/{tenant_id}/experiments/{exp_id}", headers=headers)
    assert get_del_res.status_code == 404


@patch("src.config.settings.ADMIN_MASTER_KEY", "test-admin-secret-key")
@patch("src.adapters.database.connection.tenant_session")
@patch("src.routers.admin.config_service")
def test_admin_experiment_metrics(mock_config_service, mock_tenant_session) -> None:
    """Verify GET /v1/admin/tenants/{tenantId}/experiments/{experimentId}/metrics."""
    from unittest.mock import AsyncMock, MagicMock

    from src.domain.abstractions.config import TenantConfiguration

    headers = {"X-Admin-Master-Key": "test-admin-secret-key"}
    tenant_id = "00000000-0000-0000-0000-000000000001"

    variant_a = VariantConfig(id="var_a", name="Variant A", traffic_pct=50.0)
    variant_b = VariantConfig(id="var_b", name="Variant B", traffic_pct=50.0)
    exp = ExperimentConfig(
        id="exp_123", name="Search Test", status="active", variants=[variant_a, variant_b]
    )

    fake_config = TenantConfiguration(tenant_id=tenant_id, experiments=[exp])
    mock_config_service.get_tenant_config = AsyncMock(return_value=fake_config)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    res = client.get(
        f"/v1/admin/tenants/{tenant_id}/experiments/exp_123/metrics",
        headers=headers,
    )

    assert res.status_code == 200
    body = res.json()
    assert body["experimentId"] == "exp_123"
    assert body["status"] == "active"
    assert len(body["variants"]) == 2
    assert body["variants"][0]["variantId"] == "var_a"
    assert body["variants"][1]["variantId"] == "var_b"
