from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

# Create async engine supporting asyncpg
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
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
                # Set thread-local context variables for postgres row level security
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tenant_id"),
                    {"tenant_id": str(tenant_id)},
                )
            else:
                # Set empty setting to ensure RLS triggers restriction
                await session.execute(text("SET LOCAL app.current_tenant_id = ''"))
            yield session
