"""FastAPI middleware for telemetry — request timing, span creation,
metric recording, and rate-limit enforcement.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.adapters.telemetry.logger import get_logger
from src.adapters.telemetry.prometheus_metrics import (
    HTTP_REQUEST_LATENCY,
)

logger = get_logger(__name__)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Records request latency, creates OTel spans, and exports metrics."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        route_path = request.url.path
        method = request.method
        start = time.monotonic()

        response = await call_next(request)

        duration = time.monotonic() - start

        # Record latency histogram
        HTTP_REQUEST_LATENCY.labels(method=method, route=route_path).observe(duration)

        # Structured access log
        logger.info(
            "request",
            method=method,
            path=route_path,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        return response


def setup_middleware(app: FastAPI) -> None:
    """Register telemetry middleware on the FastAPI app."""
    app.add_middleware(TelemetryMiddleware)
