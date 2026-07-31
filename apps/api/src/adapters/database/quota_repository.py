"""SQLAlchemy-backed quota repository implementation."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentDb, InferenceLogDb
from src.domain.abstractions.quota import QuotaRepository


class SqlQuotaRepository(QuotaRepository):
    """SQLAlchemy implementation for tenant quota usage database queries."""

    async def get_storage_usage(self, tenant_id: str) -> tuple[int, int]:
        """Return (document_count, total_storage_bytes) for a tenant."""
        async with tenant_session(tenant_id=tenant_id, bypass_rls=True) as session:
            stmt = select(
                func.count(DocumentDb.document_id),
                func.coalesce(func.sum(DocumentDb.file_size), 0),
            ).where(
                DocumentDb.tenant_id == uuid.UUID(tenant_id),
                DocumentDb.is_deleted == False,
            )
            res = await session.execute(stmt)
            row = res.one()
            return int(row[0]), int(row[1])

    async def get_monthly_token_usage(self, tenant_id: str) -> int:
        """Return total tokens consumed by tenant in the current calendar month."""
        now = datetime.now(UTC)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)
        async with tenant_session(tenant_id=tenant_id, bypass_rls=True) as session:
            stmt = select(
                func.coalesce(func.sum(InferenceLogDb.prompt_tokens + InferenceLogDb.completion_tokens), 0)
            ).where(
                InferenceLogDb.tenant_id == uuid.UUID(tenant_id),
                InferenceLogDb.created_at >= start_of_month,
            )
            res = await session.execute(stmt)
            return int(res.scalar() or 0)

    async def get_daily_request_usage(self, tenant_id: str) -> int:
        """Return total requests logged for tenant today (UTC)."""
        now = datetime.now(UTC)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
        async with tenant_session(tenant_id=tenant_id, bypass_rls=True) as session:
            stmt = select(
                func.count(InferenceLogDb.log_id)
            ).where(
                InferenceLogDb.tenant_id == uuid.UUID(tenant_id),
                InferenceLogDb.created_at >= start_of_day,
            )
            res = await session.execute(stmt)
            return int(res.scalar() or 0)
