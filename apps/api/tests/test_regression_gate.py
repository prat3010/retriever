"""Unit and API tests for Milestone 77: Automated CI/CD Regression Gate Engine."""

from fastapi.testclient import TestClient

from src.config import settings
from src.domain.abstractions.evaluation import (
    AggregateScores,
    DeepEvalScores,
    RagasScores,
    RegressionGateThresholds,
)
from src.domain.evaluation.regression_gate import RegressionGateEngine
from src.main import app

client = TestClient(app)


# ── 1. Unit Tests: Regression Gate Engine ────────────────────────────────────

def test_regression_gate_pass():
    """Verify gate passes when all quality metrics meet or exceed thresholds."""
    engine = RegressionGateEngine()
    scores = AggregateScores(
        ragas=RagasScores(
            faithfulness=0.96,
            context_precision=0.91,
            answer_relevancy=0.92,
        ),
        deepeval=DeepEvalScores(
            hallucination=0.03,
        ),
    )

    report = engine.evaluate_gate(scores)
    assert report.passed is True
    assert len(report.violations) == 0
    assert "PASSED" in report.summary_markdown
    assert "✅ PASS" in report.summary_markdown


def test_regression_gate_fail_faithfulness():
    """Verify gate fails when faithfulness drops below threshold."""
    engine = RegressionGateEngine()
    scores = AggregateScores(
        ragas=RagasScores(
            faithfulness=0.82,  # Below 0.90
            context_precision=0.90,
            answer_relevancy=0.88,
        ),
        deepeval=DeepEvalScores(
            hallucination=0.04,
        ),
    )

    report = engine.evaluate_gate(scores)
    assert report.passed is False
    assert len(report.violations) == 1
    assert "Faithfulness score (0.820) is below required minimum" in report.violations[0]
    assert "BLOCKED" in report.summary_markdown
    assert "❌ VIOLATION" in report.summary_markdown


def test_regression_gate_fail_hallucination():
    """Verify gate fails when hallucination exceeds 0.10 limit."""
    engine = RegressionGateEngine()
    scores = AggregateScores(
        ragas=RagasScores(
            faithfulness=0.92,
            context_precision=0.88,
            answer_relevancy=0.89,
        ),
        deepeval=DeepEvalScores(
            hallucination=0.18,  # Exceeds 0.10
        ),
    )

    report = engine.evaluate_gate(scores)
    assert report.passed is False
    assert len(report.violations) == 1
    assert "Hallucination Index (0.180) exceeds maximum allowable" in report.violations[0]


def test_regression_gate_custom_thresholds():
    """Verify gate respects custom strict thresholds."""
    engine = RegressionGateEngine()
    scores = AggregateScores(
        ragas=RagasScores(
            faithfulness=0.92,
            context_precision=0.88,
            answer_relevancy=0.89,
        ),
        deepeval=DeepEvalScores(
            hallucination=0.05,
        ),
    )

    custom_thresh = RegressionGateThresholds(
        min_faithfulness=0.98,  # Very strict
    )

    report = engine.evaluate_gate(scores, thresholds=custom_thresh)
    assert report.passed is False
    assert any("Faithfulness score" in v for v in report.violations)


# ── 2. API Tests: Admin Regression Gate Endpoint ─────────────────────────────

def test_admin_regression_gate_endpoint():
    """Verify POST /v1/admin/tenants/{tenantId}/eval/regression-gate endpoint."""
    response = client.post(
        "/v1/admin/tenants/00000000-0000-0000-0000-000000000000/eval/regression-gate",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={
            "faithfulness": 0.94,
            "context_precision": 0.89,
            "answer_relevancy": 0.91,
            "hallucination": 0.04,
            "thresholds": {
                "min_faithfulness": 0.90,
                "max_hallucination": 0.10,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert len(data["violations"]) == 0
    assert "## 🛡️ Retriever Cognitive Regression Gate Report" in data["summary_markdown"]
