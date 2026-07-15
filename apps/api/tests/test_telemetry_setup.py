"""Tests for telemetry setup module (M7: Observability & Hardening)."""

from unittest.mock import MagicMock, patch

import pytest

import src.adapters.telemetry.setup as telemetry_setup


@pytest.fixture(autouse=True)
def reset_singletons():
    saved = (
        telemetry_setup._tracer,
        telemetry_setup._metrics,
        telemetry_setup._rate_limiter,
    )
    telemetry_setup._tracer = None
    telemetry_setup._metrics = None
    telemetry_setup._rate_limiter = None
    yield
    telemetry_setup._tracer, telemetry_setup._metrics, telemetry_setup._rate_limiter = saved


@patch("src.adapters.telemetry.setup.OTelTracer")
@patch("src.adapters.telemetry.setup.settings")
def test_get_tracer_singleton(mock_settings, mock_tracer_cls):
    mock_settings.ENVIRONMENT = "test"
    mock_settings.OTLP_ENDPOINT = "http://localhost:4318"

    t1 = telemetry_setup.get_tracer()
    t2 = telemetry_setup.get_tracer()
    assert t1 is t2
    mock_tracer_cls.assert_called_once_with(
        service_name="retriever-api",
        environment="test",
        otlp_endpoint="http://localhost:4318",
    )


@patch("src.adapters.telemetry.setup.PrometheusMetricsRegistry")
def test_get_metrics_singleton(mock_metrics_cls):
    m1 = telemetry_setup.get_metrics()
    m2 = telemetry_setup.get_metrics()
    assert m1 is m2
    mock_metrics_cls.assert_called_once()


@patch("src.adapters.telemetry.setup.settings")
def test_get_rate_limiter_disabled(mock_settings):
    mock_settings.RATE_LIMIT_ENABLED = False
    assert telemetry_setup.get_rate_limiter() is None


@patch("src.adapters.telemetry.setup.RedisSlidingWindowRateLimiter")
@patch("src.adapters.telemetry.setup.settings")
def test_get_rate_limiter_enabled(mock_settings, mock_limiter_cls):
    mock_settings.RATE_LIMIT_ENABLED = True
    mock_settings.RATE_LIMIT_WINDOW_SECONDS = 60
    mock_settings.RATE_LIMIT_MAX_REQUESTS = 100

    from src.adapters.cache.config_cache import redis_client
    limiter = telemetry_setup.get_rate_limiter()
    assert limiter is not None
    mock_limiter_cls.assert_called_once_with(
        redis_client=redis_client,
        window_seconds=60,
        max_requests=100,
    )


@patch("src.adapters.telemetry.setup.get_metrics")
@patch("src.adapters.telemetry.setup.get_tracer")
@patch("src.adapters.telemetry.setup.setup_logging")
@patch("src.adapters.telemetry.setup.setup_middleware")
@patch("src.adapters.telemetry.setup.settings")
def test_init_telemetry_calls_all(
    mock_settings, mock_middleware, mock_logging, mock_tracer, mock_metrics,
):
    mock_settings.ENVIRONMENT = "test"
    mock_settings.LOG_LEVEL = "DEBUG"

    app = MagicMock()
    telemetry_setup.init_telemetry(app)

    mock_logging.assert_called_once_with(environment="test", log_level="DEBUG")
    mock_tracer.assert_called_once()
    mock_metrics.assert_called_once()
    mock_middleware.assert_called_once_with(app)


@patch("src.adapters.telemetry.setup.get_metrics")
@patch("src.adapters.telemetry.setup.get_tracer")
@patch("src.adapters.telemetry.setup.setup_logging")
@patch("src.adapters.telemetry.setup.setup_middleware")
@patch("src.adapters.telemetry.setup.settings")
def test_init_telemetry_registers_metrics_route(
    mock_settings, mock_middleware, mock_logging, mock_tracer, mock_metrics,
):
    mock_settings.ENVIRONMENT = "test"
    mock_settings.LOG_LEVEL = "DEBUG"

    app = MagicMock()
    telemetry_setup.init_telemetry(app)

    app.get.assert_called_once_with("/metrics", include_in_schema=False)
