"""Tests for worker infrastructure: engine lifecycle, Celery app config, eval stubs."""

from unittest.mock import MagicMock, patch

# ── get_engine / set_engine ────────────────────────────────────────────────


def test_get_engine_lazy_init() -> None:
    import workers.src.tasks
    workers.src.tasks._engine = None

    with patch("workers.src.tasks.create_async_engine") as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine

        engine_1 = workers.src.tasks.get_engine()
        engine_2 = workers.src.tasks.get_engine()

        assert engine_1 is mock_engine
        assert engine_2 is mock_engine
        mock_create.assert_called_once()


def test_set_engine_overrides() -> None:
    import workers.src.tasks

    mock_engine = MagicMock()
    workers.src.tasks.set_engine(mock_engine)

    assert workers.src.tasks.get_engine() is mock_engine

    workers.src.tasks._engine = None  # ponytail: cleanup for other tests


# ── Celery app configuration ────────────────────────────────────────────────


def test_celery_app_queues_and_routing() -> None:
    from workers.src.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert "workers.src.tasks.process_document" in routes
    assert routes["workers.src.tasks.process_document"]["queue"] == "ingestion.parse"
    assert "workers.src.tasks.generate_embeddings" in routes
    assert routes["workers.src.tasks.generate_embeddings"]["queue"] == "knowledge.embed"


def test_celery_beat_schedule_entries() -> None:
    from workers.src.celery_app import celery_app

    beat = celery_app.conf.beat_schedule
    assert beat is not None
    task_names = {v["task"] for v in beat.values()}
    assert "workers.src.tasks.reconcile_stalled" in task_names
    assert "workers.src.tasks.eval_tasks.run_scheduled_evaluations" in task_names


# ── eval_tasks stubs ────────────────────────────────────────────────────────


def test_eval_tasks_exist() -> None:
    from workers.src.tasks.eval_tasks import run_evaluation, run_scheduled_evaluations

    assert callable(run_evaluation)
    assert callable(run_scheduled_evaluations)
