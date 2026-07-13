"""Prometheus metrics adapter.

Implements the MetricsRegistry port using prometheus_client, exposing
a ``/metrics`` endpoint for scraping.
"""


from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

from src.domain.abstractions.telemetry import MetricsRegistry

# ── Pre-defined metric descriptors ──────────────────────────────────────────

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "HTTP Request latency distribution.",
    labelnames=["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

TOKEN_CONSUMPTION = Counter(
    "tenant_token_consumption_total",
    "Accumulated token consumption per tenant.",
    labelnames=["tenant_id", "model", "type"],
)

QUEUE_BACKPRESSURE = Gauge(
    "worker_queue_backpressure",
    "Active items in worker message queues.",
    labelnames=["queue_name"],
)

RLS_VIOLATIONS = Counter(
    "rls_violation_total",
    "Count of RLS mismatch breaches triggered.",
    labelnames=["tenant_id"],
)


class PrometheusMetricsRegistry(MetricsRegistry):
    """Prometheus-backed metrics registry."""

    def increment(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        _get_or_create_counter(name, labels or {}).inc(value)

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        _get_or_create_histogram(name, labels or {}).observe(value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        _get_or_create_gauge(name, labels or {}).set(value)

    @staticmethod
    def generate_latest() -> bytes:
        """Return the latest Prometheus metrics payload."""
        return generate_latest(REGISTRY)


# ── Metric registry helpers (lazy creation for custom metrics) ──────────────

_counter_registry: dict[str, Counter] = {}
_histogram_registry: dict[str, Histogram] = {}
_gauge_registry: dict[str, Gauge] = {}


def _get_or_create_counter(name: str, labels: dict[str, str]) -> Counter:
    if name not in _counter_registry:
        _counter_registry[name] = Counter(name, f"Counter: {name}", labelnames=list(labels))
    return _counter_registry[name].labels(**labels)


def _get_or_create_histogram(name: str, labels: dict[str, str]) -> Histogram:
    if name not in _histogram_registry:
        _histogram_registry[name] = Histogram(name, f"Histogram: {name}", labelnames=list(labels))
    return _histogram_registry[name].labels(**labels)


def _get_or_create_gauge(name: str, labels: dict[str, str]) -> Gauge:
    if name not in _gauge_registry:
        _gauge_registry[name] = Gauge(name, f"Gauge: {name}", labelnames=list(labels))
    return _gauge_registry[name].labels(**labels)
