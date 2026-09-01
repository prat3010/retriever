"""Domain models and abstractions for Multi-Agent Consensus & Critic Reflection Loops."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class CriticEvaluation(BaseModel):
    """Factual evaluation report emitted by the Critic/Auditor Agent."""

    is_approved: bool = Field(..., description="True if response is 100% supported by document evidence")
    critique_score: float = Field(..., ge=0.0, le=1.0, description="Factual alignment score between 0.0 and 1.0")
    critique_feedback: str = Field(..., description="Actionable critique feedback for Generator revision")
    unsupported_claims: list[str] = Field(default_factory=list, description="List of unverified or hallucinated claims")


class ConsensusRequest(BaseModel):
    """Input payload to trigger a Multi-Agent Consensus reflection workflow."""

    tenant_id: str = Field(default="", description="Target multi-tenant workspace ID")
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

    @model_validator(mode="before")
    @classmethod
    def normalize_request(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "prompt" not in data and "query" in data:
                data["prompt"] = data["query"]
            if "generator_provider_name" not in data and "generator_provider" in data:
                data["generator_provider_name"] = data["generator_provider"]
            if "critic_provider_name" not in data and "critic_provider" in data:
                data["critic_provider_name"] = data["critic_provider"]
        return data


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
    answer: str | None = None
    generator_model: str | None = None
    critic_model: str | None = None
    iterations: int | None = None
    consensus_score: float | None = None

    @model_validator(mode="after")
    def populate_aliases(self) -> "ConsensusResult":
        if self.answer is None:
            self.answer = self.final_response
        if self.generator_model is None:
            self.generator_model = self.generator_used
        if self.critic_model is None:
            self.critic_model = self.critic_used
        if self.iterations is None:
            self.iterations = self.approved_on_round
        if self.consensus_score is None:
            if self.reflection_history:
                last = self.reflection_history[-1]
                if isinstance(last, dict) and "critique_score" in last:
                    self.consensus_score = float(last["critique_score"])
            if self.consensus_score is None:
                self.consensus_score = 1.0
        return self

