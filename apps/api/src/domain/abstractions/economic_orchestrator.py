"""Economic Orchestrator & Smart Tool Gateway Domain Abstractions (M105).

Pure domain models and interfaces for complexity-based model routing,
mid-flight reasoning escalation, and multi-model economic ledger accounting.
Contains zero infrastructure, framework, or database imports.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ModelTier(StrEnum):
    """Execution tiers for multi-model cognitive orchestration."""

    MID_TIER = "mid_tier"
    FRONTIER = "frontier"


class EscalationReason(StrEnum):
    """Reason why an active reasoning thread was escalated from mid-tier to frontier."""

    STEP_COUNT_THRESHOLD = "step_count_threshold"
    UNRECOVERED_TOOL_EXCEPTION = "unrecovered_tool_exception"
    SELF_HEALING_FAILED = "self_healing_failed"
    CIRCUIT_BREAKER_WARNING = "circuit_breaker_warning"
    AMBIGUOUS_OUTPUT = "ambiguous_output"
    DIRECT_OVERRIDE = "direct_override"


class TaskComplexity(BaseModel):
    """Evaluation of query complexity and tier assignment."""

    score: float = Field(..., ge=0.0, le=1.0, description="Normalized complexity score from 0.0 to 1.0")
    tier_assigned: ModelTier
    estimated_steps: int = Field(default=1, ge=1, le=20)
    rationale: str
    requires_code_execution: bool = False
    requires_multi_hop: bool = False
    requires_mathematical_synthesis: bool = False


class EscalationEvent(BaseModel):
    """Record of a mid-flight escalation from mid-tier to frontier model."""

    step_index: int = Field(..., ge=0)
    from_model: str
    to_model: str
    reason: EscalationReason
    details: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class EconomicLedgerRecord(BaseModel):
    """Economic transaction record detailing token spend, counterfactual costs, and net savings."""

    tenant_id: str
    thread_id: str
    query_preview: str
    mid_tier_tokens: int = 0
    frontier_tokens: int = 0
    total_tokens: int = 0
    actual_cost_usd: float = 0.0
    counterfactual_frontier_cost_usd: float = 0.0
    net_savings_usd: float = 0.0
    savings_percentage: float = 0.0
    escalated: bool = False
    escalation_reason: EscalationReason | None = None
    timestamp: datetime = Field(default_factory=_utc_now)


class EconomicLedgerSummary(BaseModel):
    """Aggregated economic metrics for a tenant or platform fleet."""

    tenant_id: str
    total_queries: int = 0
    total_tokens: int = 0
    mid_tier_query_count: int = 0
    frontier_query_count: int = 0
    escalated_query_count: int = 0
    mid_tier_share_percentage: float = 0.0
    escalation_rate_percentage: float = 0.0
    total_actual_cost_usd: float = 0.0
    total_counterfactual_cost_usd: float = 0.0
    total_savings_usd: float = 0.0
    average_savings_percentage: float = 0.0
    records: list[EconomicLedgerRecord] = Field(default_factory=list)


class EconomicOrchestratorProtocol(ABC):
    """Abstract port for complexity analysis, escalation checks, and economic telemetry."""

    @abstractmethod
    def classify_complexity(self, query: str, allowed_tools: list[str] | None = None) -> TaskComplexity:
        """Classify task difficulty and determine appropriate starting tier."""
        pass

    @abstractmethod
    def should_escalate(
        self,
        current_tier: ModelTier,
        step_index: int,
        last_tool_error: bool = False,
        self_healing_attempted: bool = False,
        circuit_breaker_tripped: bool = False,
    ) -> tuple[bool, EscalationReason | None, str]:
        """Determine if a mid-tier execution must escalate to frontier tier."""
        pass

    @abstractmethod
    def record_transaction(
        self,
        tenant_id: str,
        thread_id: str,
        query: str,
        mid_tier_tokens: int,
        frontier_tokens: int,
        mid_tier_model: str,
        frontier_model: str,
        escalated: bool = False,
        escalation_reason: EscalationReason | None = None,
    ) -> EconomicLedgerRecord:
        """Calculate costs and record economic savings."""
        pass

    @abstractmethod
    def get_ledger_summary(self, tenant_id: str) -> EconomicLedgerSummary:
        """Retrieve aggregated economic ledger summary for tenant."""
        pass
