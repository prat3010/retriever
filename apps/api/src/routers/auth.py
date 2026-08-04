import hashlib
import logging
import uuid

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import _fetch_jwks_key
from src.adapters.database.connection import tenant_session
from src.adapters.database.models import ApiKeyDb, TenantDb, UserDb
from src.config import settings
from src.container import audit_logger

logger = logging.getLogger("api")

router = APIRouter(prefix="/v1/auth", tags=["Auth"])

GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="Google OIDC ID Token or verified payload JWT")
    email: str | None = Field(None, description="Optional fallback email for dev/testing mode")
    name: str | None = Field(None, description="Optional fallback name for dev/testing mode")


class AuthSessionResponse(BaseModel):
    tenantId: str
    userId: str
    apiKey: str
    email: str
    name: str
    jwtToken: str
    isNewTenant: bool


@router.post(
    "/google",
    status_code=status.HTTP_200_OK,
    response_model=AuthSessionResponse,
)
async def google_auth(payload: GoogleAuthRequest) -> AuthSessionResponse:
    """Verify Google OIDC token, auto-provision tenant & user if new, and return session credentials."""
    email = payload.email
    name = payload.name
    google_sub = None

    # 1. Verify Google OIDC ID Token (signature, issuer, audience, email verification)
    token_verified = False
    try:
        unverified_header = jwt.get_unverified_header(payload.id_token)
        kid = unverified_header.get("kid")
        if kid:
            jwk = await _fetch_jwks_key(GOOGLE_JWKS_URI, kid)
            if jwk:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                claims = jwt.decode(
                    payload.id_token,
                    public_key,
                    algorithms=["RS256"],
                    options={"verify_aud": False},
                )
                if claims.get("iss") not in GOOGLE_ISSUERS:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Google ID Token issuer.",
                    )
                if settings.OIDC_AUDIENCE and claims.get("aud") != settings.OIDC_AUDIENCE:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Google ID Token audience.",
                    )
                if claims.get("email_verified") is not True:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Google account email is not verified.",
                    )
                email = claims.get("email") or email
                name = claims.get("name") or claims.get("given_name") or name
                google_sub = claims.get("sub")
                token_verified = True
    except HTTPException:
        raise
    except Exception as err:
        logger.warning("Google OIDC token verification failed: %s", err)

    if not token_verified:
        # Client-supplied credentials are only tolerated outside production for local testing.
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID Token or unverified token payload.",
            )
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID Token or unverified token payload.",
            )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Token missing email claim.",
        )

    display_name = name or email.split("@")[0].capitalize()
    external_id = google_sub or email.lower()

    async with tenant_session(bypass_rls=True) as session:
        # 2. Check if user already exists
        from sqlalchemy import select
        stmt = select(UserDb).where(UserDb.external_id == external_id)
        res = await session.execute(stmt)
        existing_user = res.scalar_one_or_none()

        is_new_tenant = False

        if existing_user:
            user_id = str(existing_user.user_id)
            tenant_id = str(existing_user.tenant_id)

            # Issue a fresh API key and persist its hash so the returned key actually works.
            # Raw keys are only ever stored hashed, so returning a key requires inserting it.
            api_key = f"ret_live_{uuid.uuid4().hex}"
            session.add(
                ApiKeyDb(
                    key_id=uuid.uuid4(),
                    tenant_id=existing_user.tenant_id,
                    name="Session Key",
                    prefix="ret_live_",
                    key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
                    role="client",
                    status="active",
                )
            )
            await session.commit()
            await audit_logger.write(tenant_id, "auth.google_login", f"User '{email}' logged in via Google")
        else:
            # 3. Auto-provision New Tenant & User
            is_new_tenant = True
            tenant_uuid = uuid.uuid4()
            user_uuid = uuid.uuid4()

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
            await audit_logger.write(tenant_id, "auth.google_signup", f"New user '{email}' auto-provisioned tenant")

    # 4. Generate Session Token
    if not settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is misconfigured: SECRET_KEY is not set.",
        )
    session_jwt = jwt.encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "roles": ["owner" if is_new_tenant else "member"],
            "scopes": ["document:read", "document:write", "chat:read", "chat:write"],
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )

    return AuthSessionResponse(
        tenantId=tenant_id,
        userId=user_id,
        apiKey=api_key,
        email=email,
        name=display_name,
        jwtToken=session_jwt,
        isNewTenant=is_new_tenant,
    )
