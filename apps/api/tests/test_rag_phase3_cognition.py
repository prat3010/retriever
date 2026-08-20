"""Unit tests for Phase 3 SOTA RAG Modernization (Autonomous Cognition & RLM)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.evaluation.online_evaluator import OnlineEvaluator, QualityMetrics
from src.domain.graph.graph_extraction_service import GraphExtractionService
from src.domain.rlm.engine import RlmAnalysisRequest, RlmExecutionEngine


@pytest.mark.asyncio
async def test_rlm_multi_turn_repl_loop():
    """Verify RlmExecutionEngine executes multi-turn REPL code loops."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(side_effect=[
        MagicMock(content="```python\nresult = sum(c.score for c in chunks)\n```"),
    ])

    mock_sandbox = MagicMock()
    mock_sandbox.execute_script = AsyncMock(return_value=MagicMock(
        output="Score computed",
        return_value=4.5,
        is_error=False,
        error_message=None,
        execution_time_ms=12.5,
    ))

    mock_search = MagicMock()
    mock_search.search = AsyncMock(return_value=MagicMock(
        results=[
            MagicMock(content="Chunk 1", document_id="doc1", score=0.9, metadata={}),
            MagicMock(content="Chunk 2", document_id="doc2", score=0.8, metadata={}),
        ]
    ))

    engine = RlmExecutionEngine(
        llm_provider=mock_llm,
        sandbox_provider=mock_sandbox,
        search_service=mock_search,
    )

    request = RlmAnalysisRequest(tenant_id="tenant_123", prompt="Calculate average chunk score")
    res = await engine.analyze_repl_loop(request, max_turns=3)

    assert "Multi-turn REPL loop completed" in res.analysis_summary
    assert len(res.code_executions) == 1
    assert res.code_executions[0]["result"] == "4.5"


def test_graph_extraction_triples_synthesis():
    """Verify GraphExtractionService extracts subject-predicate-object triples."""
    service = GraphExtractionService()
    text = "PostgreSQL is a relational database. Retriever implements SOTA RAG architecture."

    triples = service.extract_triples(text, chunk_id="chk_001")

    assert len(triples) >= 1
    assert triples[0].subject.lower() in ["postgresql", "retriever"]
    formatted = service.format_triples_for_graph_store("tenant_123", "doc_1", "chk_001", triples)
    assert len(formatted) == len(triples)
    assert formatted[0]["tenant_id"] == "tenant_123"


def test_online_evaluator_and_auto_tuning():
    """Verify OnlineEvaluator computes quality metrics and auto-tunes retrieval settings."""
    evaluator = OnlineEvaluator()

    metrics = evaluator.evaluate_response(
        retrieved_chunks=["c1", "c2", "c3"],
        cited_chunks=["c1"],
        response_length=150,
        feedback_score=1.0,
    )

    assert metrics.context_precision == pytest.approx(0.3333, abs=1e-3)
    assert metrics.faithfulness == 0.5

    # Test auto-tuning with low precision trend
    tuned = evaluator.auto_tune_retrieval(
        recent_metrics=[metrics, QualityMetrics(context_precision=0.2, answer_relevance=0.5, faithfulness=0.4)],
        current_settings={"top_k": 7, "rerank_threshold": 0.3},
    )

    assert tuned.top_k < 7  # Low precision triggers top_k reduction
    assert tuned.rerank_threshold > 0.3  # Low faithfulness triggers rerank threshold elevation
