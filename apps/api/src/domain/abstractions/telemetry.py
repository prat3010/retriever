"""Telemetry Domain Abstractions (Ports).

Defines pure domain interfaces for tracing, metrics, rate limiting, and
structured logging. Contains zero infrastructure imports.
"""

from abc import ABC, abstractmethod
from typing import Any


class Tracer(ABC):
    """Port for distributed tracing — OpenTelemetry spans."""

    @abstractmethod
    def start_span(
        self, name: str, attributes: dict[str, str] | None = None
    ) -> Any:
        """Start a span, returning a context manager.

        Usage::

            with tracer.start_span("my_span") as span:
                span.set_attribute("key", "value")
        """
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
        """Attempt to consume *cost* tokens for *key*.

        Returns RateLimitResult containing allowed status and metrics.
        """
        pass
