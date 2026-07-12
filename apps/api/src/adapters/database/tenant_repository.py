from typing import Optional
import uuid
from sqlalchemy import select
from src.domain.abstractions.tenant import TenantRegistry, Tenant, TenantConfig
from src.adapters.database.models import TenantDb, TenantConfigDb
from src.adapters.database.connection import tenant_session


class SqlTenantRegistry(TenantRegistry):
    async def create_tenant(
        self, name: str, tier: str, isolation_level: str
    ) -> Tenant:
        """Create a new tenant workspace and return the Tenant entity."""
        # Provision the tenant and default configuration settings atomically
        async with tenant_session(bypass_rls=True) as session:
            tenant_id = uuid.uuid4()
            db_tenant = TenantDb(
                tenant_id=tenant_id,
                name=name,
                status="active",
                tier=tier,
            )
            session.add(db_tenant)

            # Auto-generate baseline configuration values
            db_config = TenantConfigDb(
                tenant_id=tenant_id,
                active_model="claude-3-5-sonnet",
                temperature=0.2,
                chunk_size=500,
                chunk_overlap=100,
                system_prompt_template="You are a helpful grounding assistant.",
            )
            session.add(db_config)
            await session.flush()

            return Tenant(
                tenant_id=str(db_tenant.tenant_id),
                name=db_tenant.name,
                status=db_tenant.status,
                tier=db_tenant.tier,
                created_at=db_tenant.created_at.isoformat(),
            )

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve tenant metadata by tenant ID."""
        async with tenant_session(bypass_rls=True) as session:
            stmt = select(TenantDb).where(TenantDb.tenant_id == uuid.UUID(tenant_id))
            result = await session.execute(stmt)
            db_tenant = result.scalar_one_or_none()
            if not db_tenant:
                return None
            return Tenant(
                tenant_id=str(db_tenant.tenant_id),
                name=db_tenant.name,
                status=db_tenant.status,
                tier=db_tenant.tier,
                created_at=db_tenant.created_at.isoformat(),
            )

    async def update_config(self, tenant_id: str, config: TenantConfig) -> None:
        """Update configuration settings for the tenant."""
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(TenantConfigDb).where(TenantConfigDb.tenant_id == uuid.UUID(tenant_id))
            result = await session.execute(stmt)
            db_config = result.scalar_one_or_none()
            if not db_config:
                db_config = TenantConfigDb(tenant_id=uuid.UUID(tenant_id))
                session.add(db_config)

            db_config.active_model = config.active_model
            db_config.temperature = config.temperature
            db_config.chunk_size = config.chunk_size
            db_config.chunk_overlap = config.chunk_overlap
            db_config.system_prompt_template = config.system_prompt_template
            await session.flush()

    async def get_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Retrieve dynamic configuration parameters for the tenant."""
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(TenantConfigDb).where(TenantConfigDb.tenant_id == uuid.UUID(tenant_id))
            result = await session.execute(stmt)
            db_config = result.scalar_one_or_none()
            if not db_config:
                return None
            return TenantConfig(
                tenant_id=str(db_config.tenant_id),
                active_model=db_config.active_model,
                temperature=db_config.temperature,
                chunk_size=db_config.chunk_size,
                chunk_overlap=db_config.chunk_overlap,
                system_prompt_template=db_config.system_prompt_template,
            )
