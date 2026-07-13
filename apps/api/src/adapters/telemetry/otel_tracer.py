"""OpenTelemetry tracer adapter.

Implements the Tracer port using OpenTelemetry SDK with OTLP export
and FastAPI request lifecycle instrumentation.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from src.domain.abstractions.telemetry import Tracer


class OTelTracer(Tracer):
    """OpenTelemetry-backed tracer implementation.

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

        # Always log spans to console in development
        if environment == "development":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # Send spans via OTLP when an endpoint is configured
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service_name)
        self._provider = provider

    @contextmanager
    def start_span(
        self, name: str, attributes: dict[str, str] | None = None
    ) -> Generator[Any, None, None]:
        """Start a span as a context manager."""
        with self._tracer.start_as_current_span(name) as span:
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
