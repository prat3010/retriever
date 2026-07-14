from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    tenant_id: str
    name: str
    status: str
    tier: str
    created_at: str


class TenantConfig(BaseModel):
    tenant_id: str
    active_model: str = Field(default="claude-3-5-sonnet")
    temperature: float = Field(default=0.2)
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=100)
    system_prompt_template: str = Field(default="")


class TenantRegistry(ABC):
    @abstractmethod
    async def create_tenant(
        self, name: str, tier: str, isolation_level: str
    ) -> Tenant:
        """Create a new tenant workspace and return the Tenant entity."""
        pass

    @abstractmethod
    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Retrieve tenant metadata by tenant ID."""
        pass

    @abstractmethod
    async def list_tenants(self, search: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[Tenant], int]:
        """List tenants with optional search, pagination. Returns (items, total)."""
        pass

    @abstractmethod
    async def list_tenants_cursor(
        self, search: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[Tenant], str | None, bool]:
        """List tenants using cursor-based pagination. Returns (items, next_cursor, has_more)."""
        pass

    @abstractmethod
    async def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate (suspend) a tenant. Returns True if found and deactivated."""
        pass

    @abstractmethod
    async def update_config(self, tenant_id: str, config: TenantConfig) -> None:
        """Update configuration settings for the tenant."""
        pass

    @abstractmethod
    async def get_config(self, tenant_id: str) -> TenantConfig | None:
        """Retrieve dynamic configuration parameters for the tenant."""
        pass
