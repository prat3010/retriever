"""Telemetry initialization helper.

Wires up OpenTelemetry tracing, Prometheus metrics, structlog logging,
and registers FastAPI middleware.
"""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from src.adapters.telemetry.logger import get_logger, setup_logging
from src.adapters.telemetry.middleware import setup_middleware
from src.adapters.telemetry.otel_tracer import OTelTracer
from src.adapters.telemetry.prometheus_metrics import PrometheusMetricsRegistry
from src.adapters.telemetry.rate_limiter import RedisSlidingWindowRateLimiter
from src.config import settings

logger = get_logger(__name__)

# ── Singleton instances (lazily initialised) ────────────────────────────────

_tracer: OTelTracer | None = None
_metrics: PrometheusMetricsRegistry | None = None
_rate_limiter: RedisSlidingWindowRateLimiter | None = None


def get_tracer() -> OTelTracer:
    global _tracer
    if _tracer is None:
        _tracer = OTelTracer(
            service_name="retriever-api",
            environment=settings.ENVIRONMENT,
            otlp_endpoint=settings.OTLP_ENDPOINT,
        )
    return _tracer


def get_metrics() -> PrometheusMetricsRegistry:
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetricsRegistry()
    return _metrics


def get_rate_limiter() -> RedisSlidingWindowRateLimiter | None:
    global _rate_limiter
    if _rate_limiter is None and settings.RATE_LIMIT_ENABLED:
        from src.adapters.cache.config_cache import redis_client
        _rate_limiter = RedisSlidingWindowRateLimiter(
            redis_client=redis_client,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
        )
    return _rate_limiter


def init_telemetry(app: FastAPI) -> None:
    """Initialise all telemetry subsystems and register on *app*."""
    # 1. Structured logging
    setup_logging(environment=settings.ENVIRONMENT, log_level=settings.LOG_LEVEL)

    # 2. Tracing (initialise eagerly to capture startup spans)
    get_tracer()

    # 3. Metrics
    get_metrics()

    # 4. Middleware
    setup_middleware(app)

    # 5. Metrics endpoint (scraped by Prometheus)
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> PlainTextResponse:
        from src.adapters.telemetry.prometheus_metrics import PrometheusMetricsRegistry
        return PlainTextResponse(
            content=PrometheusMetricsRegistry.generate_latest().decode("utf-8"),
            media_type="text/plain; version=0.0.4",
        )

    logger.info("telemetry_initialised", environment=settings.ENVIRONMENT)
