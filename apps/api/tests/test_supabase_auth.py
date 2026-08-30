from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.config import settings
from src.domain.abstractions.exceptions import AuthenticationError
from src.main import app

client = TestClient(app)


def test_get_auth_session_with_api_key() -> None:
    """GET /v1/auth/session succeeds with a valid API key token."""
    from src.adapters.api.security import get_current_user
    mock_user_context = MagicMock()
    mock_user_context.tenant_id = "00000000-0000-0000-0000-000000000001"
    mock_user_context.user_id = "00000000-0000-0000-0000-00000002"
    mock_user_context.roles = ["client"]
    mock_user_context.scopes = ["document:read", "document:write"]

    app.dependency_overrides[get_current_user] = lambda: mock_user_context
    try:
        response = client.get(
            "/v1/auth/session",
            headers={"Authorization": "Bearer ret_live_validkey"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["tenantId"] == "00000000-0000-0000-0000-000000000001"
    assert data["userId"] == "00000000-0000-0000-0000-00000002"
    assert data["roles"] == ["client"]
    assert "document:read" in data["scopes"]


@patch("src.adapters.database.connection.tenant_session")
@patch("src.adapters.api.security._fetch_jwks_key")
@patch("src.adapters.api.security.jwt.decode")
@patch("src.adapters.api.security.jwt.get_unverified_header")
@patch("src.adapters.api.security.jwt.algorithms.RSAAlgorithm.from_jwk")
def test_supabase_auth_auto_provisions_unseen_user(
    mock_from_jwk,
    mock_unverified_header,
    mock_jwt_decode,
    mock_fetch_jwks,
    mock_tenant_session,
) -> None:
    """A valid Supabase JWT for an unprovisioned user triggers automatic tenant & user creation."""
    mock_unverified_header.return_value = {"kid": "supabase-key-1"}
    mock_fetch_jwks.return_value = {"kty": "RSA"}
    mock_from_jwk.return_value = MagicMock()

    mock_jwt_decode.return_value = {
        "sub": "supabase-user-uuid-123",
        "email": "supabaseuser@example.com",
        "iss": "https://test.supabase.co/auth/v1",
    }

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # User does not exist yet
    mock_session.execute.return_value = result
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    with (
        patch.object(settings, "SUPABASE_URL", "https://test.supabase.co"),
        patch("src.adapters.api.security.identity_provider.validate_token", side_effect=AuthenticationError("Not API Key")),
    ):
        response = client.get(
            "/v1/auth/session",
            headers={"Authorization": "Bearer mock.supabase.jwt"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["roles"] == ["client"]
    # Check that session.add was called for TenantDb, UserDb, and ApiKeyDb
    assert mock_session.add.call_count == 3
    assert mock_session.commit.called

