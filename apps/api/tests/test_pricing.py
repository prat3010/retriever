from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

ADMIN_KEY = "dev-admin-master-key-change-in-production"
auth_header = {"X-Admin-Master-Key": ADMIN_KEY}


def test_get_pricing_config_returns_defaults() -> None:
    """Verify GET /v1/config/pricing returns active pricing configuration."""
    response = client.get("/v1/config/pricing")
    assert response.status_code == 200
    data = response.json()
    assert "inr" in data
    assert "usd" in data
    assert len(data["inr"]["plans"]) == 3
    assert len(data["usd"]["plans"]) == 3
    assert data["inr"]["plans"][0]["price"] == "1,999"
    assert data["usd"]["plans"][0]["price"] == "29"


@patch("src.routers.pricing.tenant_session")
def test_update_pricing_config_admin(mock_tenant_session) -> None:
    """Verify PUT /v1/admin/config/pricing updates pricing configuration when authorized as admin."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    updated_payload = {
        "inr": {"currency": "INR", "symbol": "₹", "plans": []},
        "usd": {"currency": "USD", "symbol": "$", "plans": []},
    }

    # Verify 401 without admin key
    unauth_resp = client.put("/v1/admin/config/pricing", json={"pricing": updated_payload})
    assert unauth_resp.status_code == 401

    # Verify 200 with admin key
    auth_resp = client.put(
        "/v1/admin/config/pricing",
        json={"pricing": updated_payload},
        headers=auth_header,
    )
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["status"] == "updated"
