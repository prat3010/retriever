import hashlib
import logging
import re
import secrets
import time

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, SecurityScopes
from jwt.exceptions import PyJWTError

from src.adapters.database.identity_repository import SqlIdentityProvider
from src.config import settings
from src.domain.abstractions.exceptions import (
    AuthenticationError,
    TenantIsolationViolationError,
)
from src.domain.abstractions.identity import UserContext

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# Header key selector
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
identity_provider = SqlIdentityProvider()

# In-memory JWKS cache with TTL
_jwks_cache: dict[str, tuple[float, dict]] = {}
_JWKS_CACHE_TTL_SECONDS = 3600.0


async def _fetch_jwks_key(jwks_uri: str, kid: str) -> dict | None:
    now = time.time()
    if jwks_uri in _jwks_cache:
        cached_time, key_map = _jwks_cache[jwks_uri]
        if now - cached_time < _JWKS_CACHE_TTL_SECONDS and kid in key_map:
            return key_map[kid]

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(jwks_uri, timeout=5.0)
            if res.status_code == 200:
                jwks = res.json()
                keys = jwks.get("keys", [])
                key_map = {}
                for key in keys:
                    if "kid" in key:
                        key_map[key["kid"]] = key
                _jwks_cache[jwks_uri] = (now, key_map)
                return key_map.get(kid)
    except Exception as exc:
        logger.warning(f"Failed to fetch JWKS key from {jwks_uri}: {exc}")
    return None


async def get_current_user(
    request: Request,
    token: str | None = Security(api_key_header),
) -> UserContext:
    """Validate incoming Bearer API key token or OIDC JWT token and return active UserContext."""
    if hasattr(request.state, "user_context") and request.state.user_context:
        return request.state.user_context

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
        user_ctx = await identity_provider.validate_token(clean_token)
        request.state.user_context = user_ctx
        return user_ctx
    except AuthenticationError as e:
        # 2. Try validating as OIDC / Supabase JWT token if OIDC or SUPABASE_URL is configured
        jwks_uri = settings.OIDC_JWKS_URI or (
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json" if settings.SUPABASE_URL else ""
        )
        issuer_url = settings.OIDC_ISSUER_URL or (
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1" if settings.SUPABASE_URL else ""
        )

        if jwks_uri or issuer_url or settings.SUPABASE_URL:
            try:
                payload: dict | None = None
                unverified_header = jwt.get_unverified_header(clean_token)
                alg = unverified_header.get("alg", "RS256")
                kid = unverified_header.get("kid")

                # Strategy A: If HS256 or SUPABASE_JWT_SECRET / SERVICE_ROLE_KEY is provided
                jwt_secret = settings.SUPABASE_JWT_SECRET or settings.SUPABASE_SERVICE_ROLE_KEY
                if (alg == "HS256" or jwt_secret) and jwt_secret:
                    try:
                        payload = jwt.decode(
                            clean_token,
                            jwt_secret,
                            algorithms=["HS256"],
                            options={"verify_aud": False, "verify_iss": False},
                        )
                    except PyJWTError:
                        payload = None

                # Strategy B: If RS256 algorithm & JWKS key is available
                if payload is None and kid and jwks_uri:
                    jwk = await _fetch_jwks_key(jwks_uri, kid)
                    if jwk and jwk.get("kty") == "RSA":
                        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                        decode_kwargs: dict = {
                            "algorithms": ["RS256"],
                            "options": {},
                        }
                        if settings.OIDC_AUDIENCE:
                            decode_kwargs["audience"] = settings.OIDC_AUDIENCE
                        else:
                            decode_kwargs["options"]["verify_aud"] = False

                        if issuer_url:
                            decode_kwargs["issuer"] = issuer_url
                        else:
                            decode_kwargs["options"]["verify_iss"] = False

                        payload = jwt.decode(clean_token, public_key, **decode_kwargs)

                # Strategy C: Fallback to Supabase Auth API GET /auth/v1/user
                if payload is None and settings.SUPABASE_URL:
                    try:
                        async with httpx.AsyncClient() as http_client:
                            user_res = await http_client.get(
                                f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                                headers={
                                    "Authorization": f"Bearer {clean_token}",
                                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY or "",
                                },
                                timeout=5.0,
                            )
                            if user_res.status_code == 200:
                                user_data = user_res.json()
                                payload = {
                                    "sub": user_data.get("id"),
                                    "email": user_data.get("email"),
                                    "app_metadata": user_data.get("app_metadata", {}),
                                    "user_metadata": user_data.get("user_metadata", {}),
                                }
                    except Exception:
                        pass

                if payload:
                    tenant_id = (
                        payload.get("tenant_id")
                        or payload.get("custom:tenant_id")
                        or payload.get("app_metadata", {}).get("tenant_id")
                    )
                    user_id = payload.get("sub")
                    email = payload.get("email")
                    roles = payload.get("roles") or payload.get("app_metadata", {}).get("roles", ["client"])
                    scopes = payload.get("scopes", ["document:read", "document:write", "chat:read", "chat:write"])

                    if not tenant_id and (user_id or email):
                        import uuid

                        from sqlalchemy import select

                        from src.adapters.database.connection import tenant_session
                        from src.adapters.database.models import (
                            ApiKeyDb,
                            TenantDb,
                            UserDb,
                        )

                        async with tenant_session(bypass_rls=True) as session:
                            stmt = select(UserDb).where(
                                (UserDb.external_id == user_id) | (UserDb.external_id == email)
                            )
                            res = await session.execute(stmt)
                            user_db = res.scalar_one_or_none()
                            if user_db:
                                tenant_id = str(user_db.tenant_id)
                                user_id = str(user_db.user_id)
                            else:
                                tenant_uuid = uuid.uuid4()
                                user_uuid = uuid.uuid4()
                                display_name = (email or "User").split("@")[0].capitalize()
                                external_id = user_id or email

                                new_tenant = TenantDb(
                                    tenant_id=tenant_uuid,
                                    name=f"{display_name}'s Workspace",
                                    tier="starter",
                                    status="active",
                                )
                                session.add(new_tenant)

                                new_user = UserDb(
                                    user_id=user_uuid,
                                    tenant_id=tenant_uuid,
                                    external_id=external_id,
                                    display_name=display_name,
                                    is_active=True,
                                )
                                session.add(new_user)

                                api_key = f"ret_live_{uuid.uuid4().hex}"
                                key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                                new_key_db = ApiKeyDb(
                                    key_id=uuid.uuid4(),
                                    tenant_id=tenant_uuid,
                                    name="Default Workspace Key",
                                    prefix="ret_live_",
                                    key_hash=key_hash,
                                    role="client",
                                    status="active",
                                )
                                session.add(new_key_db)
                                await session.commit()

                                tenant_id = str(tenant_uuid)
                                user_id = str(user_uuid)

                    if not tenant_id:
                        raise AuthenticationError("SSO / Supabase token missing required tenant context claim.")

                    user_ctx = UserContext(
                        user_id=user_id or "unknown",
                        tenant_id=tenant_id,
                        roles=roles if isinstance(roles, list) else [str(roles)],
                        scopes=scopes if isinstance(scopes, list) else [str(scopes)],
                    )
                    request.state.user_context = user_ctx
                    return user_ctx
            except PyJWTError as je:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"SSO Token validation failed: {je!s}",
                ) from je
            except AuthenticationError as ae:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(ae),
                ) from ae

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
        log_payload = {
            "level": "FATAL",
            "incident": "CRITICAL_SECURITY_BREACH",
            "authenticated_tenant": user_context.tenant_id,
            "target_tenant": tenantId,
            "message": "Tenant mismatch detected! Initiating Key Revocation Kill-Switch.",
        }
        logger.critical("Critical security breach detected: tenant mismatch", extra={"security_incident": log_payload})

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
        elif scope == "chat:write":
            if "document:write" in user_context.scopes:
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


async def verify_tenant_or_admin(
    tenantId: str,
    request: Request,
    token: str | None = Security(api_key_header),
    x_admin_master_key: str | None = Header(None, alias="X-Admin-Master-Key"),
) -> None:
    """Allow either valid admin master key OR verified tenant bearer token with tenant isolation."""
    if x_admin_master_key and secrets.compare_digest(x_admin_master_key, settings.ADMIN_MASTER_KEY):
        return

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials (bearer token or admin key).",
        )

    user_ctx = await get_current_user(request, token)
    await verify_tenant_isolation(tenantId, user_ctx, token)

