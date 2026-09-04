"""Gateway Domain Abstractions (Ports).

Defines pure domain entities, models, and abstract interfaces for the
multi-model LLM gateway, dynamic fallback cascades, and virtual tenant budgets.
Contains zero infrastructure or framework imports.
"""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field


class GatewayModelInfo(BaseModel):
    """Metadata describing a model accessible through the LLM gateway."""

    model_id: str
    provider: str  # e.g., "openai", "anthropic", "gemini", "groq", "mistral", "ollama"
    name: str
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    capabilities: list[str] = Field(default_factory=lambda: ["chat"])
    is_local: bool = False
    health_status: str = "healthy"  # "healthy", "degraded", "unavailable"
    latency_ms: int | None = None
    description: str = ""


class ModelRoutingConfig(BaseModel):
    """Configuration for dynamic fallback cascades and model routing."""

    primary_model: str = "gemini-2.5-flash"
    fallback_models: list[str] = Field(
        default_factory=lambda: ["openai/gpt-4o-mini", "ollama/qwen2.5:14b"]
    )
    latency_sla_ms: int = 4000
    cooldown_seconds: int = 60
    retry_attempts: int = 2


BudgetActionType = Literal["warn_only", "block", "downgrade_free_model"]


class VirtualTenantBudget(BaseModel):
    """Virtual spending budget and quota constraints for a tenant."""

    daily_budget: float | None = None
    monthly_budget: float | None = None
    hard_limit_action: BudgetActionType = "warn_only"
    free_fallback_model: str = "ollama/qwen2.5:14b"
    currency: str = "USD"
    current_daily_spend: float = 0.0
    current_monthly_spend: float = 0.0
    is_budget_exceeded: bool = False
    cost_by_model: dict[str, float] = Field(default_factory=dict)


class GatewayProbeResult(BaseModel):
    """Result of latency and connectivity ping across upstream providers."""

    provider: str
    target_model: str
    reachable: bool
    latency_ms: int
    error_message: str | None = None


class BudgetExceededError(Exception):
    """Raised when tenant exceeds assigned hard budget limit and action is 'block'."""

    def __init__(self, tenant_id: str, current_spend: float, budget: float, period: str = "monthly") -> None:
        self.tenant_id = tenant_id
        self.current_spend = current_spend
        self.budget = budget
        self.period = period
        super().__init__(
            f"Tenant {tenant_id} has exceeded {period} budget ceiling: "
            f"${current_spend:.4f} / ${budget:.4f} (action=block)"
        )


class BudgetRepositoryProtocol(ABC):
    """Port for persisting and calculating virtual tenant budgets and spending ledgers."""

    @abstractmethod
    async def get_tenant_spend(
        self, tenant_id: str
    ) -> tuple[float, float, dict[str, float]]:
        """Calculate (daily_spend, monthly_spend, cost_by_model) for a tenant."""
        pass

    @abstractmethod
    async def get_tenant_budget(
        self, tenant_id: str, default_budget: VirtualTenantBudget | None = None
    ) -> VirtualTenantBudget:
        """Fetch compiled virtual budget details and current utilization for a tenant."""
        pass


class GatewayRouterProtocol(ABC):
    """Port for querying gateway models, routing topologies, and provider health."""

    @abstractmethod
    def list_available_models(self) -> list[GatewayModelInfo]:
        """List all cataloged models across cloud and local providers."""
        pass

    @abstractmethod
    async def probe_providers(self) -> list[GatewayProbeResult]:
        """Probe live connectivity and roundtrip latency across upstream providers."""
        pass
