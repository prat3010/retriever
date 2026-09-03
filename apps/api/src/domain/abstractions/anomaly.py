"""Domain abstractions for Telemetry Anomaly Detection & Quota Abuse Guard (Milestone 83)."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)



class AnomalyFeatureVector(BaseModel):
    """Extracted behavioral metrics for an API key or tenant within a sliding window."""

    entity_id: str = Field(..., description="Unique API key ID or Tenant ID being monitored")
    entity_type: Literal["api_key", "tenant"] = Field(
        default="api_key", description="Entity category: 'api_key' | 'tenant'"
    )
    tenant_id: str = Field(..., description="Owning tenant UUID")
    window_start: datetime = Field(..., description="Start of observation window")
    window_end: datetime = Field(..., description="End of observation window")
    request_count: int = Field(default=0, ge=0, description="Total requests observed in window")
    request_velocity_rpm: float = Field(
        default=0.0, ge=0.0, description="Requests per minute velocity"
    )
    input_tokens_avg: float = Field(default=0.0, ge=0.0, description="Mean input tokens per request")
    output_tokens_avg: float = Field(
        default=0.0, ge=0.0, description="Mean output tokens per request"
    )
    token_ratio: float = Field(
        default=0.0,
        ge=0.0,
        description="Ratio of input tokens to output tokens (indicative of extraction attacks)",
    )
    prompt_entropy: float = Field(
        default=0.0,
        ge=0.0,
        description="Character/token Shannon entropy of prompt distribution",
    )
    p99_latency_ms: float = Field(
        default=0.0, ge=0.0, description="P99 execution latency in milliseconds"
    )
    latency_variance: float = Field(
        default=0.0, ge=0.0, description="Variance of request execution times"
    )
    error_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Ratio of failed / rejected requests"
    )
    cost_velocity_usd: float = Field(
        default=0.0, ge=0.0, description="Hourly token cost run-rate in USD"
    )


class AnomalyScore(BaseModel):
    """Calibrated anomaly score and explanatory factor breakdown."""

    entity_id: str = Field(..., description="Evaluated entity ID (API key or Tenant)")
    entity_type: Literal["api_key", "tenant"] = Field(default="api_key")
    tenant_id: str = Field(..., description="Owning tenant UUID")
    anomaly_score: float = Field(
        ..., ge=0.0, le=1.0, description="Calibrated anomaly probability (0.0=nominal, 1.0=anomaly)"
    )
    is_anomaly: bool = Field(
        default=False, description="True if anomaly score exceeds operational threshold"
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        default="LOW", description="Qualitative risk classification"
    )
    contributing_factors: list[str] = Field(
        default_factory=list, description="Human-readable explanations for why this entity was flagged"
    )
    algorithm_used: str = Field(
        default="isolation_forest",
        description="Detection algorithm used: 'isolation_forest' | 'numpy_multivariate_baseline'",
    )
    features: dict[str, float] = Field(
        default_factory=dict, description="Raw normalized feature map evaluated by the model"
    )
    detected_at: datetime = Field(
        default_factory=utc_now, description="Timestamp of anomaly evaluation"
    )


class QuarantineRecord(BaseModel):
    """Quarantine status and audit metadata for a compromised or abusive credential."""

    key_id: str = Field(..., description="Target API key UUID")
    tenant_id: str = Field(..., description="Owning tenant UUID")
    status: Literal["active", "quarantined", "suspended"] = Field(default="quarantined")
    reason: str = Field(..., description="Justification for quarantine enforcement")
    risk_level: Literal["HIGH", "CRITICAL"] = Field(default="CRITICAL")
    quarantined_at: datetime = Field(default_factory=utc_now)

    quarantined_by: str = Field(default="anomaly_sentinel")
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class AnomalyFilterParams(BaseModel):
    """Search and filter parameters for querying security anomaly events."""

    tenant_id: str | None = None
    risk_level: str | None = None
    status: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class BaseAnomalyDetector(ABC):
    """Abstract interface for unsupervised machine learning anomaly detection."""

    @abstractmethod
    def fit(self, feature_matrix: list[AnomalyFeatureVector]) -> None:
        """Fit unsupervised model on baseline feature observations."""
        pass

    @abstractmethod
    def score(self, vector: AnomalyFeatureVector) -> AnomalyScore:
        """Compute anomaly score and factor attribution for a single feature vector."""
        pass

    @abstractmethod
    def batch_detect(self, vectors: list[AnomalyFeatureVector]) -> list[AnomalyScore]:
        """Detect anomalies across a batch of feature vectors."""
        pass


class BaseAnomalyRepository(ABC):
    """Abstract persistence interface for security anomaly events and quarantine states."""

    @abstractmethod
    async def record_anomaly(
        self, score: AnomalyScore, raw_features: dict[str, Any] | None = None
    ) -> str:
        """Persist detected anomaly event and return generated anomaly ID."""
        pass

    @abstractmethod
    async def list_anomalies(
        self, filters: AnomalyFilterParams
    ) -> tuple[list[dict[str, Any]], int]:
        """Retrieve paginated anomaly events matching filter parameters."""
        pass

    @abstractmethod
    async def resolve_anomaly(
        self, anomaly_id: str, resolved_by: str, notes: str | None = None
    ) -> bool:
        """Mark an anomaly event as resolved or dismissed."""
        pass

    @abstractmethod
    async def quarantine_key(
        self, key_id: str, tenant_id: str, reason: str, level: str = "CRITICAL"
    ) -> bool:
        """Toggle API key status to quarantined and update audit records."""
        pass

    @abstractmethod
    async def unquarantine_key(self, key_id: str, resolved_by: str) -> bool:
        """Restore quarantined API key to active status."""
        pass
