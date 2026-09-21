"""Tests for Graph-of-Thoughts (GoT) Dynamic Planning & Repository Persistence."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cognitive.got_planner_adapter import GoTPlannerAdapter
from src.domain.abstractions.got_planner import (
    GoTAggregateRequest,
    GoTGraph,
    GoTPlanRequest,
    GoTRepositoryProtocol,
    GoTStepRequest,
    GoTThoughtNode,
)


class FakeGoTRepository(GoTRepositoryProtocol):
    """In-memory implementation of GoTRepositoryProtocol for testing."""

    def __init__(self) -> None:
        self.graphs: dict[str, GoTGraph] = {}
        self.thoughts: dict[str, list[GoTThoughtNode]] = {}
        self.save_graph_count = 0
        self.save_thought_count = 0

    async def save_graph(self, graph: GoTGraph) -> None:
        self.save_graph_count += 1
        self.graphs[graph.graph_id] = graph

    async def get_graph(self, tenant_id: str, graph_id: str) -> GoTGraph | None:
        graph = self.graphs.get(graph_id)
        if graph and graph.tenant_id == tenant_id:
            return graph
        return None

    async def save_thought(self, thought: GoTThoughtNode) -> None:
        self.save_thought_count += 1
        tenant_thoughts = self.thoughts.setdefault(thought.tenant_id, [])
        for idx, t in enumerate(tenant_thoughts):
            if t.id == thought.id:
                tenant_thoughts[idx] = thought
                return
        tenant_thoughts.append(thought)

    async def get_thoughts(self, tenant_id: str, graph_id: str) -> list[GoTThoughtNode]:
        tenant_thoughts = self.thoughts.get(tenant_id, [])
        return [t for t in tenant_thoughts if t.metadata.get("graph_id") == graph_id]


@pytest.mark.asyncio
async def test_got_plan_creation_and_persistence() -> None:
    repo = FakeGoTRepository()
    planner = GoTPlannerAdapter(repository=repo)
    tenant_id = "tenant-got-1"

    req = GoTPlanRequest(
        query="Design zero-downtime database migration strategy for PostgreSQL",
        branching_factor=3,
    )

    graph = await planner.create_plan(tenant_id, req)
    assert graph.tenant_id == tenant_id
    assert graph.graph_id is not None
    assert len(graph.nodes) >= 1

    # Verify saved in repo
    persisted_graph = await repo.get_graph(tenant_id, graph.graph_id)
    assert persisted_graph is not None
    assert persisted_graph.query == req.query
    assert repo.save_graph_count >= 1
    assert repo.save_thought_count >= 1


@pytest.mark.asyncio
async def test_got_dynamic_llm_generation() -> None:
    repo = FakeGoTRepository()
    mock_llm = MagicMock()

    # Configure mock LLM to return structured JSON response
    dynamic_payload = [
        {"title": "Dual-write", "description": "Dual-write with shadow replication"},
        {"title": "BlueGreen", "description": "Blue/green logical decoding slots"},
    ]
    mock_response = MagicMock()
    mock_response.content = json.dumps(dynamic_payload)
    mock_llm.generate = AsyncMock(return_value=mock_response)

    planner = GoTPlannerAdapter(repository=repo, llm_provider=mock_llm)
    tenant_id = "tenant-got-2"

    req = GoTPlanRequest(
        query="How to migrate large PostgreSQL table without locks?",
        branching_factor=2,
    )

    graph = await planner.create_plan(tenant_id, req)
    assert len(graph.nodes) == 1

    # Step plan to generate dynamic thoughts
    step_req = GoTStepRequest(action="generate", parameters={"branching_factor": 2})
    stepped = await planner.step_plan(tenant_id, graph.graph_id, step_req)

    assert len(stepped.nodes) >= 3
    assert mock_llm.generate.called
    contents = [n.content for n in stepped.nodes.values()]
    assert any("Dual-write" in c for c in contents)


@pytest.mark.asyncio
async def test_got_step_expansion_and_topological_sort() -> None:
    repo = FakeGoTRepository()
    planner = GoTPlannerAdapter(repository=repo)
    tenant_id = "tenant-got-3"

    # Create plan
    plan_req = GoTPlanRequest(query="Optimize RAG vector recall")
    graph = await planner.create_plan(tenant_id, plan_req)
    initial_count = len(graph.nodes)

    # Step expansion
    step_req = GoTStepRequest(action="generate", parameters={"branching_factor": 2})
    stepped_graph = await planner.step_plan(tenant_id, graph.graph_id, step_req)

    assert stepped_graph.graph_id == graph.graph_id
    assert len(stepped_graph.nodes) > initial_count
    # Check that DP computed an optimal path
    assert len(stepped_graph.optimal_path) >= 1
    assert stepped_graph.optimal_path[0] == stepped_graph.root_id
    assert stepped_graph.best_score > 0.0


@pytest.mark.asyncio
async def test_got_thought_aggregation_fan_in() -> None:
    repo = FakeGoTRepository()
    planner = GoTPlannerAdapter(repository=repo)
    tenant_id = "tenant-got-4"

    plan_req = GoTPlanRequest(query="Multi-strategy search ranking")
    graph = await planner.create_plan(tenant_id, plan_req)

    # Step plan to generate multiple candidates
    step_req = GoTStepRequest(action="generate", parameters={"branching_factor": 2})
    stepped = await planner.step_plan(tenant_id, graph.graph_id, step_req)

    # Pick at least two child node IDs to aggregate
    node_ids = [nid for nid in stepped.nodes.keys() if nid != stepped.root_id][:2]
    assert len(node_ids) >= 2
    count_before_agg = len(stepped.nodes)

    agg_req = GoTAggregateRequest(
        source_node_ids=node_ids,
        synthesis_prompt="Synthesize dense HNSW and keyword BM25 into reciprocal rank fusion",
    )

    agg_graph = await planner.aggregate_thoughts(tenant_id, graph.graph_id, agg_req)
    assert len(agg_graph.nodes) > count_before_agg
    assert repo.save_thought_count >= len(agg_graph.nodes)
