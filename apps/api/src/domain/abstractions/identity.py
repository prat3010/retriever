from abc import ABC, abstractmethod

from pydantic import BaseModel


class UserContext(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str]
    scopes: list[str]


class ApiKeyMetadata(BaseModel):
    key_id: str
    tenant_id: str
    name: str
    prefix: str
    role: str = "client"
    status: str
    created_at: str
    expires_at: str | None = None


class IdentityProvider(ABC):
    @abstractmethod
    async def validate_token(self, token: str) -> UserContext:
        """Validate API key token, returning UserContext payload.

        Raises:
            AuthenticationError: If the token is invalid or expired.
        """
        pass

    @abstractmethod
    async def create_api_key(
        self, tenant_id: str, name: str, expires_in_days: int | None = None, role: str = "client"
    ) -> tuple[str, ApiKeyMetadata]:
        """Generate a new API key, hash it, save to DB, and return (raw_key, metadata)."""
        pass

    @abstractmethod
    async def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Revoke API key metadata, rendering it inactive. Returns True if found and revoked."""
        pass

    @abstractmethod
    async def revoke_api_key_by_hash(self, key_hash: str) -> bool:
        """Revoke an API key by its SHA-256 hash. Bypasses RLS. Returns True if found and revoked."""
        pass

    @abstractmethod
    async def list_api_keys(self, tenant_id: str) -> list[ApiKeyMetadata]:
        """List all API keys for a tenant."""
        pass


class UserInfo(BaseModel):
    user_id: str
    tenant_id: str
    external_id: str
    display_name: str | None = None
    is_active: bool = True
    created_at: str = ""


class UserRepository(ABC):
    @abstractmethod
    async def create_user(
        self, tenant_id: str, external_id: str, display_name: str | None = None
    ) -> UserInfo:
        """Create a new user within a tenant."""
        pass

    @abstractmethod
    async def get_user(self, tenant_id: str, user_id: str) -> UserInfo | None:
        """Get a user by ID, scoped to tenant."""
        pass

    @abstractmethod
    async def list_users(self, tenant_id: str) -> list[UserInfo]:
        """List all active users in a tenant."""
        pass

    @abstractmethod
    async def deactivate_user(self, tenant_id: str, user_id: str) -> None:
        """Deactivate a user."""
        pass
