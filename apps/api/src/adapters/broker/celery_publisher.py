"""Celery task publisher adapter — sends tasks from the API to the worker.

Keeps Celery import out of business logic; the adapter is the only import site.
"""

import os

from celery import Celery

celery_app = Celery(
    "retriever",
    broker=os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"),
)
