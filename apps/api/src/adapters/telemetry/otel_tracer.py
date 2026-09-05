"""OpenTelemetry tracer adapter.

Implements the Tracer port using OpenTelemetry SDK with OTLP export,
W3C traceparent context propagation, and request lifecycle instrumentation.
"""

import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.domain.abstractions.telemetry import Tracer


class OTelTracer(Tracer):
    """OpenTelemetry-backed tracer implementation with W3C propagation.

    Attributes:
        provider: Configured TracerProvider (shared across the process).
    """

    def __init__(
        self,
        service_name: str = "retriever-api",
        environment: str = "development",
        otlp_endpoint: str = "",
    ) -> None:
        resource = Resource.create({
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: environment,
        })
        provider = TracerProvider(resource=resource)

        # Always log spans to console in development (skip under pytest to prevent unclosed background workers)
        if environment == "development" and "pytest" not in sys.modules:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # Send spans via OTLP when an endpoint is configured
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service_name)
        self._provider = provider
        self._propagator = TraceContextTextMapPropagator()

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: dict[str, str] | None = None,
        context: Context | None = None,
    ) -> Generator[Any, None, None]:
        """Start a span as a context manager with optional parent context."""
        kwargs: dict[str, Any] = {}
        if context is not None:
            kwargs["context"] = context
        with self._tracer.start_as_current_span(name, **kwargs) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            yield span


    def get_tracer(self) -> Any:
        """Return the underlying OTel tracer for advanced usage."""
        return self._tracer

    def force_flush(self) -> None:
        """Flush all pending spans (useful during shutdown)."""
        self._provider.force_flush()

    def extract_context(self, carrier: dict[str, str]) -> Context:
        """Extract W3C traceparent context from request headers dictionary."""
        return self._propagator.extract(carrier=carrier)

    def inject_context(self, carrier: dict[str, str]) -> None:
        """Inject current active span W3C traceparent into dictionary."""
        self._propagator.inject(carrier=carrier)

    @staticmethod
    def get_current_trace_id() -> str:
        """Return the 32-hex character trace ID of the currently active span."""
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id != 0:
            return format(ctx.trace_id, "032x")
        return "0" * 32

    @staticmethod
    def get_current_span_id() -> str:
        """Return the 16-hex character span ID of the currently active span."""
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.span_id != 0:
            return format(ctx.span_id, "016x")
        return "0" * 16

    @classmethod
    def get_current_traceparent(cls) -> str:
        """Return formatted W3C traceparent header string."""
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id != 0:
            trace_id = format(ctx.trace_id, "032x")
            span_id = format(ctx.span_id, "016x")
            flags = format(ctx.trace_flags, "02x")
            return f"00-{trace_id}-{span_id}-{flags}"
        return "00-" + "0" * 32 + "-" + "0" * 16 + "-01"

    def shutdown(self) -> None:
        """Shut down the tracer provider to flush and stop all span processors."""
        if hasattr(self, "_provider") and self._provider is not None:
            self._provider.shutdown()


