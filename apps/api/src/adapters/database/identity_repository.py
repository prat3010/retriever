import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import ApiKeyDb, TenantDb
from src.domain.abstractions.exceptions import AuthenticationError
from src.domain.abstractions.identity import (
    ApiKeyMetadata,
    IdentityProvider,
    UserContext,
)


class SqlIdentityProvider(IdentityProvider):
    async def validate_token(self, token: str) -> UserContext:
        """Validate API key token, returning UserContext payload.

        Args:
            token: Raw Bearer API key token.

        Raises:
            AuthenticationError: If the token is invalid, expired, or inactive.
        """
        # Hashing raw key matching SHA-256 standard (ADR-001)
        key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        # Query requires bypassing RLS since tenant is not yet resolved
        async with tenant_session(bypass_rls=True) as session:
            stmt = (
                select(ApiKeyDb)
                .join(TenantDb, ApiKeyDb.tenant_id == TenantDb.tenant_id)
                .where(
                    ApiKeyDb.key_hash == key_hash,
                    ApiKeyDb.status == "active",
                    TenantDb.status == "active",
                )
            )
            result = await session.execute(stmt)
            db_key = result.scalar_one_or_none()

            if not db_key:
                raise AuthenticationError("Invalid, inactive, or suspended API key token.")

            # Validate expiration timestamp
            if db_key.expires_at:
                now = datetime.now(UTC)
                # Convert db_key.expires_at to timezone-aware UTC if it is naive
                expires_at = db_key.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if now > expires_at:
                    raise AuthenticationError("API key token has expired.")

            roles = ["admin"] if db_key.role == "admin" else ["client"]
            scopes = (
                ["admin:*"]
                if db_key.role == "admin"
                else ["document:write", "document:read"]
            )

            return UserContext(
                user_id="",
                tenant_id=str(db_key.tenant_id),
                roles=roles,
                scopes=scopes,
            )

    async def create_api_key(
        self, tenant_id: str, name: str, expires_in_days: int | None = None, role: str = "client"
    ) -> tuple[str, ApiKeyMetadata]:
        """Generate a new API key, hash it, save to DB, and return (raw_key, metadata)."""
        # Prefix format: ret_live_<random>
        random_prefix = secrets.token_urlsafe(8)
        prefix = f"ret_live_{random_prefix}"
        secret_part = secrets.token_urlsafe(24)
        raw_key = f"{prefix}.{secret_part}"

        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        key_id = uuid.uuid4()

        expires_at: datetime | None = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        async with tenant_session(tenant_id=tenant_id) as session:
            db_key = ApiKeyDb(
                key_id=key_id,
                tenant_id=uuid.UUID(tenant_id),
                name=name,
                prefix=prefix,
                key_hash=key_hash,
                role=role,
                status="active",
                expires_at=expires_at,
            )
            session.add(db_key)
            await session.flush()

            metadata = ApiKeyMetadata(
                key_id=str(db_key.key_id),
                tenant_id=str(db_key.tenant_id),
                name=db_key.name,
                prefix=db_key.prefix,
                role=db_key.role,
                status=db_key.status,
                created_at=db_key.created_at.isoformat(),
                expires_at=db_key.expires_at.isoformat() if db_key.expires_at else None,
            )
            return raw_key, metadata

    async def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Revoke API key metadata, rendering it inactive. Returns True if found and revoked."""
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(ApiKeyDb).where(
                ApiKeyDb.key_id == uuid.UUID(key_id),
                ApiKeyDb.tenant_id == uuid.UUID(tenant_id),
            )
            result = await session.execute(stmt)
            db_key = result.scalar_one_or_none()

            if not db_key:
                return False

            db_key.status = "inactive"
            await session.flush()
            return True

    async def revoke_api_key_by_hash(self, key_hash: str) -> bool:
        """Revoke an API key by its SHA-256 hash. Bypasses RLS."""
        async with tenant_session(bypass_rls=True) as session:
            stmt = select(ApiKeyDb).where(ApiKeyDb.key_hash == key_hash)
            result = await session.execute(stmt)
            db_key = result.scalar_one_or_none()
            if not db_key:
                return False
            db_key.status = "inactive"
            await session.flush()
            return True

    async def list_api_keys(self, tenant_id: str) -> list[ApiKeyMetadata]:
        """List all API keys for a tenant."""
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(ApiKeyDb).where(ApiKeyDb.tenant_id == uuid.UUID(tenant_id))
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                ApiKeyMetadata(
                    key_id=str(r.key_id),
                    tenant_id=str(r.tenant_id),
                    name=r.name,
                    prefix=r.prefix,
                    role=r.role,
                    status=r.status,
                    created_at=r.created_at.isoformat(),
                    expires_at=r.expires_at.isoformat() if r.expires_at else None,
                )
                for r in rows
            ]
