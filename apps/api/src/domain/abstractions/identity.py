from abc import ABC, abstractmethod
from typing import Optional
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
    status: str
    created_at: str
    expires_at: Optional[str] = None


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
        self, tenant_id: str, name: str, expires_in_days: Optional[int] = None
    ) -> tuple[str, ApiKeyMetadata]:
        """Generate a new API key, hash it, save to DB, and return (raw_key, metadata)."""
        pass

    @abstractmethod
    async def revoke_api_key(self, tenant_id: str, key_id: str) -> None:
        """Revoke API key metadata, rendering it inactive."""
        pass
