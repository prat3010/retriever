"""Comprehensive unit and integration test suite for Platform Battery #38: GoT Planner & Hierarchical Memory."""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.cognitive.got_planner_adapter import (
    GoTPlannerAdapter,
    compute_ebbinghaus_retention,
    score_thought_heuristics,
)
from src.domain.abstractions.got_planner import (
    DistillationRequest,
    GoTAggregateRequest,
    GoTPlanRequest,
    GoTSimulateRequest,
    GoTStepRequest,
    GoTThoughtType,
    MemoryLayer,
)
from src.domain.batteries.battery_service import BatteryService
from src.main import app

client = TestClient(app)


def test_battery_38_registration() -> None:
    """Verify Platform Battery #38 (hierarchical_memory_got_planner) is active in BatteryService."""
    service = BatteryService()
    resp = service.get_platform_batteries()
    battery_ids = [b.id for b in resp.batteries]

    assert "hierarchical_memory_got_planner" in battery_ids
    b38 = service.get_battery("hierarchical_memory_got_planner")
    assert b38 is not None
    assert b38.category.value == "computation_graph"
    assert b38.status.value == "active"
    assert "M123" in b38.milestone
    assert "Graph-of-Thoughts" in b38.algorithm_foundation


def test_hexagonal_architecture_conformance() -> None:
    """Verify that got_planner domain abstraction contains no forbidden framework imports."""
    domain_file = Path("apps/api/src/domain/abstractions/got_planner.py")
    assert domain_file.exists()

    tree = ast.parse(domain_file.read_text(encoding="utf-8"))
    forbidden_prefixes = ("fastapi", "sqlalchemy", "torch", "scipy", "src.adapters", "src.routers")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert not name.name.startswith(forbidden_prefixes), (
                    f"Forbidden import '{name.name}' in domain abstraction!"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith(forbidden_prefixes), (
                f"Forbidden from-import '{node.module}' in domain abstraction!"
            )


def test_ebbinghaus_retention_mathematics() -> None:
    """Verify exponential retention decay R(t) = exp(-dt / S)."""
    now = 1000000.0

    # 1. At creation time (dt = 0): retention must be 1.0
    ret_0 = compute_ebbinghaus_retention(created_at=now, stability_days=5.0, current_time=now)
    assert ret_0 == 1.0

    # 2. At dt = 5 days with stability S = 5 days: R = exp(-1) ≈ 0.3679
    five_days_sec = 5 * 86400.0
    ret_5d = compute_ebbinghaus_retention(created_at=now, stability_days=5.0, current_time=now + five_days_sec)
    assert pytest.approx(ret_5d, rel=1e-2) == 0.3679

    # 3. Very old memory with stability 1 day
    ret_old = compute_ebbinghaus_retention(created_at=now, stability_days=1.0, current_time=now + (30 * 86400.0))
    assert ret_old < 0.001


def test_thought_scoring_heuristics() -> None:
    """Verify composite scoring combines grounding, coherence, and constraint alignment."""
    query = "Optimize distributed vector sharding latency in Raft cluster"
    good_content = (
        "Partitioning Strategy: Horizontally partition dense vectors across sovereign nodes "
        "using consistent hashing, reducing latency and optimizing distributed cluster retrieval. "
        "Consequently, memory throughput scales linearly."
    )
    poor_content = "Random unrelated text without any keywords."

    score_good, g1, c1, s1 = score_thought_heuristics(query, good_content)
    score_poor, g2, c2, s2 = score_thought_heuristics(query, poor_content)

    assert score_good > score_poor
    assert g1 > g2
    assert s1 > s2
    assert 0.0 <= score_good <= 1.0
    assert 0.0 <= score_poor <= 1.0


@pytest.mark.asyncio
async def test_got_dag_lifecycle_and_acyclicity() -> None:
    """Test full GoT graph creation, branching, aggregation, and acyclicity."""
    adapter = GoTPlannerAdapter()
    req = GoTPlanRequest(query="Decouple vector search from prompt synthesis in sovereign mesh", branching_factor=3)
    graph = await adapter.create_plan("tn_test_got", req)

    assert graph.graph_id.startswith("got_plan_")
    assert graph.root_id in graph.nodes
    assert len(graph.nodes) == 1
    assert graph.nodes[graph.root_id].thought_type == GoTThoughtType.ROOT

    # Step 1: Generate 3 branches
    step_gen = GoTStepRequest(action="generate", target_node_ids=[graph.root_id], parameters={"branching_factor": 3})
    graph_gen = await adapter.step_plan("tn_test_got", graph.graph_id, step_gen)
    assert len(graph_gen.nodes) == 4
    assert len(graph_gen.edges) == 3

    children = graph_gen.nodes[graph_gen.root_id].child_ids
    assert len(children) == 3

    # Step 2: Multi-in-degree aggregation
    agg_req = GoTAggregateRequest(source_node_ids=[children[0], children[1]])
    graph_agg = await adapter.aggregate_thoughts("tn_test_got", graph.graph_id, agg_req)

    assert len(graph_agg.nodes) == 5
    # Find aggregation node
    agg_nodes = [n for n in graph_agg.nodes.values() if n.thought_type == GoTThoughtType.AGGREGATION]
    assert len(agg_nodes) == 1
    agg_node = agg_nodes[0]
    assert len(agg_node.parent_ids) == 2
    assert children[0] in agg_node.parent_ids
    assert children[1] in agg_node.parent_ids

    # Verify optimal path
    assert len(graph_agg.optimal_path) >= 2
    assert graph_agg.root_id == graph_agg.optimal_path[0]


@pytest.mark.asyncio
async def test_autonomous_execution_and_hierarchical_memory() -> None:
    """Verify autonomous execution converges and populates L1 and L2 memories."""
    adapter = GoTPlannerAdapter()
    req = GoTPlanRequest(query="Deploy zero-trust micro-enclave with Kyber post-quantum attestation")
    graph = await adapter.create_plan("tn_quantum", req)

    # Autonomous execution
    converged_graph = await adapter.execute_plan("tn_quantum", graph.graph_id)
    assert converged_graph.is_converged is True
    assert len(converged_graph.optimal_path) >= 3

    # Check hierarchical memory
    mem_view = await adapter.get_hierarchical_memory("tn_quantum")
    assert len(mem_view.l1_scratchpad) >= 1
    assert len(mem_view.l2_episodic) >= 1
    assert mem_view.total_nodes >= 2
    assert mem_view.average_retention > 0.5

    # Distill into L3 Semantic memory
    distill_req = DistillationRequest(graph_id=converged_graph.graph_id, target_layer=MemoryLayer.L3_SEMANTIC)
    distill_res = await adapter.distill_graph("tn_quantum", distill_req)
    assert distill_res.status == "distilled"
    assert distill_res.layer == MemoryLayer.L3_SEMANTIC

    # Re-check hierarchical memory: L3 must now have a node
    mem_view_after = await adapter.get_hierarchical_memory("tn_quantum")
    assert len(mem_view_after.l3_semantic) >= 1


def test_simulation_engine_mathematical_precision() -> None:
    """Verify deterministic simulation endpoint produces valid DAG and statistics."""
    adapter = GoTPlannerAdapter()
    sim_req = GoTSimulateRequest(
        query="Benchmark sublinear BM25 against dense HNSW vector projection",
        branching_factor=3,
        aggregation_fanin=2,
        pruning_threshold=0.40,
    )
    sim_res = adapter.simulate(sim_req)

    assert sim_res.nodes_count >= 4
    assert sim_res.edges_count >= 3
    assert sim_res.aggregations_count >= 1
    assert sim_res.best_score > 0.5
    assert len(sim_res.optimal_path_ids) >= 3
    assert sim_res.tokens_consumed > 0
    assert sim_res.estimated_latency_ms > 0.0
    assert sim_res.hierarchical_memory.total_nodes == 3


def test_fastapi_rest_endpoints() -> None:
    """Verify full suite of FastAPI REST endpoints for GoT Planning."""
    # 1. Health check
    health_resp = client.get("/v1/got/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["battery_id"] == "hierarchical_memory_got_planner"
    assert health_data["battery_number"] == 38

    # 2. Public simulation
    sim_resp = client.post(
        "/v1/got/simulate",
        json={
            "query": "Synthesize distributed consensus and vector replication topologies",
            "branching_factor": 3,
            "aggregation_fanin": 2,
            "pruning_threshold": 0.42,
        },
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["nodes_count"] >= 4
    assert len(sim_data["optimal_path_ids"]) >= 3

    # 3. Create plan session
    tenant_id = "tn_rest_test_m123"
    headers = {"X-Admin-Key": "test-admin-key"}
    create_resp = client.post(
        f"/v1/tenants/{tenant_id}/got/plans",
        headers=headers,
        json={
            "query": "Implement Raft scatter-gather parallel search across 8 shards",
            "branching_factor": 3,
        },
    )
    assert create_resp.status_code == 201
    plan_data = create_resp.json()
    graph_id = plan_data["graph"]["graph_id"]
    assert graph_id.startswith("got_plan_")

    # 4. Get plan DAG
    get_resp = client.get(f"/v1/tenants/{tenant_id}/got/plans/{graph_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["graph_id"] == graph_id

    # 5. Autonomous execute plan
    exec_resp = client.post(f"/v1/tenants/{tenant_id}/got/plans/{graph_id}/execute", headers=headers)
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["is_converged"] is True

    # 6. Memory hierarchy
    mem_resp = client.get(f"/v1/tenants/{tenant_id}/got/memory/hierarchy", headers=headers)
    assert mem_resp.status_code == 200
    mem_data = mem_resp.json()
    assert mem_data["total_nodes"] >= 2

    # 7. Distill graph
    distill_resp = client.post(
        f"/v1/tenants/{tenant_id}/got/memory/distill",
        headers=headers,
        json={"graph_id": graph_id, "target_layer": "l3_semantic"},
    )
    assert distill_resp.status_code == 200
    assert distill_resp.json()["status"] == "distilled"
