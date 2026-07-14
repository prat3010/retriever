"""Audit Log Database Repository.

Implements audit log persistence and querying using SQLAlchemy.
Logging is best-effort — write failures never block the calling operation.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import AuditLogDb

logger = logging.getLogger(__name__)


class SqlAuditLogRepository:
    """SQLAlchemy-backed audit log repository."""

    async def write(self, tenant_id: str, action: str, details: str | None = None) -> None:
        try:
            async with tenant_session(bypass_rls=True) as session:
                session.add(
                    AuditLogDb(
                        log_id=uuid.uuid4(),
                        tenant_id=uuid.UUID(tenant_id),
                        action=action,
                        details=details,
                        created_at=datetime.now(UTC),
                    )
                )
                await session.flush()
        except Exception:
            logger.warning("audit_logger.write failed (non-blocking)", exc_info=True)

    async def list(
        self,
        tenant_id: str | None = None,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        async with tenant_session(bypass_rls=True) as session:
            base = select(AuditLogDb)
            count_base = select(func.count(AuditLogDb.log_id))
            if tenant_id:
                base = base.where(AuditLogDb.tenant_id == uuid.UUID(tenant_id))
                count_base = count_base.where(AuditLogDb.tenant_id == uuid.UUID(tenant_id))
            if action:
                base = base.where(AuditLogDb.action == action)
                count_base = count_base.where(AuditLogDb.action == action)
            total_result = await session.execute(count_base)
            total = total_result.scalar() or 0
            stmt = base.order_by(AuditLogDb.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "logId": str(r.log_id),
                    "tenantId": str(r.tenant_id),
                    "action": r.action,
                    "details": r.details,
                    "createdAt": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ], total
