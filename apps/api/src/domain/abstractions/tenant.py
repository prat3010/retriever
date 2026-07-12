from abc import ABC, abstractmethod
from typing import Optional
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
    system_prompt_template: str = Field(default="You are a helpful grounding assistant.")


class TenantRegistry(ABC):
    @abstractmethod
    async def create_tenant(
        self, name: str, tier: str, isolation_level: str
    ) -> Tenant:
        """Create a new tenant workspace and return the Tenant entity."""
        pass

    @abstractmethod
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve tenant metadata by tenant ID."""
        pass

    @abstractmethod
    async def update_config(self, tenant_id: str, config: TenantConfig) -> None:
        """Update configuration settings for the tenant."""
        pass

    @abstractmethod
    async def get_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Retrieve dynamic configuration parameters for the tenant."""
        pass
