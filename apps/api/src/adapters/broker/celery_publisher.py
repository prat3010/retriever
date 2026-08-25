"""Celery task publisher adapter — sends tasks from the API to the worker.

Keeps Celery import out of business logic; the adapter is the only import site.
"""

import os

from celery import Celery

broker_url = os.environ.get("BROKER_URL") or os.environ.get("REDIS_URL") or os.environ.get("RABBITMQ_URL") or "redis://localhost:6379/0"

celery_app = Celery(
    "retriever",
    broker=broker_url,
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
