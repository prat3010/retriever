import hashlib
import uuid
from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.adapters.database.models import ApiKeyDb
from src.config import settings
from src.main import app

client = TestClient(app)

_VALID_CLAIMS = {
    "iss": "https://accounts.google.com",
    "aud": "my-client-id.apps.googleusercontent.com",
    "sub": "google-sub-123",
    "email": "verified@example.com",
    "email_verified": True,
    "name": "Verified User",
}


@contextmanager
def _mock_verified_token(claims: dict):
    with ExitStack() as stack:
        stack.enter_context(
            patch("src.routers.auth._fetch_jwks_key", new_callable=AsyncMock, return_value={"kty": "RSA"})
        )
        stack.enter_context(patch("src.routers.auth.jwt.decode", return_value=claims))
        stack.enter_context(patch("src.routers.auth.jwt.get_unverified_header", return_value={"kid": "key-1"}))
        stack.enter_context(
            patch("src.routers.auth.jwt.algorithms.RSAAlgorithm.from_jwk", return_value=MagicMock())
        )
        yield


def _mock_db(mock_tenant_session, existing_user=None) -> MagicMock:
    mock_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_user
    mock_session.execute.return_value = result
    mock_tenant_session.return_value.__aenter__.return_value = mock_session
    return mock_session


def test_google_auth_rejects_unverified_token_in_production() -> None:
    """Unverified client-supplied tokens must never provision sessions in production."""
    with patch.object(settings, "ENVIRONMENT", "production"):
        response = client.post(
            "/v1/auth/google",
            json={
                "id_token": "mock_unverified_token",
                "email": "attacker@example.com",
                "name": "Attacker",
            },
        )

    assert response.status_code == 401


@patch("src.routers.auth.tenant_session")
def test_google_auth_dev_fallback_allows_unverified(mock_tenant_session) -> None:
    """Outside production, the unverified dev fallback remains available for local testing."""
    _mock_db(mock_tenant_session, existing_user=None)

    response = client.post(
        "/v1/auth/google",
        json={
            "id_token": "mock_unverified_token",
            "email": "devuser@example.com",
            "name": "Dev User",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "devuser@example.com"
    assert data["name"] == "Dev User"
    assert data["isNewTenant"] is True
    assert data["apiKey"].startswith("ret_live_")


@patch("src.routers.auth.tenant_session")
def test_google_auth_verified_token_provisions_tenant(mock_tenant_session) -> None:
    """A cryptographically verified Google token provisions the tenant with claims precedence."""
    _mock_db(mock_tenant_session, existing_user=None)

    with _mock_verified_token(_VALID_CLAIMS):
        response = client.post(
            "/v1/auth/google",
            json={
                "id_token": "valid.id.token",
                "email": "spoofed@example.com",
                "name": "Spoofed Name",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "verified@example.com"
    assert data["name"] == "Verified User"
    assert data["isNewTenant"] is True
    assert data["apiKey"].startswith("ret_live_")


@patch("src.routers.auth.tenant_session")
def test_google_auth_rejects_token_with_wrong_audience(mock_tenant_session) -> None:
    """ID tokens minted for a different OAuth client must be rejected."""
    claims = dict(_VALID_CLAIMS, aud="evil-client-id")

    with _mock_verified_token(claims), patch.object(
        settings, "OIDC_AUDIENCE", "my-client-id.apps.googleusercontent.com"
    ):
        response = client.post(
            "/v1/auth/google",
            json={"id_token": "valid.id.token", "email": "spoofed@example.com"},
        )

    assert response.status_code == 401
    mock_tenant_session.assert_not_called()


@patch("src.routers.auth.tenant_session")
def test_google_auth_rejects_token_with_wrong_issuer(mock_tenant_session) -> None:
    """Tokens from an unexpected issuer must be rejected."""
    claims = dict(_VALID_CLAIMS, iss="https://evil.example.com")

    with _mock_verified_token(claims):
        response = client.post("/v1/auth/google", json={"id_token": "valid.id.token"})

    assert response.status_code == 401
    mock_tenant_session.assert_not_called()


@patch("src.routers.auth.tenant_session")
def test_google_auth_existing_user_persists_new_api_key(mock_tenant_session) -> None:
    """Returned API key for a returning user must be persisted (hashed) so it actually works."""
    existing_user = MagicMock()
    existing_user.user_id = uuid.uuid4()
    existing_user.tenant_id = uuid.uuid4()
    mock_session = _mock_db(mock_tenant_session, existing_user=existing_user)

    with _mock_verified_token(_VALID_CLAIMS):
        response = client.post("/v1/auth/google", json={"id_token": "valid.id.token"})

    assert response.status_code == 200
    data = response.json()
    assert data["isNewTenant"] is False

    added = [c.args[0] for c in mock_session.add.call_args_list]
    assert len(added) == 1
    key_db: ApiKeyDb = added[0]
    assert key_db.key_hash == hashlib.sha256(data["apiKey"].encode()).hexdigest()
    assert key_db.status == "active"
    assert key_db.prefix == "ret_live_"
