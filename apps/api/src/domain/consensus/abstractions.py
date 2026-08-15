"""Domain models and abstractions for Multi-Agent Consensus & Critic Reflection Loops."""

from typing import Any

from pydantic import BaseModel, Field


class CriticEvaluation(BaseModel):
    """Factual evaluation report emitted by the Critic/Auditor Agent."""

    is_approved: bool = Field(..., description="True if response is 100% supported by document evidence")
    critique_score: float = Field(..., ge=0.0, le=1.0, description="Factual alignment score between 0.0 and 1.0")
    critique_feedback: str = Field(..., description="Actionable critique feedback for Generator revision")
    unsupported_claims: list[str] = Field(default_factory=list, description="List of unverified or hallucinated claims")


class ConsensusRequest(BaseModel):
    """Input payload to trigger a Multi-Agent Consensus reflection workflow."""

    tenant_id: str = Field(..., description="Target multi-tenant workspace ID")
    prompt: str = Field(..., description="High-stakes user query or prompt")
    generator_provider_name: str | None = Field(
        default=None, description="Optional target LLM provider name for Generator role"
    )
    critic_provider_name: str | None = Field(
        default=None, description="Optional target LLM provider name for Critic/Auditor role"
    )
    max_reflection_rounds: int = Field(
        default=2, ge=1, le=5, description="Maximum critique and revision passes allowed"
    )


class ConsensusResult(BaseModel):
    """Output response returned by the Multi-Agent Consensus Engine."""

    tenant_id: str
    prompt: str
    final_response: str
    generator_used: str
    critic_used: str
    approved_on_round: int
    reflection_history: list[dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float
