import datetime
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, status
from fastapi.security import SecurityScopes
from workers.src.tasks import cleanup_expired_data

from src.adapters.api.security import get_current_user, verify_scopes
from src.adapters.database.audit_repository import SqlAuditLogRepository
from src.config import settings
from src.domain.abstractions.exceptions import AuthenticationError
from src.domain.abstractions.identity import UserContext


# Helper to generate RSA key pair for testing OIDC signatures
@pytest.fixture(scope="module")
def rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    
    # Serialize private key to PEM
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key numbers for JWK
    numbers = public_key.public_numbers()
    import base64
    def int_to_b64(value):
        value_hex = format(value, 'x')
        if len(value_hex) % 2 == 1:
            value_hex = '0' + value_hex
        value_bytes = bytes.fromhex(value_hex)
        return base64.urlsafe_b64encode(value_bytes).decode('utf-8').rstrip('=')
        
    jwk = {
        "kty": "RSA",
        "kid": "test-key-id",
        "use": "sig",
        "alg": "RS256",
        "n": int_to_b64(numbers.n),
        "e": int_to_b64(numbers.e)
    }
    
    return pem_private, jwk


@pytest.mark.asyncio
@patch("src.adapters.database.audit_repository.tenant_session")
async def test_cryptographic_audit_chain_verification(mock_session_factory) -> None:
    repo = SqlAuditLogRepository()
    tenant_id = str(uuid.uuid4())
    
    # Simulate DB records list
    records = []
    
    # Mock tenant session as MagicMock so non-async methods aren't coroutines
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory.return_value = mock_ctx
    
    # Mock session add to save entries
    def add_side_effect(obj):
        records.append(obj)
        
    mock_session.add.side_effect = add_side_effect
    
    # Fetch first returns None (first write)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Write first log entry
    await repo.write(tenant_id, "user.login", "User successfully authenticated.")
    assert len(records) == 1
    assert records[0].previous_hash == "0" * 64
    assert records[0].entry_hash is not None
    
    # Mock next fetch returning the first record
    mock_result_2 = MagicMock()
    mock_result_2.scalars.return_value.first.return_value = records[0]
    mock_session.execute.return_value = mock_result_2
    
    # Write second log entry
    await repo.write(tenant_id, "document.upload", "contract.pdf uploaded.")
    assert len(records) == 2
    assert records[1].previous_hash == records[0].entry_hash
    
    # Verify chain integrity
    mock_result_3 = MagicMock()
    mock_result_3.scalars.return_value.all.return_value = records
    mock_session.execute.return_value = mock_result_3
    
    is_valid = await repo.verify_audit_chain(tenant_id)
    assert is_valid is True
    
    # Tamper with the chain by altering details of the first record
    records[0].details = "Tampered login details."
    
    is_valid_after_tamper = await repo.verify_audit_chain(tenant_id)
    assert is_valid_after_tamper is False


@pytest.mark.asyncio
@patch("src.adapters.api.security._fetch_jwks_key", new_callable=AsyncMock)
async def test_oidc_authentication_validation(mock_fetch_jwk, rsa_keys) -> None:
    pem_private, jwk = rsa_keys
    mock_fetch_jwk.return_value = jwk
    
    tenant_uuid = str(uuid.uuid4())
    payload = {
        "iss": "https://auth.example.com",
        "sub": "user-sso-123",
        "aud": "retriever-api",
        "tenant_id": tenant_uuid,
        "roles": ["client"],
        "scopes": ["document:read"],
        "exp": int(datetime.datetime.now(datetime.UTC).timestamp()) + 3600
    }
    
    # Generate token
    token = jwt.encode(payload, pem_private, algorithm="RS256", headers={"kid": "test-key-id"})
    
    # Set settings
    original_issuer = settings.OIDC_ISSUER_URL
    original_jwks = settings.OIDC_JWKS_URI
    original_aud = settings.OIDC_AUDIENCE
    
    settings.OIDC_ISSUER_URL = "https://auth.example.com"
    settings.OIDC_JWKS_URI = "https://auth.example.com/.well-known/jwks.json"
    settings.OIDC_AUDIENCE = "retriever-api"
    
    try:
        # Patch identity provider validate_token to raise AuthenticationError (simulate no API Key match)
        with patch("src.adapters.api.security.identity_provider.validate_token", side_effect=AuthenticationError("No API Key match")):
            user_context = await get_current_user(f"Bearer {token}")
            
            assert user_context.user_id == "user-sso-123"
            assert user_context.tenant_id == tenant_uuid
            assert "client" in user_context.roles
            assert "document:read" in user_context.scopes
            
            # Verify validation fails on expired token
            payload_expired = payload.copy()
            payload_expired["exp"] = int(datetime.datetime.now(datetime.UTC).timestamp()) - 100
            token_expired = jwt.encode(payload_expired, pem_private, algorithm="RS256", headers={"kid": "test-key-id"})
            
            with pytest.raises(HTTPException) as exc:
                await get_current_user(f"Bearer {token_expired}")
            assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
            
    finally:
        settings.OIDC_ISSUER_URL = original_issuer
        settings.OIDC_JWKS_URI = original_jwks
        settings.OIDC_AUDIENCE = original_aud


@patch("workers.src.tasks.get_engine")
def test_data_retention_scheduler_purging(mock_get_engine) -> None:
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx
    
    # Mock configuration select
    tenant_id = str(uuid.uuid4())
    config_dict = {
        "security_settings": {
            "data_retention_ttl_days": 15
        }
    }
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(tenant_id, json.dumps(config_dict))]
    mock_conn.execute.return_value = mock_result
    
    # Run maintenance task (run synchronously, no event loop running error)
    cleanup_expired_data()
    
    # Verify DB deletes were run for this tenant
    delete_runs = 0
    for call in mock_conn.execute.call_args_list:
        arg = call[0][0]
        if hasattr(arg, "text") and "DELETE FROM" in arg.text:
            params = call[0][1]
            assert params["tenant_id"] == tenant_id
            assert params["ttl_interval"] == "15 days"
            delete_runs += 1
            
    assert delete_runs == 2  # Documents + Chat sessions


@pytest.mark.asyncio
async def test_granular_rbac_scope_checking() -> None:
    user_context = UserContext(
        user_id="user-123",
        tenant_id="tenant-123",
        roles=["client"],
        scopes=["collection:finance:read", "document_type:pdf:write"]
    )
    
    # Test 1: Query param collection match allows read
    mock_request = MagicMock()
    mock_request.query_params = {"collection": "finance"}
    mock_request.json = AsyncMock(return_value={})
    
    security_scopes = SecurityScopes(scopes=["document:read"])
    # Should not raise exception
    await verify_scopes(security_scopes, user_context, mock_request)
    
    # Test 2: Mismatched collection query parameter denies read
    mock_request_bad = MagicMock()
    mock_request_bad.query_params = {"collection": "legal"}
    mock_request_bad.json = AsyncMock(return_value={})
    
    with pytest.raises(HTTPException) as exc:
        await verify_scopes(security_scopes, user_context, mock_request_bad)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    
    # Test 3: Document type matches filename extension allows write
    mock_request_write = MagicMock()
    mock_request_write.query_params = {}
    mock_request_write.json = AsyncMock(return_value={"filename": "report.pdf"})
    
    security_scopes_write = SecurityScopes(scopes=["document:write"])
    # Should allow
    await verify_scopes(security_scopes_write, user_context, mock_request_write)
