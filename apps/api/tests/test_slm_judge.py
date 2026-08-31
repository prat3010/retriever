"""Unit tests for Milestone 74: Tier 2 Structured SLM-as-a-Judge Engine & Admin APIs."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.domain.evaluation.slm_judge import SlmJudgeEngine
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: SLM Judge LLM JSON Parsing ─────────────────────────────────

@pytest.mark.asyncio
async def test_slm_judge_llm_json_parsing():
    """Verify SlmJudgeEngine parses structured JSON output from model correctly."""
    judge = SlmJudgeEngine()

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = """
    ```json
    {
      "verdict": "PASS",
      "faithfulness_score": 0.95,
      "reasoning": "All claims are strictly verified against context chunks.",
      "claim_analyses": [
        {
          "claim": "The API uses Bearer tokens.",
          "status": "supported",
          "evidence_span": "Authentication requires Bearer JWT in request headers.",
          "confidence": 0.98,
          "rationale": "Direct textual grounding."
        }
      ]
    }
    ```
    """

    res = await judge.judge_response(
        query="How is the API secured?",
        answer="The API uses Bearer tokens.",
        contexts=["Authentication requires Bearer JWT in request headers."],
        llm_provider=mock_llm,
    )

    assert res.verdict == "PASS"
    assert res.faithfulness_score == 0.95
    assert len(res.claim_analyses) == 1
    assert res.claim_analyses[0].status == "supported"
    assert res.claim_analyses[0].evidence_span == "Authentication requires Bearer JWT in request headers."


# ── 2. Unit Test: Structural Fallback Judge ───────────────────────────────────

@pytest.mark.asyncio
async def test_slm_judge_structural_fallback():
    """Verify SlmJudgeEngine generates deterministic structural verdict without live LLM."""
    judge = SlmJudgeEngine()

    res = await judge.judge_response(
        query="What database is used?",
        answer="Retriever uses PostgreSQL with pgvector for vector search.",
        contexts=["Retriever uses PostgreSQL with pgvector for vector search."],
    )

    assert res.verdict == "PASS"
    assert res.faithfulness_score >= 0.80
    assert len(res.claim_analyses) >= 1
    assert res.claim_analyses[0].status == "supported"


@pytest.mark.asyncio
async def test_slm_judge_fail_on_contradiction():
    """Verify SlmJudgeEngine fails verdict when contradiction is present."""
    judge = SlmJudgeEngine()

    res = await judge.judge_response(
        query="Does it support refunds?",
        answer="The system does not support any payment refunds.",
        contexts=["The system supports full payment refunds within 30 days."],
    )

    assert res.verdict == "FAIL"
    assert any(a.status == "contradicted" for a in res.claim_analyses)


# ── 3. API Tests: Admin Evaluation Endpoints ─────────────────────────────────

def test_admin_nli_endpoint():
    """Verify POST /v1/admin/eval/nli endpoint."""
    response = client.post(
        "/v1/admin/eval/nli",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={
            "claims": [
                "FastAPI is used for REST endpoints.",
                "The database is MongoDB.",
            ],
            "contexts": [
                "FastAPI is used for high speed REST endpoints on PostgreSQL.",
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_claims"] == 2
    assert data["entailed_claims"] == 1
    assert data["neutral_claims"] == 1
    assert data["faithfulness_score"] == 0.50
    assert len(data["classifications"]) == 2


def test_admin_slm_judge_endpoint():
    """Verify POST /v1/admin/eval/slm-judge endpoint."""
    response = client.post(
        "/v1/admin/eval/slm-judge",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={
            "query": "What is the token expiration?",
            "answer": "API tokens expire in 90 days.",
            "contexts": [
                "Security policy dictates that API tokens expire in 90 days.",
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "PASS"
    assert data["faithfulness_score"] >= 0.80
    assert len(data["claim_analyses"]) >= 1
