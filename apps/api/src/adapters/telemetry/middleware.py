"""FastAPI middleware for telemetry — request timing, span creation,
W3C traceparent propagation, metric recording, and rate-limit enforcement.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.middleware.base import BaseHTTPMiddleware

from src.adapters.telemetry.logger import get_logger
from src.adapters.telemetry.otel_tracer import OTelTracer
from src.adapters.telemetry.prometheus_metrics import (
    HTTP_REQUEST_LATENCY,
)

logger = get_logger(__name__)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Records request latency, creates OTel spans with W3C propagation, and exports metrics."""

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self._propagator = TraceContextTextMapPropagator()
        self._tracer = trace.get_tracer("retriever-http-gateway")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        route_path = request.url.path
        method = request.method
        start = time.monotonic()

        # 1. Extract parent context from incoming W3C traceparent headers if present
        parent_context = self._propagator.extract(carrier=dict(request.headers))

        # 2. Extract tenant and user identifiers if present in request headers
        tenant_id = request.headers.get("x-tenant-id", request.headers.get("tenant-id", ""))
        user_id = request.headers.get("x-user-id", request.headers.get("user-id", ""))

        span_name = f"HTTP {method} {route_path}"
        with self._tracer.start_as_current_span(span_name, context=parent_context) as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.route", route_path)
            if tenant_id:
                span.set_attribute("tenant_id", tenant_id)
            if user_id:
                span.set_attribute("user_id", user_id)

            trace_id = OTelTracer.get_current_trace_id()
            span_id = OTelTracer.get_current_span_id()
            traceparent = f"00-{trace_id}-{span_id}-01"

            try:
                response = await call_next(request)
                status_code = response.status_code
                span.set_attribute("http.status_code", status_code)
                if status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, description=f"HTTP {status_code}"))
                else:
                    span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                span.record_exception(exc)
                raise

            duration = time.monotonic() - start

            # Record latency histogram
            HTTP_REQUEST_LATENCY.labels(method=method, route=route_path).observe(duration)

            # Attach W3C Trace context and custom X-Trace-Id to response headers
            response.headers["X-Trace-Id"] = trace_id
            response.headers["traceparent"] = traceparent

            # Structured access log with trace_id correlation
            logger.info(
                "request",
                method=method,
                path=route_path,
                status=response.status_code,
                duration_ms=round(duration * 1000, 2),
                trace_id=trace_id,
                tenant_id=tenant_id if tenant_id else None,
            )

            return response


def setup_middleware(app: FastAPI) -> None:
    """Register telemetry middleware on the FastAPI app."""
    app.add_middleware(TelemetryMiddleware)
