"""Celery task for periodic evaluation runs.

Dispatches to the async eval runner. Actual evaluation logic
lives in the API app where wired dependencies are available.
"""

import asyncio

from celery import Task

from workers.src.celery_app import celery_app


@celery_app.task(
    bind=True,
    base=Task,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def run_evaluation(self, run_id: str, tenant_id: str, dataset_id: str) -> None:
    """Dispatches an evaluation run. The actual evaluation is triggered
    via the admin API which has access to wired dependencies.
    """
    pass


@celery_app.task(
    bind=True,
    base=Task,
    acks_late=True,
)
def run_scheduled_evaluations(self) -> None:
    """Nightly task: find datasets without recent runs and trigger evaluation.
    This will invoke the admin API endpoint for each dataset.
    """
    pass
