import json
from uuid import uuid4

from sqlalchemy import text

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import EvalDatasetDb, EvalQuestionDb, EvalRunDb, EvalRunResultDb
from src.domain.abstractions.evaluation import (
    AggregateScores,
    DeepEvalScores,
    EvalDataset,
    EvalDatasetRepository,
    EvalQuestion,
    EvalRun,
    EvalRunRepository,
    EvalRunResult,
    EvalRunResultScores,
    RagasScores,
    SearchMetrics,
)


def _row_to_dataset(row) -> EvalDataset:
    return EvalDataset(
        dataset_id=str(row.dataset_id),
        tenant_id=str(row.tenant_id),
        name=row.name,
        description=row.description or "",
        question_count=getattr(row, "question_count", 0),
        created_at=str(row.created_at),
    )


def _row_to_question(row) -> EvalQuestion:
    return EvalQuestion(
        question_id=str(row.question_id),
        dataset_id=str(row.dataset_id),
        question=row.question,
        ground_truth_answer=row.ground_truth_answer,
        relevant_chunk_ids=list(row.relevant_chunk_ids or []),
    )


def _row_to_run(row) -> EvalRun:
    scores = row.aggregate_scores or {}
    return EvalRun(
        run_id=str(row.run_id),
        tenant_id=str(row.tenant_id),
        dataset_id=str(row.dataset_id),
        status=row.status,
        trigger=row.trigger,
        aggregate_scores=AggregateScores(**scores) if scores else AggregateScores(),
        question_count=row.question_count or 0,
        completed_count=row.completed_count or 0,
        created_at=str(row.created_at),
        completed_at=str(row.completed_at) if row.completed_at else None,
    )


def _row_to_result(row) -> EvalRunResult:
    scores_data = row.scores or {}
    return EvalRunResult(
        result_id=str(row.result_id),
        run_id=str(row.run_id),
        question_id=str(row.question_id),
        generated_answer=row.generated_answer or "",
        retrieved_chunk_ids=list(row.retrieved_chunk_ids or []),
        scores=EvalRunResultScores(**scores_data) if scores_data else EvalRunResultScores(),
        latency_ms=row.latency_ms or 0,
    )


class SqlEvalDatasetRepository(EvalDatasetRepository):

    async def create_dataset(self, dataset: EvalDataset) -> EvalDataset:
        async with tenant_session(tenant_id=dataset.tenant_id) as session:
            db = EvalDatasetDb(
                dataset_id=uuid4() if not dataset.dataset_id else uuid4(),
                tenant_id=dataset.tenant_id,
                name=dataset.name,
                description=dataset.description or None,
            )
            session.add(db)
            await session.flush()
            return _row_to_dataset(db)

    async def get_dataset(self, tenant_id: str, dataset_id: str) -> EvalDataset | None:
        async with tenant_session(tenant_id=tenant_id) as session:
            row = await session.get(EvalDatasetDb, dataset_id)
            if not row:
                return None
            return _row_to_dataset(row)

    async def list_datasets(self, tenant_id: str) -> list[EvalDataset]:
        async with tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text("""
                    SELECT d.*, COUNT(q.question_id) AS question_count
                    FROM eval_datasets d
                    LEFT JOIN eval_questions q ON q.dataset_id = d.dataset_id
                    WHERE d.tenant_id = :tenant_id
                    GROUP BY d.dataset_id
                    ORDER BY d.created_at DESC
                """),
                {"tenant_id": tenant_id},
            )
            return [_row_to_dataset(row) for row in result.fetchall()]

    async def delete_dataset(self, tenant_id: str, dataset_id: str) -> bool:
        async with tenant_session(tenant_id=tenant_id) as session:
            row = await session.get(EvalDatasetDb, dataset_id)
            if not row:
                return False
            await session.delete(row)
            return True

    async def add_question(self, question: EvalQuestion) -> EvalQuestion:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            db = EvalQuestionDb(
                dataset_id=question.dataset_id,
                question=question.question,
                ground_truth_answer=question.ground_truth_answer,
                relevant_chunk_ids=question.relevant_chunk_ids,
            )
            session.add(db)
            await session.flush()
            return _row_to_question(db)

    async def list_questions(self, dataset_id: str) -> list[EvalQuestion]:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            result = await session.execute(
                text("SELECT * FROM eval_questions WHERE dataset_id = :ds ORDER BY created_at"),
                {"ds": dataset_id},
            )
            return [_row_to_question(row) for row in result.fetchall()]

    async def delete_question(self, dataset_id: str, question_id: str) -> bool:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            row = await session.get(EvalQuestionDb, question_id)
            if not row:
                return False
            await session.delete(row)
            return True


class SqlEvalRunRepository(EvalRunRepository):

    async def create_run(self, run: EvalRun) -> EvalRun:
        async with tenant_session(tenant_id=run.tenant_id) as session:
            db = EvalRunDb(
                tenant_id=run.tenant_id,
                dataset_id=run.dataset_id,
                trigger=run.trigger,
            )
            session.add(db)
            await session.flush()
            return _row_to_run(db)

    async def get_run(self, tenant_id: str, run_id: str) -> EvalRun | None:
        async with tenant_session(tenant_id=tenant_id) as session:
            row = await session.get(EvalRunDb, run_id)
            if not row:
                return None
            return _row_to_run(row)

    async def list_runs(self, tenant_id: str, limit: int = 20) -> list[EvalRun]:
        async with tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text("""
                    SELECT * FROM eval_runs
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC LIMIT :lim
                """),
                {"tenant_id": tenant_id, "lim": limit},
            )
            return [_row_to_run(row) for row in result.fetchall()]

    async def update_run_status(self, run_id: str, status: str, aggregate_scores: dict | None = None) -> None:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            if aggregate_scores:
                await session.execute(
                    text("""
                        UPDATE eval_runs
                        SET status = :status, aggregate_scores = :scores,
                            completed_at = CASE WHEN :status = 'completed' THEN NOW() ELSE completed_at END
                        WHERE run_id = :run_id
                    """),
                    {"run_id": run_id, "status": status, "scores": json.dumps(aggregate_scores)},
                )
            else:
                await session.execute(
                    text("""
                        UPDATE eval_runs
                        SET status = :status,
                            completed_at = CASE WHEN :status = 'completed' THEN NOW() ELSE completed_at END
                        WHERE run_id = :run_id
                    """),
                    {"run_id": run_id, "status": status},
                )

    async def add_result(self, result: EvalRunResult) -> EvalRunResult:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            db = EvalRunResultDb(
                run_id=result.run_id,
                question_id=result.question_id,
                generated_answer=result.generated_answer,
                retrieved_chunk_ids=result.retrieved_chunk_ids,
                scores=result.scores.model_dump() if result.scores else {},
                latency_ms=result.latency_ms,
            )
            session.add(db)
            await session.flush()
            return _row_to_result(db)

    async def list_results(self, run_id: str) -> list[EvalRunResult]:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            result = await session.execute(
                text("SELECT * FROM eval_run_results WHERE run_id = :run_id ORDER BY created_at"),
                {"run_id": run_id},
            )
            return [_row_to_result(row) for row in result.fetchall()]

    async def increment_completed(self, run_id: str) -> None:
        async with tenant_session(tenant_id=None) as session:
            await session.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            await session.execute(
                text("UPDATE eval_runs SET completed_count = completed_count + 1 WHERE run_id = :run_id"),
                {"run_id": run_id},
            )
