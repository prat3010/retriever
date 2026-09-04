"""SQLAlchemy implementation of the BudgetRepositoryProtocol (M93).

Aggregates historical and current-period tenant token spending, model cost
breakdowns, and checks virtual budget ceiling compliance.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import InferenceLogDb
from src.domain.abstractions.gateway import (
    BudgetRepositoryProtocol,
    VirtualTenantBudget,
)


class SqlBudgetRepository(BudgetRepositoryProtocol):
    """SQL-backed repository for tenant spend ledgers and virtual budgets."""

    async def get_tenant_spend(
        self, tenant_id: str
    ) -> tuple[float, float, dict[str, float]]:
        """Calculate (daily_spend, monthly_spend, cost_by_model) for a tenant."""
        tenant_uuid = uuid.UUID(tenant_id)
        now = datetime.now(UTC)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

        async with tenant_session(tenant_id=tenant_id, bypass_rls=True) as session:
            # 1. Daily spend
            daily_stmt = (
                select(func.coalesce(func.sum(InferenceLogDb.cost_usd), 0.0))
                .where(InferenceLogDb.tenant_id == tenant_uuid)
                .where(InferenceLogDb.created_at >= start_of_day)
            )
            daily_res = await session.execute(daily_stmt)
            daily_spend = float(daily_res.scalar() or 0.0)

            # 2. Monthly spend & cost by model
            monthly_stmt = (
                select(
                    InferenceLogDb.model_used,
                    func.coalesce(func.sum(InferenceLogDb.cost_usd), 0.0),
                )
                .where(InferenceLogDb.tenant_id == tenant_uuid)
                .where(InferenceLogDb.created_at >= start_of_month)
                .group_by(InferenceLogDb.model_used)
            )
            monthly_res = await session.execute(monthly_stmt)
            cost_by_model: dict[str, float] = defaultdict(float)
            monthly_spend = 0.0
            for model_used, cost in monthly_res.all():
                c = float(cost or 0.0)
                cost_by_model[model_used] = round(c, 4)
                monthly_spend += c

            return round(daily_spend, 4), round(monthly_spend, 4), dict(cost_by_model)

    async def get_tenant_budget(
        self, tenant_id: str, default_budget: VirtualTenantBudget | None = None
    ) -> VirtualTenantBudget:
        """Fetch compiled virtual budget details and current utilization for a tenant."""
        daily_spend, monthly_spend, cost_by_model = await self.get_tenant_spend(tenant_id)
        base = default_budget or VirtualTenantBudget()

        exceeded = False
        if base.daily_budget is not None and daily_spend >= base.daily_budget:
            exceeded = True
        if base.monthly_budget is not None and monthly_spend >= base.monthly_budget:
            exceeded = True

        return VirtualTenantBudget(
            daily_budget=base.daily_budget,
            monthly_budget=base.monthly_budget,
            hard_limit_action=base.hard_limit_action,
            free_fallback_model=base.free_fallback_model,
            currency=base.currency,
            current_daily_spend=daily_spend,
            current_monthly_spend=monthly_spend,
            is_budget_exceeded=exceeded,
            cost_by_model=cost_by_model,
        )
