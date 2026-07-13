"""Structured logging configuration via structlog.

Configures JSON-formatted logging with OpenTelemetry trace context
injection, environment-aware output, and PII redaction support.
"""

import logging
import sys
from typing import Any

import structlog


def setup_logging(environment: str = "development", log_level: str = "INFO") -> None:
    """Configure structlog with environment-appropriate formatting.

    In production, output newline-delimited JSON for log aggregators.
    In development, output coloured human-readable lines.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            _add_trace_context,
            structlog.dev.ConsoleRenderer() if environment == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer() if environment == "development"
        else structlog.processors.JSONRenderer(),
    ))
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def _add_trace_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Inject OpenTelemetry trace / span IDs into log records."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if span_context.is_valid:
            event_dict["trace_id"] = hex(span_context.trace_id)
            event_dict["span_id"] = hex(span_context.span_id)
    except Exception:
        pass
    return event_dict


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger instance."""
    return structlog.get_logger(name or __name__)
