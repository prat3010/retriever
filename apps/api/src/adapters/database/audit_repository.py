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
            import hashlib
            created_at = datetime.now(UTC)
            tenant_uuid = uuid.UUID(tenant_id)
            
            async with tenant_session(bypass_rls=True) as session:
                # 1. Fetch latest record to get prior entry_hash
                stmt = select(AuditLogDb).where(AuditLogDb.tenant_id == tenant_uuid).order_by(AuditLogDb.created_at.desc()).limit(1)
                res = await session.execute(stmt)
                last_entry = res.scalars().first()
                
                if last_entry and last_entry.entry_hash:
                    previous_hash = last_entry.entry_hash
                else:
                    previous_hash = "0" * 64
                    
                # 2. Compute current SHA-256 hash
                payload_str = f"{tenant_id}:{action}:{details or ''}:{previous_hash}:{created_at.isoformat()}"
                entry_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
                
                session.add(
                    AuditLogDb(
                        log_id=uuid.uuid4(),
                        tenant_id=tenant_uuid,
                        action=action,
                        details=details,
                        created_at=created_at,
                        entry_hash=entry_hash,
                        previous_hash=previous_hash,
                    )
                )
                await session.flush()
        except Exception:
            logger.warning("audit_logger.write failed (non-blocking)", exc_info=True)

    async def verify_audit_chain(self, tenant_id: str) -> bool:
        """Traverse all audit log records for tenant in chronological order and verify hash chain integrity."""
        import hashlib
        tenant_uuid = uuid.UUID(tenant_id)
        async with tenant_session(bypass_rls=True) as session:
            stmt = select(AuditLogDb).where(AuditLogDb.tenant_id == tenant_uuid).order_by(AuditLogDb.created_at.asc())
            res = await session.execute(stmt)
            rows = res.scalars().all()
            
            expected_prev = "0" * 64
            for row in rows:
                if row.previous_hash != expected_prev:
                    logger.error(f"Audit chain verification failed at log_id={row.log_id}: previous_hash mismatch. Expected {expected_prev}, got {row.previous_hash}")
                    return False
                    
                payload_str = f"{tenant_id}:{row.action}:{row.details or ''}:{row.previous_hash}:{row.created_at.isoformat()}"
                calculated_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
                
                if row.entry_hash != calculated_hash:
                    logger.error(f"Audit chain verification failed at log_id={row.log_id}: entry_hash mismatch. Calculated {calculated_hash}, got {row.entry_hash}")
                    return False
                    
                expected_prev = row.entry_hash
                
            return True

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
                    "entryHash": r.entry_hash,
                    "previousHash": r.previous_hash,
                }
                for r in rows
            ], total
