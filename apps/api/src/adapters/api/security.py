import hashlib
import json
import sys

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, SecurityScopes
from sqlalchemy import update

from src.adapters.database.connection import tenant_session
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.database.models import ApiKeyDb
from src.config import settings
from src.domain.abstractions.exceptions import (
    AuthenticationError,
    TenantIsolationViolationError,
)
from src.domain.abstractions.identity import UserContext

# Header key selector
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
identity_provider = SqlIdentityProvider()


async def get_current_user(token: str | None = Security(api_key_header)) -> UserContext:
    """Validate incoming Bearer API key token and return active UserContext."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization API key is missing.",
        )

    clean_token = token
    if token.lower().startswith("bearer "):
        clean_token = token[7:]

    try:
        return await identity_provider.validate_token(clean_token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


async def verify_tenant_isolation(
    tenantId: str,
    user_context: UserContext = Depends(get_current_user),
    token: str | None = Security(api_key_header),
) -> None:
    """Compare authenticated context tenant_id against path parameters.

    Triggers the Tenancy Breach Kill-Switch on mismatches.
    """
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

            # Execute immediate update bypassing RLS context to deactivate key
            async with tenant_session(bypass_rls=True) as session:
                await session.execute(
                    update(ApiKeyDb)
                    .where(ApiKeyDb.key_hash == key_hash)
                    .values(status="inactive")
                )

        raise TenantIsolationViolationError(
            "Access Denied: Tenancy boundary violation detected."
        )


async def verify_scopes(
    security_scopes: SecurityScopes,
    user_context: UserContext = Depends(get_current_user),
) -> None:
    """Enforce Role-Based Access Control (RBAC) scopes checks on key permissions."""
    if security_scopes.scopes:
        for scope in security_scopes.scopes:
            if scope not in user_context.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Forbidden: Missing required scope '{scope}'.",
                )


async def verify_admin_key(
    x_admin_master_key: str = Header(..., alias="X-Admin-Master-Key"),
) -> None:
    """Enforce administrative master key verification checks (System-wide Admin)."""
    if x_admin_master_key != settings.ADMIN_MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative master key credential.",
        )
