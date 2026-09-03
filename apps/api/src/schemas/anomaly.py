"""Pydantic schemas for Telemetry Anomaly Sentinel & Abuse Guard API."""

from typing import Literal

from pydantic import BaseModel, Field


class ScanTelemetryRequest(BaseModel):
    """Payload to trigger an on-demand telemetry anomaly detection scan."""

    lookback_minutes: int = Field(default=60, ge=5, le=1440, description="Window duration in minutes")
    tenant_id: str | None = Field(default=None, description="Optional tenant UUID filter")
    auto_quarantine: bool = Field(default=True, description="Automatically quarantine CRITICAL risk keys")


class ResolveAnomalyRequest(BaseModel):
    """Payload to resolve or dismiss a flagged security anomaly."""

    notes: str | None = Field(default=None, description="Resolution notes or justification")


class QuarantineKeyRequest(BaseModel):
    """Payload to manually quarantine an API key."""

    tenant_id: str = Field(..., description="Owning tenant UUID")
    reason: str = Field(default="Manual administrator quarantine", description="Justification")
    level: Literal["HIGH", "CRITICAL"] = Field(default="CRITICAL")


class AnomalyItemResponse(BaseModel):
    """Summary representation of a security anomaly event."""

    anomaly_id: str
    tenant_id: str
    entity_id: str
    entity_type: str
    key_id: str | None
    risk_level: str
    anomaly_score: float
    algorithm_used: str
    features: dict[str, float]
    contributing_factors: list[str]
    is_quarantined: bool
    status: str
    created_at: str | None
    resolved_at: str | None
    resolved_by: str | None
    notes: str | None


class AnomalyListResponse(BaseModel):
    """Paginated list of telemetry anomalies."""

    total: int
    items: list[AnomalyItemResponse]
    limit: int
    offset: int
