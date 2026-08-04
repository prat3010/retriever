import time
from typing import Any

from src.domain.abstractions.evaluation import (
    AggregateScores,
    DeepEvalScores,
    EvalDatasetRepository,
    EvalRun,
    EvalRunRepository,
    EvalRunResult,
    EvalRunResultScores,
    RagasScores,
)
from src.domain.abstractions.retrieval import (
    SearchQuery,
)
from src.domain.evaluation.search_metrics import compute_search_metrics
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.retrieval.search_service import HybridSearchService


class EvalRunService:

    def __init__(
        self,
        eval_dataset_repo: EvalDatasetRepository,
        eval_run_repo: EvalRunRepository,
        search_service: HybridSearchService,
        inference_orchestrator: InferenceOrchestrator,
        ragas_fn: Any | None = None,
        deepeval_fn: Any | None = None,
    ) -> None:
        self.dataset_repo = eval_dataset_repo
        self.run_repo = eval_run_repo
        self.search_service = search_service
        self.orchestrator = inference_orchestrator
        self.ragas_fn = ragas_fn
        self.deepeval_fn = deepeval_fn

    async def run_evaluation(self, tenant_id: str, dataset_id: str, trigger: str = "manual") -> EvalRun:
        run = await self.run_repo.create_run(EvalRun(
            tenant_id=tenant_id,
            dataset_id=dataset_id,
            trigger=trigger,
        ))

        await self.run_repo.update_run_status(run.run_id, "running")

        questions = await self.dataset_repo.list_questions(dataset_id)
        await self.run_repo.update_run_status(run.run_id, "running")

        all_scores: list[EvalRunResultScores] = []

        for question in questions:
            start = time.monotonic()

            search_result = await self.search_service.search(
                tenant_id,
                SearchQuery(
                    query_text=question.question,
                    top_k=5,
                ),
            )

            retrieved_chunk_ids = [r.chunk_id for r in search_result.results]
            context_chunks = [r.content for r in search_result.results if r.content]

            generated_answer: str | None = None
            try:
                result = await self.orchestrator.execute_rag(
                    query=question.question,
                    tenant_id=tenant_id,
                )
                generated_answer = result.answer
            except Exception:
                pass

            search_metrics = compute_search_metrics(
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=question.relevant_chunk_ids,
            )

            ragas_scores = RagasScores()
            deepeval_scores = DeepEvalScores()

            if generated_answer:
                if self.ragas_fn is not None:
                    try:
                        ragas_scores = await self.ragas_fn(
                            question=question.question,
                            answer=generated_answer,
                            contexts=context_chunks,
                            ground_truth=question.ground_truth_answer,
                        )
                    except Exception:
                        pass

                if self.deepeval_fn is not None:
                    try:
                        deepeval_scores = await self.deepeval_fn(
                            question=question.question,
                            answer=generated_answer,
                            contexts=context_chunks,
                        )
                    except Exception:
                        pass

            elapsed = int((time.monotonic() - start) * 1000)

            result = EvalRunResult(
                run_id=run.run_id,
                question_id=question.question_id,
                generated_answer=generated_answer,
                retrieved_chunk_ids=retrieved_chunk_ids,
                scores=EvalRunResultScores(
                    ragas=ragas_scores,
                    deepeval=deepeval_scores,
                    search_metrics=search_metrics,
                ),
                latency_ms=elapsed,
            )
            await self.run_repo.add_result(result)
            await self.run_repo.increment_completed(run.run_id)
            all_scores.append(result.scores)

        aggregate = self._compute_aggregate(all_scores)
        await self.run_repo.update_run_status(run.run_id, "completed", aggregate_scores=aggregate.model_dump())

        run.status = "completed"
        run.aggregate_scores = AggregateScores(**aggregate.model_dump())
        run.completed_count = len(all_scores)
        return run

    def _compute_aggregate(self, scores: list[EvalRunResultScores]) -> AggregateScores:
        if not scores:
            return AggregateScores()

        n = len(scores)
        agg = AggregateScores()

        agg.ragas.faithfulness = sum(s.ragas.faithfulness for s in scores) / n
        agg.ragas.answer_relevancy = sum(s.ragas.answer_relevancy for s in scores) / n
        agg.ragas.context_precision = sum(s.ragas.context_precision for s in scores) / n
        agg.ragas.context_recall = sum(s.ragas.context_recall for s in scores) / n

        agg.deepeval.hallucination = sum(s.deepeval.hallucination for s in scores) / n
        agg.deepeval.toxicity = sum(s.deepeval.toxicity for s in scores) / n
        agg.deepeval.bias = sum(s.deepeval.bias for s in scores) / n

        agg.search_metrics.ndcg_at_10 = sum(s.search_metrics.ndcg_at_10 for s in scores) / n
        agg.search_metrics.mrr = sum(s.search_metrics.mrr for s in scores) / n
        agg.search_metrics.hit_rate_at_10 = sum(s.search_metrics.hit_rate_at_10 for s in scores) / n

        return agg
