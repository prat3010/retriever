"""Schemas and DTOs for live telemetry and SLA webhook alerting."""

from typing import Any

from pydantic import BaseModel, Field


class TenantLiveTelemetryDTO(BaseModel):
    """Response DTO for real-time tenant telemetry metrics."""

    tenant_id: str
    monthly_tokens_used: int
    documents_count: int
    storage_bytes_used: int
    cache_hits: int
    latency_saved_ms: int
    cost_saved_usd: float
    thumbs_up: int
    thumbs_down: int
    satisfaction_rate: int
    avg_faithfulness: float
    avg_precision: float
    hallucination_index: float
    p99_latency_ms: float


class TestAlertRequest(BaseModel):
    """Request model to test webhook alert delivery."""

    channel: str = Field("slack", description="Target notification channel: 'slack', 'discord', or 'webhook'")
    webhook_url: str = Field(..., description="Target webhook endpoint URL")


class TestAlertResponse(BaseModel):
    """Response model for test alert delivery."""

    status: str
    channel: str
    webhook_url: str
    formatted_payload: dict[str, Any]
    timestamp: str


class AlertHistoryItemDTO(BaseModel):
    """DTO for an individual historical alert item."""

    alert_id: str
    tenant_id: str
    rule_name: str
    severity: str
    title: str
    description: str
    metrics: dict[str, Any]
    timestamp: str
