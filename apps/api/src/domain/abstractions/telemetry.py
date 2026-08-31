"""Telemetry Domain Abstractions (Ports).

Defines pure domain interfaces for tracing, metrics, rate limiting,
live database telemetry aggregations, and multi-channel SLA alerts.
Contains zero infrastructure imports.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class Tracer(ABC):
    """Port for distributed tracing — OpenTelemetry spans."""

    @abstractmethod
    def start_span(
        self, name: str, attributes: dict[str, str] | None = None
    ) -> Any:
        """Start a span, returning a context manager."""
        pass


class MetricsRegistry(ABC):
    """Port for application metrics — counters, histograms, gauges."""

    @abstractmethod
    def increment(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        pass

    @abstractmethod
    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a value for a histogram metric."""
        pass

    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric to an absolute value."""
        pass


class RateLimitResult:
    def __init__(self, allowed: bool, limit: int, remaining: int, reset_after: int) -> None:
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_after = reset_after

    def __bool__(self) -> bool:
        return self.allowed


class RateLimiter(ABC):
    """Port for rate limiting — token-bucket / sliding-window checks."""

    @abstractmethod
    async def acquire(self, key: str, cost: float = 1.0) -> RateLimitResult:
        """Attempt to consume *cost* tokens for *key*."""
        pass


class TenantLiveTelemetry(BaseModel):
    """Live aggregated telemetry metrics for a tenant workspace."""

    tenant_id: str
    monthly_tokens_used: int = 0
    documents_count: int = 0
    storage_bytes_used: int = 0
    cache_hits: int = 0
    latency_saved_ms: int = 0
    cost_saved_usd: float = 0.0
    thumbs_up: int = 0
    thumbs_down: int = 0
    satisfaction_rate: int = 100
    avg_faithfulness: float = 1.0
    avg_precision: float = 1.0
    hallucination_index: float = 0.0
    p99_latency_ms: float = 0.0


class AlertPayload(BaseModel):
    """Normalized multi-channel incident alert payload."""

    alert_id: str
    tenant_id: str
    rule_name: str
    severity: str = "WARNING"  # "INFO" | "WARNING" | "CRITICAL"
    title: str
    description: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


class TenantAlertConfig(BaseModel):
    """Webhook and notification destination configuration for tenant SLA alerts."""

    tenant_id: str
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None
    custom_webhook_url: str | None = None
    email_recipient: str | None = None
    enabled_rules: list[str] = Field(
        default_factory=lambda: [
            "hallucination_spike",
            "token_quota_threshold",
            "latency_spike",
            "tenancy_breach",
        ]
    )
    min_interval_minutes: int = 15


class BaseAlertService(ABC):
    """Port for SLA webhook and incident alerting."""

    @abstractmethod
    async def evaluate_and_dispatch(
        self,
        tenant_id: str,
        telemetry: TenantLiveTelemetry,
        token_quota_max: int,
        config: TenantAlertConfig | None = None,
    ) -> list[AlertPayload]:
        """Evaluate telemetry against alert rules and dispatch notifications."""
        pass

    @abstractmethod
    async def dispatch_test_alert(
        self, tenant_id: str, channel: str, webhook_url: str
    ) -> dict[str, Any]:
        """Send a test incident alert to verify webhook integration."""
        pass
