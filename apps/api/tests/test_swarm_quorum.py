"""Comprehensive Unit & Integration Test Suite for Multi-Agent Swarm Quorum Engine (M109)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.abstractions.agent_swarm import (
    AgentBallot,
    CandidateClaim,
    DebateStance,
    DebateTurn,
    QuorumConsensusResult,
    SwarmAgentRole,
    SwarmDebateEvent,
    SwarmDebateRequest,
)
from src.domain.agentic.swarm.engine import MultiAgentSwarmQuorumEngine
from src.domain.memory.engine import CognitiveMemoryEngine
from src.main import app


@pytest.fixture
def memory_engine() -> CognitiveMemoryEngine:
    return CognitiveMemoryEngine(vector_dim=64)


@pytest.fixture
def swarm_engine(memory_engine: CognitiveMemoryEngine) -> MultiAgentSwarmQuorumEngine:
    return MultiAgentSwarmQuorumEngine(memory_engine=memory_engine)


@pytest.mark.asyncio
async def test_swarm_domain_model_contracts():
    """Verify domain model instantiation, default values, and schema constraints."""
    claim = CandidateClaim(
        claim_id="clm_test_1",
        agent_role=SwarmAgentRole.PLANNER,
        statement="System must partition workloads across 3 nodes.",
        evidence_basis=["Architecture invariant 1"],
        confidence_score=0.91,
    )
    assert claim.claim_id == "clm_test_1"
    assert claim.is_verified is True
    assert claim.agent_role == SwarmAgentRole.PLANNER

    turn = DebateTurn(
        turn_index=0,
        round_index=1,
        agent_role=SwarmAgentRole.PLANNER,
        stance=DebateStance.PROPOSAL,
        content="Strategic proposal outline",
        claims_proposed=[claim],
        confidence_score=0.90,
    )
    assert turn.turn_index == 0
    assert turn.stance == DebateStance.PROPOSAL
    assert len(turn.claims_proposed) == 1

    ballot = AgentBallot(
        agent_role=SwarmAgentRole.FORENSIC_AUDITOR,
        candidate_id="res_alpha",
        confidence=0.95,
        rationale="Evidence validated",
        weight=1.4,
    )
    assert ballot.weight == 1.4
    assert ballot.confidence == 0.95


@pytest.mark.asyncio
async def test_topology_graph_construction(swarm_engine: MultiAgentSwarmQuorumEngine):
    """Verify directed networkx debate DAG connections and role presence."""
    roles = [
        SwarmAgentRole.PLANNER,
        SwarmAgentRole.FORENSIC_AUDITOR,
        SwarmAgentRole.CODE_SYNTHESIZER,
        SwarmAgentRole.SKEPTIC_CRITIC,
    ]
    graph = swarm_engine.build_topology_graph(roles)

    assert len(graph.nodes) == 4
    for r in roles:
        assert r.value in graph.nodes

    # Verify key dialectic edges
    assert graph.has_edge(SwarmAgentRole.PLANNER.value, SwarmAgentRole.SKEPTIC_CRITIC.value)
    assert graph.has_edge(SwarmAgentRole.SKEPTIC_CRITIC.value, SwarmAgentRole.CODE_SYNTHESIZER.value)
    assert graph.has_edge(SwarmAgentRole.CODE_SYNTHESIZER.value, SwarmAgentRole.FORENSIC_AUDITOR.value)
    assert graph.has_edge(SwarmAgentRole.FORENSIC_AUDITOR.value, SwarmAgentRole.PLANNER.value)


@pytest.mark.asyncio
async def test_execute_swarm_debate_full_cycle(swarm_engine: MultiAgentSwarmQuorumEngine):
    """Verify full 3-round dialectic debate execution and quorum consensus."""
    request = SwarmDebateRequest(
        tenant_id="tenant_alpha",
        prompt="Design a zero-downtime vector index re-indexing pipeline under 10k QPS load",
        quorum_threshold=0.70,
        max_rounds=3,
    )
    result = await swarm_engine.execute_debate(request)

    assert isinstance(result, QuorumConsensusResult)
    assert result.tenant_id == "tenant_alpha"
    assert result.rounds_completed == 3
    assert len(result.rounds) == 3
    assert result.quorum_reached is True
    assert result.consensus_confidence >= 0.70
    assert len(result.candidate_resolutions) == 2

    # Verify winning candidate
    assert result.winning_consensus != ""
    assert result.winning_resolution_id.startswith("res_")

    # Verify rounds metadata
    r1 = result.rounds[0]
    assert r1.round_index == 1
    assert len(r1.turns) == 4  # All 4 agents participated

    r2 = result.rounds[1]
    assert r2.round_index == 2
    assert len(r2.turns) == 4  # All 4 agents cross-examined

    r3 = result.rounds[2]
    assert r3.round_index == 3
    assert len(r3.turns) == 4  # Rebuttal turns


@pytest.mark.asyncio
async def test_hallucination_pruning(swarm_engine: MultiAgentSwarmQuorumEngine):
    """Verify that unverified or extreme assertions are audited and quarantined."""
    request = SwarmDebateRequest(
        tenant_id="tenant_audit_test",
        prompt="Validate sub-50ms distributed transactions across planetary nodes",
        quorum_threshold=0.75,
    )
    result = await swarm_engine.execute_debate(request)

    # Forensic auditor should have audited and pruned ungrounded claims
    assert len(result.hallucinations_pruned) >= 1
    for pruned in result.hallucinations_pruned:
        assert pruned.is_verified is False
        assert pruned.rejection_reason is not None
        assert "Forensic Audit" in pruned.rejection_reason


@pytest.mark.asyncio
async def test_operational_telemetry_tracking(swarm_engine: MultiAgentSwarmQuorumEngine):
    """Verify aggregate debate telemetry metrics are properly tracked and calculated."""
    tenant = "tenant_telemetry"
    initial_stats = await swarm_engine.get_stats(tenant)
    assert initial_stats.total_debates == 0

    req = SwarmDebateRequest(
        tenant_id=tenant,
        prompt="Evaluate cryptographic token exchange security",
    )
    await swarm_engine.execute_debate(req)

    stats = await swarm_engine.get_stats(tenant)
    assert stats.total_debates == 1
    assert stats.quorum_success_rate == 1.0
    assert stats.avg_debate_rounds == 3.0
    assert stats.active_agent_count == 4


@pytest.mark.asyncio
async def test_stream_swarm_debate_events(swarm_engine: MultiAgentSwarmQuorumEngine):
    """Verify Server-Sent Events sequence emission during real-time streaming."""
    request = SwarmDebateRequest(
        tenant_id="tenant_stream",
        prompt="Synthesize multi-cloud database failover topology",
    )
    events: list[SwarmDebateEvent] = []
    async for event in swarm_engine.stream_debate(request):
        events.append(event)

    event_types = [e.event_type for e in events]
    assert "debate_start" in event_types
    assert "round_start" in event_types
    assert "agent_turn" in event_types
    assert "peer_critique" in event_types
    assert "ballot_cast" in event_types
    assert "consensus_reached" in event_types
    assert event_types[-1] == "consensus_reached"


@pytest.mark.asyncio
async def test_api_endpoints_integration():
    """Verify FastAPI route handlers for debate execution, streaming, roles, and stats."""
    from src.config import settings

    transport = ASGITransport(app=app)
    headers = {
        "X-Admin-Master-Key": settings.ADMIN_MASTER_KEY,
        "Content-Type": "application/json",
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get Roles
        roles_res = await client.get("/v1/tenants/test_tenant/agentic/swarm/roles", headers=headers)
        assert roles_res.status_code == 200
        roles_data = roles_res.json()
        assert len(roles_data) == 4
        role_names = [r["role"] for r in roles_data]
        assert "planner" in role_names
        assert "forensic_auditor" in role_names
        assert "code_synthesizer" in role_names
        assert "skeptic_critic" in role_names

        # 2. Execute Debate
        debate_payload = {
            "tenant_id": "test_tenant",
            "prompt": "Evaluate AES-256 vs ChaCha20-Poly1305 for hardware enclave encryption",
            "quorum_threshold": 0.70,
            "max_rounds": 3,
        }
        debate_res = await client.post(
            "/v1/tenants/test_tenant/agentic/swarm/debate",
            json=debate_payload,
            headers=headers,
        )
        assert debate_res.status_code == 200
        debate_data = debate_res.json()
        assert debate_data["quorum_reached"] is True
        assert debate_data["consensus_confidence"] >= 0.70
        assert len(debate_data["rounds"]) == 3
        assert len(debate_data["candidate_resolutions"]) == 2

        # 3. Stream Debate
        stream_res = await client.post(
            "/v1/tenants/test_tenant/agentic/swarm/debate/stream",
            json=debate_payload,
            headers=headers,
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers.get("content-type", "")
        text = stream_res.text
        assert "data: " in text
        assert "[DONE]" in text

        # 4. Get Stats
        stats_res = await client.get("/v1/tenants/test_tenant/agentic/swarm/stats", headers=headers)
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert stats_data["total_debates"] >= 1
        assert stats_data["active_agent_count"] == 4
