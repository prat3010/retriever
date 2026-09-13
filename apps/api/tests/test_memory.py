"""Comprehensive Unit & Integration Test Suite for Cognitive Agent Memory (M108)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.abstractions.memory import (
    ConsolidationRequest,
    ConsolidationResult,
    DistilledGuidance,
    EpisodicMemoryNode,
    MemoryStats,
    MemoryType,
)
from src.domain.memory.engine import CognitiveMemoryEngine
from src.main import app


@pytest.fixture
def memory_engine() -> CognitiveMemoryEngine:
    return CognitiveMemoryEngine(vector_dim=64)


@pytest.mark.asyncio
async def test_domain_model_contracts():
    """Verify domain model instantiations and default attributes."""
    node = EpisodicMemoryNode(
        id="mem_test_1",
        tenant_id="tenant_alpha",
        memory_type=MemoryType.EPISODIC,
        query="Compute Q3 revenue margin",
        distilled_insight="Executed calculator with financial percentages.",
        tool_chain=["calculator"],
        success=True,
    )
    assert node.id == "mem_test_1"
    assert node.stability_score == 1.0
    assert node.access_count == 0
    assert node.memory_type == MemoryType.EPISODIC
    assert node.importance_score == 0.5


@pytest.mark.asyncio
async def test_trace_consolidation_episodic(memory_engine: CognitiveMemoryEngine):
    """Test consolidating a standard multi-turn ReAct trace into episodic memory."""
    req = ConsolidationRequest(
        tenant_id="tenant_alpha",
        session_id="session_101",
        query="Calculate pricing discount for enterprise tier",
        turns=[
            {
                "step_index": 0,
                "thought": "Need to search pricing rules",
                "tools_called": ["retriever_search_hybrid"],
                "observation": "Enterprise tier gets 20% discount on annual plan.",
            },
            {
                "step_index": 1,
                "thought": "Now compute discounted rate",
                "tools_called": ["calculator"],
                "observation": "Final price: $80,000",
            },
        ],
        final_answer="The discounted enterprise pricing is $80,000/year.",
        success=True,
    )

    res: ConsolidationResult = await memory_engine.consolidate_trace("tenant_alpha", req)
    assert res.node_id.startswith("mem_")
    assert res.memory_type == MemoryType.EPISODIC
    assert res.importance_score >= 0.70
    assert "retriever_search_hybrid" in res.tool_chain
    assert "calculator" in res.tool_chain

    # Verify stored node
    nodes = await memory_engine.list_memories("tenant_alpha")
    assert len(nodes) == 1
    assert nodes[0].id == res.node_id
    assert nodes[0].turns_count == 2


@pytest.mark.asyncio
async def test_trace_consolidation_procedural_self_healing(memory_engine: CognitiveMemoryEngine):
    """Test that self-healing traces with errors consolidate into procedural recovery rules."""
    req = ConsolidationRequest(
        tenant_id="tenant_alpha",
        session_id="session_102",
        query="Execute Python REPL script to process sales telemetry",
        turns=[
            {
                "step_index": 0,
                "thought": "Run Python script",
                "tools_called": ["rlm_execute"],
                "observation": "Error: NameError: name 'pandas' is not defined",
            },
            {
                "step_index": 1,
                "thought": "Self-heal: import csv standard library instead of pandas",
                "tools_called": ["rlm_execute"],
                "observation": "Successfully parsed 1,420 records.",
            },
        ],
        final_answer="Parsed 1,420 sales records using standard csv module.",
        success=True,
    )

    res = await memory_engine.consolidate_trace("tenant_alpha", req)
    assert res.memory_type == MemoryType.PROCEDURAL
    assert res.importance_score >= 0.80
    assert "self-healed" in res.distilled_insight.lower()


@pytest.mark.asyncio
async def test_experience_distillation_and_stability_reinforcement(memory_engine: CognitiveMemoryEngine):
    """Test experience retrieval, guidance prompt synthesis, and Ebbinghaus stability boost."""
    req = ConsolidationRequest(
        tenant_id="tenant_alpha",
        query="Diagnose slow vector search query latency",
        turns=[
            {
                "step_index": 0,
                "tools_called": ["system_metrics", "hybrid_search"],
                "observation": "HNSW index ef_search was too high (ef=256).",
            }
        ],
        final_answer="Reduced ef_search to 64 to drop latency to 12ms.",
        success=True,
    )
    await memory_engine.consolidate_trace("tenant_alpha", req)

    # First retrieval: query matches keywords
    guidance: DistilledGuidance = await memory_engine.retrieve_guidance(
        tenant_id="tenant_alpha",
        query="Vector search query latency diagnosis and indexing",
        min_similarity=0.40,
    )
    assert len(guidance.relevant_nodes) >= 1
    assert "DISTILLED EXPERIENCE FROM PRIOR SESSIONS" in guidance.guidance_prompt
    assert "system_metrics" in guidance.guidance_prompt

    # Verify stability reinforcement: initial stability 1.0 -> reinforced: 1.0 * 1.5 + 0.5 = 2.0
    nodes = await memory_engine.list_memories("tenant_alpha")
    node = nodes[0]
    assert node.access_count == 2  # initial 1 on creation + 1 on retrieval
    assert node.stability_score >= 1.9


@pytest.mark.asyncio
async def test_multi_tenancy_isolation(memory_engine: CognitiveMemoryEngine):
    """Verify strict multi-tenant partition: Tenant A memories cannot be seen by Tenant B."""
    await memory_engine.consolidate_trace(
        "tenant_alpha",
        ConsolidationRequest(
            tenant_id="tenant_alpha",
            query="Confidential Alpha patent roadmap",
            turns=[{"tools_called": ["document_reader"], "observation": "Patent A1."}],
            success=True,
        ),
    )

    # Query as Tenant Beta
    beta_guidance = await memory_engine.retrieve_guidance("tenant_beta", "Confidential Alpha patent roadmap")
    assert len(beta_guidance.relevant_nodes) == 0

    beta_nodes = await memory_engine.list_memories("tenant_beta")
    assert len(beta_nodes) == 0

    alpha_nodes = await memory_engine.list_memories("tenant_alpha")
    assert len(alpha_nodes) == 1


@pytest.mark.asyncio
async def test_ebbinghaus_pruning_and_deletion(memory_engine: CognitiveMemoryEngine):
    """Test manual node deletion and automated Ebbinghaus retention decay pruning."""
    res = await memory_engine.consolidate_trace(
        "tenant_alpha",
        ConsolidationRequest(
            tenant_id="tenant_alpha",
            query="Stale temporary observation",
            turns=[{"tools_called": ["calculator"], "observation": "1+1=2"}],
            success=True,
        ),
    )
    node_id = res.node_id

    # Simulate decay by artificially shifting last_accessed_at into the past (e.g. 30 days ago)
    store = memory_engine._get_tenant_store("tenant_alpha")
    store[node_id].last_accessed_at = store[node_id].last_accessed_at - (30 * 86400)

    # Prune with retention threshold 0.15 (decay exp(-30/1) ≈ 9.3e-14 < 0.15)
    pruned_count = await memory_engine.prune_memories("tenant_alpha", min_retention=0.15)
    assert pruned_count == 1

    remaining = await memory_engine.list_memories("tenant_alpha")
    assert len(remaining) == 0

    # Test delete non-existent
    deleted = await memory_engine.delete_memory("tenant_alpha", "non_existent")
    assert deleted is False


@pytest.mark.asyncio
async def test_memory_stats_aggregation(memory_engine: CognitiveMemoryEngine):
    """Test tenant memory metrics reporting."""
    await memory_engine.consolidate_trace(
        "tenant_alpha",
        ConsolidationRequest(
            tenant_id="tenant_alpha",
            query="Query 1",
            turns=[{"tools_called": ["calculator"], "observation": "ok"}],
            success=True,
        ),
    )
    await memory_engine.consolidate_trace(
        "tenant_alpha",
        ConsolidationRequest(
            tenant_id="tenant_alpha",
            query="Graph triple inspection",
            turns=[{"tools_called": ["graph_query"], "observation": "graph linked"}],
            success=True,
        ),
    )

    stats: MemoryStats = await memory_engine.get_stats("tenant_alpha")
    assert stats.total_memories == 2
    assert stats.episodic_count >= 1
    assert stats.semantic_count >= 1
    assert stats.avg_stability >= 1.0


@pytest.mark.asyncio
async def test_fastapi_memory_router():
    """Verify HTTP API endpoints for Cognitive Memory."""
    from src.config import settings

    headers = {
        "X-Admin-Master-Key": settings.ADMIN_MASTER_KEY,
        "Content-Type": "application/json",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Consolidate a trace
        cons_res = await client.post(
            "/v1/tenants/tn_test_mem/memory/consolidate",
            headers=headers,
            json={
                "tenant_id": "tn_test_mem",
                "session_id": "sess_api_1",
                "query": "Optimize database index for high concurrency",
                "turns": [
                    {
                        "step_index": 0,
                        "tools_called": ["hybrid_search"],
                        "observation": "Postgres HNSW index optimized with m=32 ef_construction=128",
                    }
                ],
                "final_answer": "Postgres HNSW index configured with m=32.",
                "success": True,
            },
        )
        assert cons_res.status_code == 201
        data = cons_res.json()
        assert "node_id" in data
        node_id = data["node_id"]

        # 2. Query stats (verify /memory and /agentic/memory dual routes)
        stats_res = await client.get("/v1/tenants/tn_test_mem/memory/stats", headers=headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_memories"] >= 1

        agentic_stats_res = await client.get("/v1/tenants/tn_test_mem/agentic/memory/stats", headers=headers)
        assert agentic_stats_res.status_code == 200
        assert agentic_stats_res.json()["total_memories"] == stats["total_memories"]

        # 3. List nodes
        list_res = await client.get("/v1/tenants/tn_test_mem/memory/nodes", headers=headers)
        assert list_res.status_code == 200
        nodes = list_res.json()
        assert any(n["id"] == node_id for n in nodes)

        agentic_list_res = await client.get("/v1/tenants/tn_test_mem/agentic/memory/nodes", headers=headers)
        assert agentic_list_res.status_code == 200
        assert len(agentic_list_res.json()) == len(nodes)

        # 4. Retrieve guidance
        guidance_res = await client.post(
            "/v1/tenants/tn_test_mem/agentic/memory/guidance",
            headers=headers,
            json={"query": "Database index optimization for Postgres", "min_similarity": 0.40},
        )
        assert guidance_res.status_code == 200
        guidance = guidance_res.json()
        assert len(guidance["relevant_nodes"]) >= 1

        # 5. Delete node via /agentic/memory alias
        del_res = await client.delete(f"/v1/tenants/tn_test_mem/agentic/memory/nodes/{node_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True
