"""Automated tests for 2026 RAG Evaluation Harness & Golden Benchmark Integration."""

import pytest

from src.domain.abstractions.evaluation import RegressionGateThresholds
from src.domain.evaluation.golden_dataset import GOLDEN_BENCHMARK_DATASET
from src.domain.evaluation.metrics import (
    calculate_answer_relevance,
    calculate_context_precision,
    calculate_context_recall,
    calculate_faithfulness,
)
from src.domain.evaluation.rag_eval_harness import RagEvalHarness


def test_faithfulness_grounded_vs_hallucinated():
    contexts = [
        "Retriever uses PostgreSQL Row-Level Security (RLS) on all vector tables.",
        "Database sessions bind tenant_id via tenant_session.",
    ]

    # Grounded answer
    grounded = "Retriever uses PostgreSQL Row-Level Security (RLS) on vector tables, binding tenant_id via tenant_session."
    score_grounded = calculate_faithfulness(grounded, contexts)
    assert score_grounded >= 0.85

    # Hallucinated answer
    hallucinated = "Retriever stores all vectors in unencrypted public MongoDB clusters on Mars without tenant separation."
    score_hallucinated = calculate_faithfulness(hallucinated, contexts)
    assert score_hallucinated < 0.35


def test_answer_relevance_aligned_vs_evasive():
    question = "What are the payment terms and late fees for overdue invoices?"

    # Relevant answer
    good_answer = "Payment terms are Net 30 days from invoice issuance, with a 1.5% monthly late fee for overdue balances."
    score_good = calculate_answer_relevance(question, good_answer)
    assert score_good >= 0.80

    # Evasive answer
    evasive_answer = "I do not have enough information to answer this question."
    score_evasive = calculate_answer_relevance(question, evasive_answer)
    assert score_evasive <= 0.20


def test_context_recall_complete_vs_incomplete():
    ground_truth = "Retriever guarantees 99.95% uptime SLA with a p95 query latency under 250 milliseconds."

    # Complete context containing all facts
    complete_context = [
        "The production enterprise tier guarantees 99.95% monthly uptime SLA.",
        "Hybrid search queries execute within a p95 latency budget of 250 milliseconds.",
    ]
    recall_complete = calculate_context_recall(ground_truth, complete_context)
    assert recall_complete >= 0.90

    # Incomplete context missing latency requirement
    incomplete_context = [
        "The web dashboard is styled with modern CSS modules.",
        "Celery processes async task queues.",
    ]
    recall_incomplete = calculate_context_recall(ground_truth, incomplete_context)
    assert recall_incomplete <= 0.25


def test_context_precision_ranking_sensitivity():
    ground_truth = "Payment terms are Net 30 days."

    # High precision: Relevant context at Rank 1
    ranked_top = [
        "Standard commercial invoices carry Net 30 payment terms.",
        "Some unrelated background text about coffee breaks.",
        "Another unrelated piece of text.",
    ]
    precision_top = calculate_context_precision(ranked_top, ground_truth)

    # Low precision: Relevant context at Rank 3, preceded by distractors
    ranked_bottom = [
        "Some unrelated background text about coffee breaks.",
        "Another unrelated piece of text.",
        "Standard commercial invoices carry Net 30 payment terms.",
    ]
    precision_bottom = calculate_context_precision(ranked_bottom, ground_truth)

    assert precision_top > precision_bottom
    assert precision_top == 1.0


def test_golden_benchmark_dataset_integrity():
    assert len(GOLDEN_BENCHMARK_DATASET) >= 5
    for item in GOLDEN_BENCHMARK_DATASET:
        assert item.question_id
        assert item.domain in {"security", "finance", "sla", "architecture", "ingestion"}
        assert len(item.question.strip()) > 10
        assert len(item.ground_truth_answer.strip()) > 20
        assert len(item.golden_contexts) >= 1
        assert len(item.relevant_chunk_ids) >= 1


@pytest.mark.asyncio
async def test_rag_eval_harness_golden_run_passes_gate():
    harness = RagEvalHarness()
    result = await harness.evaluate_dataset()

    assert result.total_questions == len(GOLDEN_BENCHMARK_DATASET)
    assert result.aggregate_scores.ragas.faithfulness >= 0.85
    assert result.aggregate_scores.ragas.answer_relevancy >= 0.80
    assert result.aggregate_scores.ragas.context_recall >= 0.85
    assert result.aggregate_scores.ragas.context_precision >= 0.85
    assert result.aggregate_scores.deepeval.hallucination <= 0.15

    # Check that report markdown was populated
    assert "Retriever Cognitive Regression Gate Report" in result.summary_markdown
    assert len(result.item_scores) == len(GOLDEN_BENCHMARK_DATASET)


@pytest.mark.asyncio
async def test_rag_eval_harness_blocks_hallucination_regression():
    harness = RagEvalHarness()

    # Provide intentionally hallucinated answers
    hallucinated_answers = {
        item.question_id: "We do not know, because all data was deleted and servers were shut down."
        for item in GOLDEN_BENCHMARK_DATASET
    }

    result = await harness.evaluate_dataset(
        answers_map=hallucinated_answers,
        thresholds=RegressionGateThresholds(min_faithfulness=0.90, max_hallucination=0.10),
    )

    # Must fail CI gate
    assert result.passed is False
    assert len(result.regression_report.violations) > 0
    assert "BLOCKED" in result.summary_markdown


def test_faithfulness_avoids_substring_false_grounding():
    # 'cat' is a substring of 'application', but not a valid grounded token
    answer = "We provide cat support."
    context = ["Our enterprise application architecture provides support."]
    score = calculate_faithfulness(answer, context)
    # Must not be 1.0! Only 2 of 3 tokens matched
    assert score < 0.70


def test_faithfulness_catches_short_claim_contradictions():
    # 'Status: Inactive.' directly contradicts 'Status: Active.'
    answer = "The SLA is 99.95%. Status: Inactive."
    context = ["The SLA is 99.95%. Status: Active."]
    score = calculate_faithfulness(answer, context)
    assert score < 0.85


def test_hallucination_empty_answer_is_zero():
    from src.domain.evaluation.metrics import compute_rag_scores

    _ragas, deepeval = compute_rag_scores(
        question="What is the SLA?",
        generated_answer="",
        contexts=["The SLA is 99.95%."],
        ground_truth_answer="The SLA is 99.95%.",
    )
    assert deepeval.hallucination == 0.0


def test_currency_and_percentage_literals_support():
    ground_truth = "Invoices over $1,200 incur a 1.5% fee."
    context = ["Invoices over $1,200 incur a 1.5% fee."]
    recall = calculate_context_recall(ground_truth, context)
    assert recall >= 0.95

