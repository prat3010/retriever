import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.domain.abstractions.exceptions import TenantIsolationViolationError

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def tenant_session(
    tenant_id: str | None = None, bypass_rls: bool = False
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session context enforcing RLS settings.

    Args:
        tenant_id: Active tenant ID context to set for RLS filters.
        bypass_rls: Set True during token lookup to bypass default RLS limits.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            if bypass_rls:
                await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            elif tenant_id:
                try:
                    # Validate that tenant_id is a valid UUID to prevent SQL injection
                    valid_uuid = uuid.UUID(str(tenant_id))
                except ValueError as e:
                    raise TenantIsolationViolationError(f"Invalid tenant ID format: {e}") from e
                
                # Set thread-local context variables for postgres row level security
                await session.execute(
                    text(f"SET LOCAL app.current_tenant_id = '{valid_uuid}'"),
                )
            else:
                # Set empty setting to ensure RLS triggers restriction
                await session.execute(text("SET LOCAL app.current_tenant_id = ''"))
            yield session
