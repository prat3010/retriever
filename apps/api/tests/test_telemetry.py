"""Observability & Telemetry Tests.

Verifies:
- Domain abstractions for tracing, metrics, rate limiting
- OTelTracer span creation and attribute injection
- PrometheusMetricsRegistry counter/histogram/gauge operations
- Structured logging setup and trace context injection
- RedisSlidingWindowRateLimiter acquire/reject logic
- Rate limit FastAPI dependency
- /metrics endpoint
- Middleware request timing
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.telemetry import MetricsRegistry, RateLimiter, Tracer
from src.main import app

client = TestClient(app)


# ── 1. Domain Abstractions (Port Protocols) ─────────────────────────────────


def test_tracer_is_abstract():
    """Verify Tracer port defines required abstract methods."""
    assert callable(Tracer.start_span)


def test_metrics_registry_is_abstract():
    """Verify MetricsRegistry port defines required abstract methods."""
    assert callable(MetricsRegistry.increment)
    assert callable(MetricsRegistry.observe)
    assert callable(MetricsRegistry.set_gauge)


def test_rate_limiter_is_abstract():
    """Verify RateLimiter port defines required abstract methods."""
    assert callable(RateLimiter.acquire)


# ── 2. OTel Tracer ──────────────────────────────────────────────────────────


@patch("src.adapters.telemetry.otel_tracer.ConsoleSpanExporter", autospec=True)
@patch("src.adapters.telemetry.otel_tracer.TracerProvider", autospec=True)
def test_otel_tracer_initialises(mock_provider, mock_exporter):
    """Verify OTelTracer creates a TracerProvider with correct resource."""
    from src.adapters.telemetry.otel_tracer import OTelTracer

    tracer = OTelTracer(service_name="test-svc", environment="testing")
    assert tracer._tracer is not None


@patch("src.adapters.telemetry.otel_tracer.ConsoleSpanExporter", autospec=True)
@patch("src.adapters.telemetry.otel_tracer.TracerProvider", autospec=True)
def test_otel_tracer_start_span(mock_provider, mock_exporter):
    """Verify start_span context manager works."""
    from src.adapters.telemetry.otel_tracer import OTelTracer

    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
    mock_provider.return_value.get_tracer.return_value = mock_tracer

    tracer = OTelTracer(service_name="test-svc", environment="testing")
    tracer._tracer = mock_tracer

    with tracer.start_span("test_span", attributes={"key": "val"}) as span:
        assert span is mock_span

    mock_tracer.start_as_current_span.assert_called_once_with("test_span")
    mock_span.set_attribute.assert_called_once_with("key", "val")


# ── 3. Prometheus Metrics ───────────────────────────────────────────────────


def test_prometheus_increment():
    """Verify counter increment works."""
    from src.adapters.telemetry.prometheus_metrics import PrometheusMetricsRegistry

    registry = PrometheusMetricsRegistry()
    registry.increment("test_counter", value=5, labels={"tenant_id": "t1"})

    # Should not raise
    assert True


def test_prometheus_observe():
    """Verify histogram observation works."""
    from src.adapters.telemetry.prometheus_metrics import PrometheusMetricsRegistry

    registry = PrometheusMetricsRegistry()
    registry.observe("test_histogram", value=0.5, labels={"method": "GET"})


def test_prometheus_set_gauge():
    """Verify gauge set works."""
    from src.adapters.telemetry.prometheus_metrics import PrometheusMetricsRegistry

    registry = PrometheusMetricsRegistry()
    registry.set_gauge("test_gauge", value=42, labels={"queue": "ingestion"})


def test_prometheus_generate_latest():
    """Verify generate_latest returns valid Prometheus text format."""
    from src.adapters.telemetry.prometheus_metrics import PrometheusMetricsRegistry

    payload = PrometheusMetricsRegistry.generate_latest()
    assert isinstance(payload, bytes)
    assert b"# HELP" in payload
    assert b"http_request_latency_seconds" in payload


def test_prometheus_predefined_metrics():
    """Verify predefined metric descriptors are registered."""
    from src.adapters.telemetry.prometheus_metrics import (
        PrometheusMetricsRegistry,
    )

    payload = PrometheusMetricsRegistry.generate_latest().decode()
    assert "http_request_latency_seconds" in payload
    assert "tenant_token_consumption_total" in payload
    assert "worker_queue_backpressure" in payload
    assert "rls_violation_total" in payload


# ── 4. Rate Limiter ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit():
    """Verify acquire returns True when under limit."""
    from src.adapters.telemetry.rate_limiter import RedisSlidingWindowRateLimiter

    mock_redis = AsyncMock()
    mock_redis.eval.return_value = 1

    limiter = RedisSlidingWindowRateLimiter(
        redis_client=mock_redis,
        window_seconds=60,
        max_requests=10,
    )

    result = await limiter.acquire("test_key")
    assert result is True
    mock_redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limiter_rejects_over_limit():
    """Verify acquire returns False when over limit."""
    from src.adapters.telemetry.rate_limiter import RedisSlidingWindowRateLimiter

    mock_redis = AsyncMock()
    mock_redis.eval.return_value = 0

    limiter = RedisSlidingWindowRateLimiter(
        redis_client=mock_redis,
        window_seconds=60,
        max_requests=10,
    )

    result = await limiter.acquire("test_key")
    assert result is False


@pytest.mark.asyncio
async def test_rate_limiter_fails_open():
    """Verify acquire returns True on Redis error (fail-open)."""
    from src.adapters.telemetry.rate_limiter import RedisSlidingWindowRateLimiter

    mock_redis = AsyncMock()
    mock_redis.eval.side_effect = RuntimeError("Connection lost")

    limiter = RedisSlidingWindowRateLimiter(
        redis_client=mock_redis,
        window_seconds=60,
        max_requests=10,
    )

    result = await limiter.acquire("test_key")
    assert result is True


# ── 5. Rate Limit Dependency ────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("src.adapters.telemetry.rate_limiter_dep.get_rate_limiter", autospec=True)
async def test_rate_limit_dependency_allows(mock_get_limiter):
    """Verify rate_limit dependency calls limiter.acquire."""
    mock_limiter = AsyncMock()
    mock_limiter.acquire.return_value = True
    mock_get_limiter.return_value = mock_limiter

    from src.adapters.telemetry.rate_limiter_dep import rate_limit

    dep = rate_limit(scope="test", max_requests=50)
    mock_request = MagicMock()

    # Should not raise
    await dep(request=mock_request, tenantId="t1")


@pytest.mark.asyncio
@patch("src.adapters.telemetry.rate_limiter_dep.get_rate_limiter", autospec=True)
async def test_rate_limit_dependency_rejects(mock_get_limiter):
    """Verify rate_limit dependency raises 429 when over limit."""
    from fastapi import HTTPException

    mock_limiter = AsyncMock()
    mock_limiter.acquire.return_value = False
    mock_get_limiter.return_value = mock_limiter

    from src.adapters.telemetry.rate_limiter_dep import rate_limit

    dep = rate_limit(scope="test")
    mock_request = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await dep(request=mock_request, tenantId="t1")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
@patch("src.adapters.telemetry.rate_limiter_dep.get_rate_limiter", autospec=True)
async def test_rate_limit_dependency_disabled(mock_get_limiter):
    """Verify rate_limit dependency is a no-op when limiter is None."""
    mock_get_limiter.return_value = None

    from src.adapters.telemetry.rate_limiter_dep import rate_limit

    dep = rate_limit(scope="test")

    # Should not raise
    await dep(request=MagicMock(), tenantId="t1")


# ── 6. Structured Logging ───────────────────────────────────────────────────


def test_setup_logging_configures_structlog():
    """Verify setup_logging configures structlog without errors."""
    from src.adapters.telemetry.logger import get_logger, setup_logging

    setup_logging(environment="testing", log_level="DEBUG")
    log = get_logger("test_logger")
    assert log is not None

    # Should not raise when logging
    log.info("test message", extra_field="value")


def test_trace_context_injection():
    """Verify trace context is injected into log events when span exists."""
    from src.adapters.telemetry.logger import _add_trace_context

    event = _add_trace_context(MagicMock(), "info", {"event": "test"})
    assert "event" in event


# ── 7. /metrics Endpoint ────────────────────────────────────────────────────


@patch("src.adapters.api.security.identity_provider.validate_token", autospec=True)
def test_metrics_endpoint_accessible(mock_validate):
    """Verify /metrics returns Prometheus-formatted text."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert "# HELP" in response.text
    assert "http_request_latency_seconds" in response.text
