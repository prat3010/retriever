"""Unit tests for Milestone 48: Multi-Agent Consensus & Critic Reflection Loops."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.domain.abstractions.inference import InferenceResponse, LlmProvider
from src.domain.abstractions.retrieval import SearchMeta, SearchResponse, SearchResult
from src.domain.consensus.abstractions import ConsensusRequest
from src.domain.consensus.reflection_loop import MultiAgentConsensusEngine
from src.domain.retrieval.search_service import HybridSearchService
from src.main import app

# ── 1. Consensus Reflection Loop Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_consensus_reflection_loop_success():
    """Verify Generator vs Critic reflection loop revises draft and approves."""
    mock_llm = MagicMock(spec=LlmProvider)

    # Round 1: Gen draft 1, Critic rejects with feedback
    gen_resp_1 = InferenceResponse(content="Draft 1: The policy covers all water leaks.")
    critic_resp_1 = InferenceResponse(
        content='{"is_approved": false, "critique_score": 0.5, "critique_feedback": "Missing 48h reporting requirement.", "unsupported_claims": ["all water leaks"]}'
    )

    # Round 2: Gen draft 2, Critic approves
    gen_resp_2 = InferenceResponse(content="Draft 2: Policy covers leaks reported within 48h.")
    critic_resp_2 = InferenceResponse(
        content='{"is_approved": true, "critique_score": 1.0, "critique_feedback": "Approved", "unsupported_claims": []}'
    )

    mock_llm.generate = AsyncMock(
        side_effect=[gen_resp_1, critic_resp_1, gen_resp_2, critic_resp_2]
    )

    mock_search = MagicMock(spec=HybridSearchService)
    mock_search.search = AsyncMock(
        return_value=SearchResponse(
            results=[
                SearchResult(
                    chunk_id="c1",
                    document_id="d1",
                    content="Section 4.2: Water leaks are covered if reported within 48 hours.",
                    score=0.95,
                )
            ],
            query="water leaks policy",
            search_meta=SearchMeta(
                strategy="hybrid",
                total_candidates=1,
                returned_results=1,
                duration_ms=4.0,
            ),
        )
    )

    engine = MultiAgentConsensusEngine(
        default_llm=mock_llm,
        search_service=mock_search,
    )

    req = ConsensusRequest(
        tenant_id=str(uuid.uuid4()),
        prompt="Does policy cover water leaks?",
        max_reflection_rounds=3,
    )

    result = await engine.execute_consensus(req)

    assert "within 48h" in result.final_response
    assert result.approved_on_round == 2
    assert len(result.reflection_history) == 2


@pytest.mark.asyncio
async def test_consensus_dual_provider_switching():
    """Verify dual-provider AI model switching between Generator and Critic."""
    mock_gen_llm = MagicMock(spec=LlmProvider)
    mock_gen_llm.generate = AsyncMock(
        return_value=InferenceResponse(content="Generator Draft Answer")
    )

    mock_critic_llm = MagicMock(spec=LlmProvider)
    mock_critic_llm.generate = AsyncMock(
        return_value=InferenceResponse(
            content='{"is_approved": true, "critique_score": 1.0, "critique_feedback": "Approved", "unsupported_claims": []}'
        )
    )

    mock_search = MagicMock(spec=HybridSearchService)
    mock_search.search = AsyncMock(
        return_value=SearchResponse(
            results=[],
            query="test",
            search_meta=SearchMeta(
                strategy="hybrid",
                total_candidates=0,
                returned_results=0,
                duration_ms=1.0,
            ),
        )
    )

    provider_registry = {
        "provider_gen": mock_gen_llm,
        "provider_critic": mock_critic_llm,
    }

    engine = MultiAgentConsensusEngine(
        default_llm=mock_gen_llm,
        search_service=mock_search,
        provider_registry=provider_registry,
    )

    req = ConsensusRequest(
        tenant_id=str(uuid.uuid4()),
        prompt="Dual provider test",
        generator_provider_name="provider_gen",
        critic_provider_name="provider_critic",
    )

    result = await engine.execute_consensus(req)

    assert result.generator_used == "provider_gen"
    assert result.critic_used == "provider_critic"
    assert result.final_response == "Generator Draft Answer"


# ── 2. Router Endpoint Tests ─────────────────────────────────────────────────

@patch("src.container.container.consensus_engine.execute_consensus")
def test_consensus_endpoint(mock_execute):
    """Verify POST /v1/tenants/{tenantId}/consensus/generate endpoint."""
    mock_execute.return_value = AsyncMock()
    mock_execute.return_value = {
        "tenant_id": "t1",
        "prompt": "Test prompt",
        "final_response": "Audited final answer",
        "generator_used": "default_llm",
        "critic_used": "default_llm",
        "approved_on_round": 1,
        "reflection_history": [],
        "execution_time_ms": 15.2,
    }

    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    payload = {
        "tenant_id": tenant_id,
        "prompt": "Factual audit question",
    }

    response = client.post(
        f"/v1/tenants/{tenant_id}/consensus/generate",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["final_response"] == "Audited final answer"
