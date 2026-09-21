"""Tests for Swarm Quorum Debate Engine dynamic LLM generation and fallback."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.abstractions.agent_swarm import (
    SwarmAgentRole,
    SwarmDebateRequest,
)
from src.domain.agentic.swarm.engine import MultiAgentSwarmQuorumEngine


@pytest.mark.asyncio
async def test_swarm_debate_dynamic_llm() -> None:
    mock_llm = MagicMock()

    # Response for opening round
    opening_json = {
        "content": "Dynamic LLM Argument: Partitioning improves scan efficiency by 10x.",
        "confidence_score": 0.95,
        "claims": [
            {
                "statement": "Partitioning reduces index scan tree depth",
                "evidence_basis": ["PostgreSQL documentation chapter 5.11"],
                "confidence_score": 0.95,
            }
        ],
    }
    # Response for critique round
    critique_json = {
        "critique": "Dynamic LLM Critique: While partitioning helps, query routing overhead must be budgeted.",
        "confidence_score": 0.88,
        "pruned_claim_statements": [],
        "prune_rationale": "Partitioning benefits hold but require connection pool routing.",
    }

    mock_resp_1 = MagicMock()
    mock_resp_1.content = json.dumps(opening_json)
    mock_resp_2 = MagicMock()
    mock_resp_2.content = json.dumps(critique_json)

    mock_llm.generate = AsyncMock(side_effect=[mock_resp_1, mock_resp_1, mock_resp_2, mock_resp_2, mock_resp_2, mock_resp_2])

    engine = MultiAgentSwarmQuorumEngine(llm_provider=mock_llm)
    tenant_id = "tenant-swarm-1"

    req = SwarmDebateRequest(
        tenant_id=tenant_id,
        prompt="Design high-throughput multi-tenant indexing architecture in PostgreSQL",
        active_roles=[
            SwarmAgentRole.PLANNER,
            SwarmAgentRole.FORENSIC_AUDITOR,
        ],
        max_rounds=2,
        quorum_threshold=0.6,
    )

    result = await engine.execute_debate(req)
    assert result.tenant_id == tenant_id
    assert len(result.rounds) >= 1
    assert mock_llm.generate.called

    # Verify that dynamic content is present in debate turns
    all_turns = [turn for r in result.rounds for turn in r.turns]
    turn_texts = [t.content for t in all_turns]
    assert any("Dynamic LLM" in text for text in turn_texts)


@pytest.mark.asyncio
async def test_swarm_debate_fallback_without_llm() -> None:
    # No LLM provided - must execute deterministic templates without failing
    engine = MultiAgentSwarmQuorumEngine(llm_provider=None)
    tenant_id = "tenant-swarm-2"

    req = SwarmDebateRequest(
        tenant_id=tenant_id,
        prompt="Evaluate HNSW vector index for approximate nearest neighbors",
        active_roles=[
            SwarmAgentRole.PLANNER,
            SwarmAgentRole.SKEPTIC_CRITIC,
        ],
        max_rounds=1,
    )

    result = await engine.execute_debate(req)
    assert result.tenant_id == tenant_id
    assert len(result.rounds) >= 1
    assert result.winning_consensus != ""
