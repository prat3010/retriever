from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@patch("src.routers.auth.tenant_session")
def test_google_auth_auto_provision(mock_tenant_session) -> None:
    """Verify Google auth endpoint auto-provisions a new tenant and user on first login."""
    test_email = "testuser_auto_onboard@example.com"
    test_name = "Auto Onboard User"

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # User does not exist
    mock_session.execute.return_value = mock_result
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    response = client.post(
        "/v1/auth/google",
        json={
            "id_token": "mock_unverified_token",
            "email": test_email,
            "name": test_name,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "tenantId" in data
    assert "userId" in data
    assert "apiKey" in data
    assert data["email"] == test_email
    assert data["name"] == test_name
    assert "jwtToken" in data
    assert data["apiKey"].startswith("ret_live_")
    assert data["isNewTenant"] is True
