import uuid

from sqlalchemy import func, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import TenantConfigDb, TenantDb
from src.adapters.database.pagination import encode_cursor, decode_cursor
from src.domain.abstractions.tenant import Tenant, TenantConfig, TenantRegistry


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
                system_prompt_template="",
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

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
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

    async def list_tenants(self, search: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[Tenant], int]:
        """List tenants with optional search and pagination. Returns (items, total)."""
        async with tenant_session(bypass_rls=True) as session:
            base = select(TenantDb)
            count_base = select(func.count(TenantDb.tenant_id))
            if search:
                pattern = f"%{search}%"
                base = base.where(TenantDb.name.ilike(pattern))
                count_base = count_base.where(TenantDb.name.ilike(pattern))
            total_result = await session.execute(count_base)
            total = total_result.scalar() or 0
            stmt = base.order_by(TenantDb.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                Tenant(
                    tenant_id=str(r.tenant_id),
                    name=r.name,
                    status=r.status,
                    tier=r.tier,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                )
                for r in rows
            ], total

    async def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate (suspend) a tenant. Returns True if found and deactivated."""
        async with tenant_session(bypass_rls=True) as session:
            stmt = select(TenantDb).where(TenantDb.tenant_id == uuid.UUID(tenant_id))
            result = await session.execute(stmt)
            db_tenant = result.scalar_one_or_none()
            if not db_tenant:
                return False
            db_tenant.status = "suspended"
            await session.flush()
            return True

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

    async def get_config(self, tenant_id: str) -> TenantConfig | None:
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

    async def list_tenants_cursor(
        self, search: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[Tenant], str | None, bool]:
        """List tenants using cursor-based pagination. Returns (items, next_cursor, has_more)."""
        async with tenant_session(bypass_rls=True) as session:
            stmt = select(TenantDb)
            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(TenantDb.name.ilike(pattern))

            if cursor:
                try:
                    cursor_time, cursor_id = decode_cursor(cursor)
                    stmt = stmt.where(
                        (TenantDb.created_at < cursor_time) |
                        ((TenantDb.created_at == cursor_time) & (TenantDb.tenant_id < cursor_id))
                    )
                except ValueError:
                    pass

            stmt = stmt.order_by(TenantDb.created_at.desc(), TenantDb.tenant_id.desc()).limit(limit + 1)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            items = [
                Tenant(
                    tenant_id=str(r.tenant_id),
                    name=r.name,
                    status=r.status,
                    tier=r.tier,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                )
                for r in rows
            ]

            next_cursor = None
            if has_more and rows:
                last_item = rows[-1]
                next_cursor = encode_cursor(last_item.created_at, last_item.tenant_id)

            return items, next_cursor, has_more
