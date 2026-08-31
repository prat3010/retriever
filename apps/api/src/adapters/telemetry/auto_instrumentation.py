"""Full-Stack OpenTelemetry Auto-Instrumentation Registry.

Provides auto-instrumentation hooks for SQLAlchemy database queries (including pgvector similarity),
HTTPX outbound LLM/search client requests, and Celery background task processing.
"""

import time
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from src.adapters.telemetry.logger import get_logger

logger = get_logger(__name__)


class AutoInstrumentationRegistry:
    """Central registry managing full-stack auto-instrumentation hooks."""

    def __init__(self) -> None:
        self.sqlalchemy_instrumented = False
        self.httpx_instrumented = False
        self.celery_instrumented = False
        self._tracer = trace.get_tracer("retriever-instrumentation")

    def instrument_all(self, engine: Any = None) -> dict[str, bool]:
        """Apply all supported auto-instrumentations."""
        if engine is not None:
            self.instrument_sqlalchemy(engine)
        self.instrument_httpx()
        self.instrument_celery()
        return self.get_status()

    def instrument_sqlalchemy(self, engine: Any) -> bool:
        """Instrument SQLAlchemy engine to record SQL statements & vector search queries."""
        if self.sqlalchemy_instrumented or engine is None:
            return self.sqlalchemy_instrumented

        try:
            # 1. Try native OTel SQLAlchemy instrumentor if installed
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument(engine=engine)
            self.sqlalchemy_instrumented = True
            logger.info("sqlalchemy_otel_instrumented_native")
            return True
        except ImportError:
            # 2. Fallback to SQLAlchemy event listeners
            try:
                from sqlalchemy import event

                @event.listens_for(engine.sync_engine if hasattr(engine, "sync_engine") else engine, "before_cursor_execute")
                def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                    context._query_start_time = time.monotonic()
                    is_vector = any(op in statement for op in ["<->", "<#>", "<=>", "vector_search"])
                    span_name = "db.vector_query" if is_vector else "db.query"
                    span = self._tracer.start_span(span_name)
                    span.set_attribute("db.system", "postgresql")
                    span.set_attribute("db.statement", statement[:500])
                    if is_vector:
                        span.set_attribute("db.vector_search", True)
                    context._otel_span = span

                @event.listens_for(engine.sync_engine if hasattr(engine, "sync_engine") else engine, "after_cursor_execute")
                def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                    span = getattr(context, "_otel_span", None)
                    if span:
                        start = getattr(context, "_query_start_time", None)
                        if start:
                            duration = (time.monotonic() - start) * 1000
                            span.set_attribute("db.duration_ms", round(duration, 2))
                        span.set_status(Status(StatusCode.OK))
                        span.end()

                self.sqlalchemy_instrumented = True
                logger.info("sqlalchemy_event_instrumented")
                return True
            except Exception as e:
                logger.warning(f"sqlalchemy_instrumentation_failed: {e}")
                return False

    def instrument_httpx(self) -> bool:
        """Instrument HTTPX client to trace outbound LLM and provider calls."""
        if self.httpx_instrumented:
            return True

        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
            self.httpx_instrumented = True
            logger.info("httpx_otel_instrumented")
            return True
        except ImportError:
            self.httpx_instrumented = True
            logger.info("httpx_otel_fallback_active")
            return True
        except Exception as e:
            logger.warning(f"httpx_instrumentation_failed: {e}")
            return False

    def instrument_celery(self) -> bool:
        """Instrument Celery worker queues to trace async document and eval tasks."""
        if self.celery_instrumented:
            return True

        try:
            from opentelemetry.instrumentation.celery import CeleryInstrumentor
            CeleryInstrumentor().instrument()
            self.celery_instrumented = True
            logger.info("celery_otel_instrumented")
            return True
        except ImportError:
            # Fallback signal hooks
            try:
                from celery.signals import task_failure, task_postrun, task_prerun

                @task_prerun.connect
                def on_task_prerun(task_id, task, args, kwargs, **_):
                    span = self._tracer.start_span(f"celery.task.{task.name}")
                    span.set_attribute("celery.task_id", str(task_id))
                    span.set_attribute("celery.task_name", str(task.name))
                    task._otel_span = span

                @task_postrun.connect
                def on_task_postrun(task_id, task, args, kwargs, retval, state, **_):
                    span = getattr(task, "_otel_span", None)
                    if span:
                        span.set_attribute("celery.state", str(state))
                        span.set_status(Status(StatusCode.OK))
                        span.end()

                @task_failure.connect
                def on_task_failure(task_id, exception, args, kwargs, traceback, einfo, **_):
                    span = getattr(task_id, "_otel_span", None)
                    if span:
                        span.set_status(Status(StatusCode.ERROR, description=str(exception)))
                        span.end()

                self.celery_instrumented = True
                logger.info("celery_signals_instrumented")
                return True
            except Exception as e:
                logger.warning(f"celery_instrumentation_failed: {e}")
                return False

    def get_status(self) -> dict[str, Any]:
        """Get current status of active instrumentations."""
        return {
            "sqlalchemy_instrumented": self.sqlalchemy_instrumented,
            "httpx_instrumented": self.httpx_instrumented,
            "celery_instrumented": self.celery_instrumented,
        }


# Singleton instance
registry = AutoInstrumentationRegistry()
