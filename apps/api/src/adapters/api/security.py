import hashlib
import json
import re
import secrets
import sys
import httpx
import jwt
from jwt.exceptions import PyJWTError

from fastapi import Depends, Header, HTTPException, Security, Request, status
from fastapi.security import APIKeyHeader, SecurityScopes

from src.adapters.database.identity_repository import SqlIdentityProvider
from src.config import settings
from src.domain.abstractions.exceptions import (
    AuthenticationError,
    TenantIsolationViolationError,
)
from src.domain.abstractions.identity import UserContext

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# Header key selector
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
identity_provider = SqlIdentityProvider()

# In-memory JWKS cache
_jwks_cache = {}


async def _fetch_jwks_key(jwks_uri: str, kid: str) -> dict | None:
    if jwks_uri in _jwks_cache:
        if kid in _jwks_cache[jwks_uri]:
            return _jwks_cache[jwks_uri][kid]
            
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(jwks_uri, timeout=5.0)
            if res.status_code == 200:
                jwks = res.json()
                keys = jwks.get("keys", [])
                _jwks_cache[jwks_uri] = {}
                for key in keys:
                    if "kid" in key:
                        _jwks_cache[jwks_uri][key["kid"]] = key
                return _jwks_cache[jwks_uri].get(kid)
    except Exception:
        pass
    return None


async def get_current_user(token: str | None = Security(api_key_header)) -> UserContext:
    """Validate incoming Bearer API key token or OIDC JWT token and return active UserContext."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization API key or SSO token is missing.",
        )

    clean_token = token
    if token.lower().startswith("bearer "):
        clean_token = token[7:]

    # 1. Try validating as internal API key
    try:
        return await identity_provider.validate_token(clean_token)
    except AuthenticationError as e:
        # 2. Try validating as OIDC JWT token if OIDC is configured
        if settings.OIDC_ISSUER_URL and settings.OIDC_JWKS_URI:
            try:
                unverified_header = jwt.get_unverified_header(clean_token)
                kid = unverified_header.get("kid")
                if kid:
                    jwk = await _fetch_jwks_key(settings.OIDC_JWKS_URI, kid)
                    if jwk:
                        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                        payload = jwt.decode(
                            clean_token,
                            public_key,
                            algorithms=["RS256"],
                            audience=settings.OIDC_AUDIENCE,
                            issuer=settings.OIDC_ISSUER_URL
                        )
                        tenant_id = payload.get("tenant_id") or payload.get("custom:tenant_id")
                        user_id = payload.get("sub")
                        roles = payload.get("roles", ["client"])
                        scopes = payload.get("scopes", ["document:read"])
                        
                        if not tenant_id:
                            raise AuthenticationError("SSO token missing required tenant context claim.")
                            
                        return UserContext(
                            user_id=user_id,
                            tenant_id=tenant_id,
                            roles=roles,
                            scopes=scopes
                        )
            except PyJWTError as je:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"SSO Token validation failed: {str(je)}",
                )
            except AuthenticationError as ae:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(ae),
                )
        
        # Raise the original validation failure if OIDC is disabled or did not match
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


async def get_current_user_id(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    user_context: UserContext = Depends(get_current_user),
) -> str | None:
    """Extract X-User-ID from request headers.

    Returns None for admin API keys (bypass user scoping).
    Raises 401 if X-User-ID is missing for client API keys.
    """
    is_admin = "admin" in user_context.roles
    if not is_admin and not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is required for client API keys.",
        )
    if x_user_id and not _UUID_RE.match(x_user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-User-ID must be a valid UUID.",
        )
    return x_user_id


async def verify_tenant_isolation(
    tenantId: str,
    user_context: UserContext = Depends(get_current_user),
    token: str | None = Security(api_key_header),
) -> None:
    """Compare authenticated context tenant_id against path parameters.

    Triggers the Tenancy Breach Kill-Switch on mismatches.
    """
    if "admin" in user_context.roles:
        return

    if user_context.tenant_id != tenantId:
        # LOG CRITICAL SECURITY BREACH (Structured JSON out to stderr)
        log_payload = {
            "level": "FATAL",
            "incident": "CRITICAL_SECURITY_BREACH",
            "authenticated_tenant": user_context.tenant_id,
            "target_tenant": tenantId,
            "message": "Tenant mismatch detected! Initiating Key Revocation Kill-Switch.",
        }
        print(json.dumps(log_payload), file=sys.stderr)

        # Invalidate key immediately if token is available
        if token:
            clean_token = token
            if token.lower().startswith("bearer "):
                clean_token = token[7:]
            key_hash = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()
            await identity_provider.revoke_api_key_by_hash(key_hash)

        raise TenantIsolationViolationError(
            "Access Denied: Tenancy boundary violation detected."
        )


async def verify_scopes(
    security_scopes: SecurityScopes,
    user_context: UserContext = Depends(get_current_user),
    request: Request = None,
) -> None:
    """Enforce Role-Based Access Control (RBAC) scopes checks on key permissions."""
    if "admin" in user_context.roles:
        return

    if not security_scopes.scopes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="verify_scopes used without scopes — use Security(verify_scopes, scopes=[...]) instead of Depends(verify_scopes).",
        )

    # Resolve request context parameters if request object is available
    collection_param = None
    doc_type_param = None
    if request:
        # Check query parameters
        collection_param = request.query_params.get("collection")
        # Check json body if possible
        try:
            body = await request.json()
            if isinstance(body, dict):
                collection_param = collection_param or body.get("collection") or body.get("filters", {}).get("collection")
                filename = body.get("filename")
                if filename and "." in filename:
                    doc_type_param = filename.split(".")[-1].lower()
        except Exception:
            pass

    for scope in security_scopes.scopes:
        if scope in user_context.scopes:
            continue
            
        allowed = False
        if scope == "document:read":
            if collection_param and f"collection:{collection_param}:read" in user_context.scopes:
                allowed = True
            if doc_type_param and f"document_type:{doc_type_param}:read" in user_context.scopes:
                allowed = True
        elif scope == "document:write":
            if collection_param and f"collection:{collection_param}:write" in user_context.scopes:
                allowed = True
            if doc_type_param and f"document_type:{doc_type_param}:write" in user_context.scopes:
                allowed = True
                
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Forbidden: Missing required scope '{scope}' or matching resource-level scope.",
            )


async def verify_admin_key(
    x_admin_master_key: str | None = Header(None, alias="X-Admin-Master-Key"),
) -> None:
    """Enforce administrative master key verification checks (System-wide Admin)."""
    if not x_admin_master_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing administrative master key credential.",
        )
    if not secrets.compare_digest(x_admin_master_key, settings.ADMIN_MASTER_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative master key credential.",
        )
