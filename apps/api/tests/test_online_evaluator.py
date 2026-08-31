"""Unit tests for Milestone 50: Online Production Hallucination Tracing."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.config import EvaluationSettings, TenantConfiguration
from src.domain.evaluation.online_evaluator import (
    OnlineHallucinationEvaluator,
    calculate_context_precision,
    calculate_faithfulness,
    extract_claims,
)
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: Claim Extraction & Metric Scoring ───────────────────────────

def test_extract_claims_and_scoring():
    """Verify claim extraction and faithfulness/precision math."""
    text = "Payment gateway supports credit cards. Database Z stores user tokens."
    claims = extract_claims(text)
    assert len(claims) == 2
    assert "Payment gateway supports credit cards" in claims[0]

    contexts = [
        "Payment gateway supports credit cards and debit cards.",
        "Database Z stores user tokens securely.",
    ]
    faithfulness = calculate_faithfulness(claims, contexts)
    assert faithfulness == 1.0

    precision = calculate_context_precision("payment gateway", contexts)
    assert precision > 0.0


# ── 2. Unit Test: Evaluator Scoring & SLA Threshold Alerting ─────────────────

@pytest.mark.asyncio
async def test_online_evaluator_alert_trigger():
    """Verify OnlineHallucinationEvaluator calculates hallucination index and triggers alert on breach."""
    mock_repo = AsyncMock()
    mock_repo.save_evaluation.side_effect = lambda data: data

    evaluator = OnlineHallucinationEvaluator(repository=mock_repo)

    config = TenantConfiguration()
    config.evaluation_settings = EvaluationSettings(
        enable_online_tracing=True,
        hallucination_threshold=0.2,
    )

    query = "What database is used?"
    # Hallucinated answer with facts ungrounded in context
    answer = "We use Quantum Cloud Engine version 99 which is located on Saturn."
    contexts = ["System uses PostgreSQL 16 database."]

    res = await evaluator.evaluate_inference(
        tenant_id=str(uuid.uuid4()),
        query=query,
        answer=answer,
        contexts=contexts,
        config=config,
    )

    assert res["faithfulness"] < 1.0
    assert res["hallucination_index"] > 0.2
    assert res["is_alert"] is True
    mock_repo.save_evaluation.assert_awaited_once()


# ── 3. Unit Test: Disabled Tracing Check ──────────────────────────────────────

@pytest.mark.asyncio
async def test_online_evaluator_disabled():
    """Verify evaluator returns default payload when online tracing is disabled."""
    evaluator = OnlineHallucinationEvaluator()
    config = TenantConfiguration()
    config.evaluation_settings.enable_online_tracing = False

    res = await evaluator.evaluate_inference(
        tenant_id=str(uuid.uuid4()),
        query="test",
        answer="test",
        contexts=[],
        config=config,
    )

    assert res["status"] == "disabled"
    assert res["is_alert"] is False


# ── 4. Integration Test: Online Evaluation Admin APIs ────────────────────────

@patch("src.routers.admin.online_eval_repo.get_online_summary", new_callable=AsyncMock)
@patch("src.routers.admin.online_eval_repo.list_online_logs", new_callable=AsyncMock)
def test_admin_online_evaluation_endpoints(mock_list_logs, mock_get_summary):
    """Verify GET /v1/tenants/{tenantId}/evaluation/online/summary and /logs endpoints."""
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())
        mock_get_summary.return_value = {
            "tenant_id": tenant_id,
            "total_evaluations": 10,
            "avg_faithfulness": 0.95,
            "avg_context_precision": 0.90,
            "avg_hallucination_index": 0.05,
            "total_alerts": 1,
        }

        mock_list_logs.return_value = (
            [
                {
                    "eval_id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "query": "Sample query?",
                    "answer": "Sample answer.",
                    "faithfulness": 0.9,
                    "context_precision": 0.85,
                    "hallucination_index": 0.1,
                    "is_alert": False,
                    "created_at": "2026-08-15T08:00:00Z",
                }
            ],
            1,
        )

        headers = {"X-Admin-Master-Key": "test_admin_key"}

        # 1. Summary Endpoint Test
        res_sum = client.get(
            f"/v1/admin/tenants/{tenant_id}/evaluation/online/summary",
            headers=headers,
        )
        assert res_sum.status_code == 200
        body_sum = res_sum.json()
        assert body_sum["total_evaluations"] == 10
        assert body_sum["avg_faithfulness"] == 0.95

        # 2. Logs Endpoint Test
        res_logs = client.get(
            f"/v1/admin/tenants/{tenant_id}/evaluation/online/logs",
            headers=headers,
        )
        assert res_logs.status_code == 200
        body_logs = res_logs.json()
        assert body_logs["total"] == 1
        assert len(body_logs["items"]) == 1
        assert body_logs["items"][0]["query"] == "Sample query?"
    finally:
        app.dependency_overrides.clear()


@patch("src.routers.admin.online_eval_repo.get_online_log", new_callable=AsyncMock)
def test_admin_get_online_evaluation_log(mock_get_log):
    """Verify GET /v1/admin/tenants/{tenantId}/evaluation/online/logs/{evalId} returns claims breakdown."""
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())
        eval_id = str(uuid.uuid4())
        mock_get_log.return_value = {
            "eval_id": eval_id,
            "tenant_id": tenant_id,
            "query": "What is the token limit?",
            "answer": "The token limit is 250,000.",
            "faithfulness": 1.0,
            "context_precision": 1.0,
            "hallucination_index": 0.0,
            "is_alert": False,
            "claims": [
                {
                    "claim": "The token limit is 250,000.",
                    "premise": "Standard tier allows 250,000 monthly tokens.",
                    "status": "entailment",
                    "entailment_prob": 0.95,
                    "contradiction_prob": 0.02,
                    "neutral_prob": 0.03,
                }
            ],
            "created_at": "2026-08-31T09:00:00Z",
        }

        res = client.get(
            f"/v1/admin/tenants/{tenant_id}/evaluation/online/logs/{eval_id}",
            headers={"X-Admin-Master-Key": "test_admin_key"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["eval_id"] == eval_id
        assert len(data["claims"]) == 1
        assert data["claims"][0]["status"] == "entailment"
    finally:
        app.dependency_overrides.clear()


def test_admin_and_tenant_grounding_diff():
    """Verify on-demand claim grounding diff endpoint returns sentence breakdown."""
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())
        payload = {
            "answer": "FastAPI is our backend framework. PostgreSQL 16 is used for vectors.",
            "contexts": [
                "FastAPI is our backend framework.",
                "PostgreSQL 16 is used for vectors.",
            ],
        }

        res = client.post(
            f"/v1/admin/tenants/{tenant_id}/evaluation/grounding-diff",
            json=payload,
            headers={"X-Admin-Master-Key": "test_admin_key"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_claims"] == 2
        assert data["entailed_claims"] == 2
        assert len(data["claims"]) == 2
        assert "entailment_prob" in data["claims"][0]
    finally:
        app.dependency_overrides.clear()

