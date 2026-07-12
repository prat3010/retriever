"""Workers Main Entrypoint.

Initializes the Celery application and binds task brokers based on environmental connection strings.
"""

from celery import Celery

import os

broker_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
backend_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# In a production context, setting broker configurations loads from settings
app = Celery(
    "retriever-workers",
    broker=broker_url,
    backend=backend_url,
    include=["src.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # Ensure late acks for consumer crash resiliency
    task_reject_on_worker_lost=True,
)

if __name__ == "__main__":
    app.start()
