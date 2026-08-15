"""Unit tests for Milestone 47: Recursive Language Model (RLM) Engine & REPL Sandbox."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.adapters.sandbox.python_sandbox_adapter import (
    RestrictedPythonSandboxAdapter,
)
from src.config import settings
from src.domain.abstractions.inference import InferenceResponse, LlmProvider
from src.domain.abstractions.retrieval import (
    SearchMeta,
    SearchResponse,
    SearchResult,
)
from src.domain.retrieval.search_service import HybridSearchService
from src.domain.rlm.abstractions import RlmAnalysisRequest
from src.domain.rlm.engine import RlmExecutionEngine
from src.main import app

# ── 1. Sandbox AST Safety Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sandbox_ast_safety_blocks_imports():
    """Verify RestrictedPythonSandboxAdapter blocks illegal module imports."""
    sandbox = RestrictedPythonSandboxAdapter()

    res = await sandbox.execute_script("t1", "import os\nprint(os.getcwd())")
    assert res.is_error is True

    res2 = await sandbox.execute_script("t1", "from sys import exit\nexit(0)")
    assert res2.is_error is True


@pytest.mark.asyncio
async def test_sandbox_safe_math_execution():
    """Verify safe execution of data calculations in sandbox."""
    sandbox = RestrictedPythonSandboxAdapter()

    code = """
nums = [10, 20, 30, 40]
result = sum(nums) / len(nums)
print(f"Average: {result}")
"""
    res = await sandbox.execute_script("t1", code)
    assert res.is_error is False
    assert res.return_value == 25.0
    assert "Average: 25.0" in res.output


# ── 2. RlmExecutionEngine Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rlm_engine_analysis():
    """Verify RlmExecutionEngine workflow with search service and sandbox."""
    mock_llm = MagicMock(spec=LlmProvider)

    # 1. Code gen LLM response
    code_resp = InferenceResponse(
        content='```python\nresult = len(chunks)\nprint(f"Processed {result} chunks")\n```'
    )
    # 2. Synthesis LLM response
    synth_resp = InferenceResponse(
        content="Recursive RLM analysis synthesized 2 target chunks successfully."
    )
    mock_llm.generate = AsyncMock(side_effect=[code_resp, synth_resp])
    mock_search = MagicMock(spec=HybridSearchService)
    mock_search.search = AsyncMock(
        return_value=SearchResponse(
            results=[
                SearchResult(chunk_id="c1", document_id="d1", content="Text 1", score=0.9),
                SearchResult(chunk_id="c2", document_id="d2", content="Text 2", score=0.8),
            ],
            query="test analytical task",
            search_meta=SearchMeta(
                strategy="hybrid",
                total_candidates=2,
                returned_results=2,
                duration_ms=5.0,
            ),
        )
    )

    sandbox = RestrictedPythonSandboxAdapter()
    engine = RlmExecutionEngine(
        llm_provider=mock_llm,
        sandbox_provider=sandbox,
        search_service=mock_search,
    )

    req = RlmAnalysisRequest(
        tenant_id=str(uuid.uuid4()),
        prompt="Analyze document chunks",
    )

    result = await engine.analyze(req)
    assert "Recursive RLM analysis synthesized" in result.analysis_summary
    assert len(result.code_executions) == 1
    assert result.code_executions[0]["is_error"] is False
    assert result.code_executions[0]["result"] == "2"


# ── 3. Router Endpoint Tests ─────────────────────────────────────────────────

@patch("src.container.container.rlm_engine.analyze")
def test_rlm_analyze_endpoint(mock_analyze):
    """Verify POST /v1/tenants/{tenantId}/rlm/analyze endpoint."""
    mock_analyze.return_value = AsyncMock()
    mock_analyze.return_value = {
        "tenant_id": "t1",
        "prompt": "Test RLM prompt",
        "analysis_summary": "Synthesized RLM report",
        "code_executions": [],
        "subcalls_count": 2,
        "execution_time_ms": 25.4,
    }

    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    payload = {
        "tenant_id": tenant_id,
        "prompt": "Summarize cross-document trends",
    }

    response = client.post(
        f"/v1/tenants/{tenant_id}/rlm/analyze",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_summary"] == "Synthesized RLM report"
