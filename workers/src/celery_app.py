"""Celery application configuration for Retriever background workers.

Broker: RabbitMQ (ADR-004)
Result Backend: Redis (ADR-005)

Task routing segregates resource-heavy parsing from API-bound embedding
into separate worker pools with distinct concurrency and retry policies.
"""

import os
from celery import Celery
from celery.signals import worker_process_init


@worker_process_init.connect
def init_sentry(**kwargs):
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.opentelemetry import OpenTelemetryIntegration

    environment = os.environ.get("ENVIRONMENT", "development")
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        send_default_pii=False,
        integrations=[
            CeleryIntegration(),
            OpenTelemetryIntegration(),
        ],
    )

RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"
)
REDIS_URL = os.environ.get(
    "REDIS_URL", "redis://localhost:6379/0"
)

celery_app = Celery(
    "retriever",
    broker=RABBITMQ_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_result_expires=3600,
    result_expires=3600,
    task_routes={
        "workers.src.tasks.process_document": {
            "queue": "ingestion.parse",
            "routing_key": "ingestion.parse",
        },
        "workers.src.tasks.generate_embeddings": {
            "queue": "knowledge.embed",
            "routing_key": "knowledge.embed",
        },
        "workers.src.tasks.reconcile_stalled": {
            "queue": "periodic",
            "routing_key": "periodic.reconcile",
        },
        "workers.src.tasks.eval_tasks.run_evaluation": {
            "queue": "evaluation",
            "routing_key": "evaluation.run",
        },
        "workers.src.tasks.eval_tasks.run_scheduled_evaluations": {
            "queue": "periodic",
            "routing_key": "periodic.evaluation",
        },
    },
    task_annotations={
        "workers.src.tasks.process_document": {
            "rate_limit": "10/m",
        },
    },
    beat_schedule={
        "reconcile-stalled-documents": {
            "task": "workers.src.tasks.reconcile_stalled",
            "schedule": 900.0,
            "args": (),
        },
        "nightly-evaluation": {
            "task": "workers.src.tasks.eval_tasks.run_scheduled_evaluations",
            "schedule": 43200.0,
            "args": (),
        },
    },
)
