import time

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
    ) -> None:
        self.dataset_repo = eval_dataset_repo
        self.run_repo = eval_run_repo
        self.search_service = search_service
        self.orchestrator = inference_orchestrator

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

            try:
                search_query = SearchQuery(
                    query=question.question,
                    tenant_id=tenant_id,
                    top_k=10,
                    enable_hybrid=True,
                    enable_reranking=True,
                    enable_self_query=False,
                    enable_web_search=False,
                )
                search_response = await self.search_service.search(search_query)
                retrieved_chunks = search_response.results
                context_chunks = [r.content for r in retrieved_chunks]
                retrieved_chunk_ids = [r.chunk_id for r in retrieved_chunks]
            except Exception:
                retrieved_chunks = []
                context_chunks = []
                retrieved_chunk_ids = []

            try:
                response = await self.orchestrator.generate(
                    tenant_id=tenant_id,
                    session_id=f"__eval__{question.question_id}",
                    query=question.question,
                    context_chunks=retrieved_chunks,
                    tenant_config=None,
                    system_prompt_name="default",
                )
                generated_answer = response.content
            except Exception:
                generated_answer = ""

            search_metrics = compute_search_metrics(
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=question.relevant_chunk_ids,
            )

            ragas_scores = RagasScores()
            deepeval_scores = DeepEvalScores()

            if generated_answer:
                try:
                    from src.adapters.cognitive.ragas_evaluator import (
                        compute_ragas_scores,
                    )
                    ragas_scores = await compute_ragas_scores(
                        question=question.question,
                        answer=generated_answer,
                        contexts=context_chunks,
                        ground_truth=question.ground_truth_answer,
                    )
                except Exception:
                    pass

                try:
                    from src.adapters.cognitive.deepeval_evaluator import (
                        compute_deepeval_scores,
                    )
                    deepeval_scores = await compute_deepeval_scores(
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
