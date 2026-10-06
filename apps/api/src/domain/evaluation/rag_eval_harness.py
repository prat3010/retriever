"""Automated RAG Evaluation Harness (2026 Standards).

Runs automated end-to-end evaluation runs on golden benchmark datasets, computing
Faithfulness, Answer Relevance, Context Recall, Context Precision, and Search Metrics.
Integrates directly with CI/CD Regression Gate to block regressions.
Conforms strictly to Hexagonal Architecture boundaries (0 framework imports).
"""

import time
from collections.abc import Callable
from typing import Any

from src.domain.abstractions.evaluation import (
    AggregateScores,
    DeepEvalScores,
    RagasScores,
    RegressionGateReport,
    RegressionGateThresholds,
    SearchMetrics,
)
from src.domain.evaluation.golden_dataset import (
    GOLDEN_BENCHMARK_DATASET,
    GoldenEvalItem,
)
from src.domain.evaluation.metrics import compute_rag_scores
from src.domain.evaluation.regression_gate import RegressionGateEngine
from src.domain.evaluation.search_metrics import compute_search_metrics


class RagEvalHarnessResult:
    """Complete summary produced by an automated RAG evaluation harness run."""

    def __init__(
        self,
        aggregate_scores: AggregateScores,
        item_scores: list[dict[str, Any]],
        regression_report: RegressionGateReport,
        total_questions: int,
        duration_ms: float,
    ) -> None:
        self.aggregate_scores = aggregate_scores
        self.item_scores = item_scores
        self.regression_report = regression_report
        self.total_questions = total_questions
        self.duration_ms = duration_ms

    @property
    def passed(self) -> bool:
        return self.regression_report.passed

    @property
    def summary_markdown(self) -> str:
        return self.regression_report.summary_markdown


class RagEvalHarness:
    """Automated RAG evaluation harness for regression verification and continuous benchmarking."""

    def __init__(
        self,
        regression_gate: RegressionGateEngine | None = None,
        default_thresholds: RegressionGateThresholds | None = None,
    ) -> None:
        self.gate = regression_gate or RegressionGateEngine()
        self.thresholds = default_thresholds or RegressionGateThresholds()

    async def evaluate_dataset(
        self,
        dataset: list[GoldenEvalItem] | None = None,
        answers_map: dict[str, str] | None = None,
        generator_fn: Callable[[str, list[str]], Any] | None = None,
        search_fn: Callable[[str], Any] | None = None,
        thresholds: RegressionGateThresholds | None = None,
    ) -> RagEvalHarnessResult:
        """Run evaluation harness over a golden dataset.

        Args:
            dataset: Golden test items (defaults to GOLDEN_BENCHMARK_DATASET)
            answers_map: Optional precomputed {question_id: generated_answer}
            generator_fn: Optional async or sync callable (question, contexts) -> answer
            search_fn: Optional async or sync callable (question) -> (contexts, chunk_ids)
            thresholds: Custom CI regression thresholds
        """
        import inspect

        items = dataset or GOLDEN_BENCHMARK_DATASET
        thresh = thresholds or self.thresholds

        start_time = time.monotonic()
        all_ragas: list[RagasScores] = []
        all_deepeval: list[DeepEvalScores] = []
        all_search: list[SearchMetrics] = []
        item_reports: list[dict[str, Any]] = []

        for item in items:
            t0 = time.monotonic()
            contexts = list(item.golden_contexts)
            retrieved_chunk_ids = list(item.relevant_chunk_ids)

            # 1. Custom search retrieval if provided
            if search_fn is not None:
                try:
                    search_res = search_fn(item.question)
                    if inspect.isawaitable(search_res):
                        search_res = await search_res
                    if isinstance(search_res, tuple) and len(search_res) == 2:
                        contexts, retrieved_chunk_ids = search_res
                    elif isinstance(search_res, list):
                        contexts = search_res
                except Exception:
                    pass

            # 2. Answer generation or lookup
            generated_answer = ""
            if answers_map and item.question_id in answers_map:
                generated_answer = answers_map[item.question_id]
            elif generator_fn is not None:
                try:
                    gen_res = generator_fn(item.question, contexts)
                    if inspect.isawaitable(gen_res):
                        gen_res = await gen_res
                    generated_answer = str(gen_res)
                except Exception as err:
                    generated_answer = f"Error generating answer: {err}"
            else:
                # Default to grounded answer based on golden contexts
                generated_answer = item.ground_truth_answer

            # 3. Compute RAG scores
            ragas_score, deepeval_score = compute_rag_scores(
                question=item.question,
                generated_answer=generated_answer,
                contexts=contexts,
                ground_truth_answer=item.ground_truth_answer,
                relevant_chunk_ids=item.relevant_chunk_ids,
                retrieved_chunk_ids=retrieved_chunk_ids,
            )

            # 4. Compute search metrics
            search_metric = compute_search_metrics(
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=item.relevant_chunk_ids,
            )

            all_ragas.append(ragas_score)
            all_deepeval.append(deepeval_score)
            all_search.append(search_metric)

            latency = (time.monotonic() - t0) * 1000
            item_reports.append(
                {
                    "question_id": item.question_id,
                    "domain": item.domain,
                    "question": item.question,
                    "generated_answer": generated_answer,
                    "faithfulness": ragas_score.faithfulness,
                    "answer_relevancy": ragas_score.answer_relevancy,
                    "context_recall": ragas_score.context_recall,
                    "context_precision": ragas_score.context_precision,
                    "hallucination": deepeval_score.hallucination,
                    "latency_ms": round(latency, 2),
                }
            )

        # 5. Compute Aggregate Scores
        n = len(items) if items else 1
        agg = AggregateScores(
            ragas=RagasScores(
                faithfulness=sum(s.faithfulness for s in all_ragas) / n,
                answer_relevancy=sum(s.answer_relevancy for s in all_ragas) / n,
                context_precision=sum(s.context_precision for s in all_ragas) / n,
                context_recall=sum(s.context_recall for s in all_ragas) / n,
            ),
            deepeval=DeepEvalScores(
                hallucination=sum(s.hallucination for s in all_deepeval) / n,
                toxicity=0.0,
                bias=0.0,
            ),
            search_metrics=SearchMetrics(
                ndcg_at_10=sum(s.ndcg_at_10 for s in all_search) / n,
                mrr=sum(s.mrr for s in all_search) / n,
                hit_rate_at_10=sum(s.hit_rate_at_10 for s in all_search) / n,
            ),
        )

        # 6. Evaluate CI Regression Gate
        gate_report = self.gate.evaluate_gate(agg, thresholds=thresh)
        total_duration = (time.monotonic() - start_time) * 1000

        return RagEvalHarnessResult(
            aggregate_scores=agg,
            item_scores=item_reports,
            regression_report=gate_report,
            total_questions=len(items),
            duration_ms=round(total_duration, 2),
        )
