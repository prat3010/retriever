"""Unit and API tests for Milestone 75: Full-Stack OpenTelemetry Auto-Instrumentation & Distributed Tracing."""

from fastapi.testclient import TestClient

from src.adapters.telemetry.auto_instrumentation import registry
from src.adapters.telemetry.otel_tracer import OTelTracer
from src.config import settings
from src.main import app

client = TestClient(app)


# ── 1. Unit Tests: OTel Tracer W3C Propagation Helpers ───────────────────────

def test_otel_tracer_w3c_helpers():
    """Verify OTelTracer extracts, injects, and formats W3C traceparents."""
    from src.adapters.telemetry.setup import get_tracer
    tracer = get_tracer()

    # Format traceparent with active span
    with tracer.start_span("test-span"):
        trace_id = OTelTracer.get_current_trace_id()
        span_id = OTelTracer.get_current_span_id()
        traceparent = OTelTracer.get_current_traceparent()

        assert len(trace_id) == 32
        assert len(span_id) == 16
        assert traceparent.startswith(f"00-{trace_id}-{span_id}-")

        # Injection check
        carrier: dict[str, str] = {}
        tracer.inject_context(carrier)
        assert "traceparent" in carrier
        assert carrier["traceparent"] == traceparent


def test_auto_instrumentation_registry_status():
    """Verify AutoInstrumentationRegistry exposes instrumentor status."""
    status = registry.get_status()
    assert "sqlalchemy_instrumented" in status
    assert "httpx_instrumented" in status
    assert "celery_instrumented" in status
    assert status["httpx_instrumented"] is True
    assert status["celery_instrumented"] is True


# ── 2. API Tests: Gateway Trace Propagation & Header Reflection ───────────────

def test_w3c_traceparent_header_propagation():
    """Verify incoming W3C traceparent header is preserved across the HTTP gateway."""
    custom_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    custom_span_id = "00f067aa0ba902b7"
    incoming_traceparent = f"00-{custom_trace_id}-{custom_span_id}-01"

    response = client.get(
        "/health/liveness",
        headers={"traceparent": incoming_traceparent},
    )

    assert response.status_code == 200
    assert "X-Trace-Id" in response.headers
    assert response.headers["X-Trace-Id"] == custom_trace_id
    assert "traceparent" in response.headers
    assert response.headers["traceparent"].startswith(f"00-{custom_trace_id}-")


def test_auto_generated_trace_id_when_missing():
    """Verify gateway auto-generates a valid 32-hex trace ID when no parent header is sent."""
    response = client.get("/health/liveness")

    assert response.status_code == 200
    assert "X-Trace-Id" in response.headers
    trace_id = response.headers["X-Trace-Id"]
    assert len(trace_id) == 32
    assert int(trace_id, 16) > 0  # Valid non-zero hex


def test_admin_trace_context_endpoint():
    """Verify GET /v1/admin/telemetry/trace-context endpoint."""
    response = client.get(
        "/v1/admin/telemetry/trace-context",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["w3c_propagation_enabled"] is True
    assert "auto_instrumentation" in data
    assert data["auto_instrumentation"]["httpx_instrumented"] is True
    assert "traceparent_sample" in data
    assert data["traceparent_sample"].startswith("00-")
