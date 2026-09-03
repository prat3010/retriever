"""SQLAlchemy implementation of BaseAnomalyRepository."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select, update

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import ApiKeyDb, TelemetryAnomalyDb
from src.domain.abstractions.anomaly import (
    AnomalyFilterParams,
    AnomalyScore,
    BaseAnomalyRepository,
)


class SqlAnomalyRepository(BaseAnomalyRepository):
    """PostgreSQL-backed repository for telemetry anomaly events and credential quarantine."""

    async def record_anomaly(
        self, score: AnomalyScore, raw_features: dict[str, Any] | None = None
    ) -> str:
        """Persist detected anomaly event into telemetry_anomalies table."""
        anomaly_uuid = uuid.uuid4()
        tenant_uuid = uuid.UUID(score.tenant_id)
        key_uuid = None
        if score.entity_type == "api_key":
            try:
                key_uuid = uuid.UUID(score.entity_id)
            except ValueError:
                key_uuid = None

        features_data = raw_features or score.features

        async with tenant_session(tenant_id=score.tenant_id, bypass_rls=True) as session:
            anomaly_db = TelemetryAnomalyDb(
                anomaly_id=anomaly_uuid,
                tenant_id=tenant_uuid,
                entity_id=score.entity_id,
                entity_type=score.entity_type,
                key_id=key_uuid,
                risk_level=score.risk_level,
                anomaly_score=float(score.anomaly_score),
                algorithm_used=score.algorithm_used,
                features=features_data,
                contributing_factors=score.contributing_factors,
                is_quarantined=score.risk_level == "CRITICAL",
                status="active",
                created_at=datetime.now(UTC),
            )
            session.add(anomaly_db)
            await session.flush()

        return str(anomaly_uuid)

    async def list_anomalies(
        self, filters: AnomalyFilterParams
    ) -> tuple[list[dict[str, Any]], int]:
        """Retrieve paginated anomaly events matching filter criteria."""
        async with tenant_session(tenant_id=filters.tenant_id, bypass_rls=True) as session:
            query = select(TelemetryAnomalyDb)

            if filters.tenant_id:
                query = query.where(TelemetryAnomalyDb.tenant_id == uuid.UUID(filters.tenant_id))
            if filters.risk_level:
                query = query.where(TelemetryAnomalyDb.risk_level == filters.risk_level.upper())
            if filters.status:
                query = query.where(TelemetryAnomalyDb.status == filters.status.lower())

            # Count total matching records
            count_stmt = select(func.count()).select_from(query.subquery())
            total = (await session.execute(count_stmt)).scalar() or 0

            # Execute paginated fetch
            query = query.order_by(desc(TelemetryAnomalyDb.created_at)).offset(filters.offset).limit(filters.limit)
            result = await session.execute(query)
            rows = result.scalars().all()

            items = [
                {
                    "anomaly_id": str(r.anomaly_id),
                    "tenant_id": str(r.tenant_id),
                    "entity_id": str(r.entity_id),
                    "entity_type": str(r.entity_type),
                    "key_id": str(r.key_id) if r.key_id else None,
                    "risk_level": str(r.risk_level),
                    "anomaly_score": float(r.anomaly_score),
                    "algorithm_used": str(r.algorithm_used),
                    "features": dict(r.features or {}),
                    "contributing_factors": list(r.contributing_factors or []),
                    "is_quarantined": bool(r.is_quarantined),
                    "status": str(r.status),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                    "resolved_by": r.resolved_by,
                    "notes": r.notes,
                }
                for r in rows
            ]

            return items, total

    async def resolve_anomaly(
        self, anomaly_id: str, resolved_by: str, notes: str | None = None
    ) -> bool:
        """Mark an anomaly as resolved or dismissed."""
        anomaly_uuid = uuid.UUID(anomaly_id)
        async with tenant_session(bypass_rls=True) as session:
            stmt = (
                update(TelemetryAnomalyDb)
                .where(TelemetryAnomalyDb.anomaly_id == anomaly_uuid)
                .values(
                    status="resolved",
                    resolved_at=datetime.now(UTC),
                    resolved_by=resolved_by,
                    notes=notes,
                )
            )
            result = await session.execute(stmt)
            return bool(result.rowcount and result.rowcount > 0)

    async def quarantine_key(
        self, key_id: str, tenant_id: str, reason: str, level: str = "CRITICAL"
    ) -> bool:
        """Toggle API key status to quarantined and update audit records."""
        key_uuid = uuid.UUID(key_id)
        async with tenant_session(bypass_rls=True) as session:
            # 1. Update ApiKeyDb status
            key_stmt = (
                update(ApiKeyDb)
                .where(ApiKeyDb.key_id == key_uuid)
                .values(status="quarantined")
            )
            await session.execute(key_stmt)

            # 2. Update active anomalies for this key to is_quarantined = True
            anomaly_stmt = (
                update(TelemetryAnomalyDb)
                .where(
                    TelemetryAnomalyDb.key_id == key_uuid,
                    TelemetryAnomalyDb.status == "active",
                )
                .values(is_quarantined=True, notes=reason)
            )
            await session.execute(anomaly_stmt)

            return True

    async def unquarantine_key(self, key_id: str, resolved_by: str) -> bool:
        """Restore quarantined API key to active status."""
        key_uuid = uuid.UUID(key_id)
        async with tenant_session(bypass_rls=True) as session:
            # 1. Update ApiKeyDb status to active
            key_stmt = (
                update(ApiKeyDb)
                .where(ApiKeyDb.key_id == key_uuid)
                .values(status="active")
            )
            await session.execute(key_stmt)

            # 2. Update active anomalies for this key
            anomaly_stmt = (
                update(TelemetryAnomalyDb)
                .where(
                    TelemetryAnomalyDb.key_id == key_uuid,
                    TelemetryAnomalyDb.status == "active",
                )
                .values(
                    is_quarantined=False,
                    status="resolved",
                    resolved_at=datetime.now(UTC),
                    resolved_by=resolved_by,
                    notes="Restored to active by administrator",
                )
            )
            await session.execute(anomaly_stmt)

            return True
