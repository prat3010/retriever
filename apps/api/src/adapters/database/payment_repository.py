"""Database repository adapter for recording and querying payment transactions."""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import PaymentTransactionDb

logger = logging.getLogger(__name__)


class SqlPaymentRepository:
    """PostgreSQL implementation for payment transaction ledger persistence."""

    async def save_transaction(
        self,
        tenant_id: str,
        provider: str,
        event_type: str,
        amount: float,
        currency: str = "INR",
        status: str = "completed",
        external_reference: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Log an immutable payment transaction record."""
        tenant_uuid = UUID(tenant_id)
        tx = PaymentTransactionDb(
            tenant_id=tenant_uuid,
            provider=provider,
            event_type=event_type,
            amount=amount,
            currency=currency,
            status=status,
            external_reference=external_reference,
            meta_data=metadata or {},
        )

        async with tenant_session(tenant_id=tenant_id) as session:
            session.add(tx)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info(
                    "Ignoring duplicate payment event for provider '%s' and reference '%s'.",
                    provider,
                    external_reference,
                )
                return {
                    "duplicate": True,
                    "provider": provider,
                    "external_reference": external_reference,
                }
            await session.refresh(tx)

            return {
                "transaction_id": str(tx.transaction_id),
                "tenant_id": str(tx.tenant_id),
                "provider": tx.provider,
                "event_type": tx.event_type,
                "amount": tx.amount,
                "currency": tx.currency,
                "status": tx.status,
                "external_reference": tx.external_reference,
                "metadata": tx.meta_data,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }

    async def list_transactions(
        self, tenant_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict], int]:
        """Retrieve paginated payment transaction history for a tenant."""
        tenant_uuid = UUID(tenant_id)
        async with tenant_session(tenant_id=tenant_id) as session:
            count_stmt = select(func.count(PaymentTransactionDb.transaction_id)).where(
                PaymentTransactionDb.tenant_id == tenant_uuid
            )
            total_res = await session.execute(count_stmt)
            total = total_res.scalar() or 0

            stmt = (
                select(PaymentTransactionDb)
                .where(PaymentTransactionDb.tenant_id == tenant_uuid)
                .order_by(PaymentTransactionDb.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            res = await session.execute(stmt)
            rows = res.scalars().all()

            items = [
                {
                    "transaction_id": str(r.transaction_id),
                    "tenant_id": str(r.tenant_id),
                    "provider": r.provider,
                    "event_type": r.event_type,
                    "amount": r.amount,
                    "currency": r.currency,
                    "status": r.status,
                    "external_reference": r.external_reference,
                    "metadata": r.meta_data,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
            return items, total
