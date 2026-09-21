"""Tests for Cognitive Memory Engine DB Persistence and Multi-Tenancy."""

import pytest

from src.domain.abstractions.memory import (
    CognitiveMemoryRepositoryProtocol,
    ConsolidationRequest,
    EpisodicMemoryNode,
    MemoryType,
)
from src.domain.memory.engine import CognitiveMemoryEngine


class FakeMemoryRepository(CognitiveMemoryRepositoryProtocol):
    """In-memory implementation of CognitiveMemoryRepositoryProtocol for unit testing."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, EpisodicMemoryNode]] = {}
        self.save_count = 0
        self.delete_count = 0
        self.access_updates: list[tuple[str, str, float]] = []

    async def save_node(self, node: EpisodicMemoryNode) -> None:
        self.save_count += 1
        tenant_store = self.nodes.setdefault(node.tenant_id, {})
        tenant_store[node.id] = node

    async def get_nodes(
        self, tenant_id: str, memory_type: MemoryType | None = None
    ) -> list[EpisodicMemoryNode]:
        tenant_store = self.nodes.get(tenant_id, {})
        nodes = list(tenant_store.values())
        if memory_type:
            nodes = [n for n in nodes if n.memory_type == memory_type]
        return nodes

    async def delete_node(self, tenant_id: str, node_id: str) -> bool:
        tenant_store = self.nodes.get(tenant_id, {})
        if node_id in tenant_store:
            del tenant_store[node_id]
            self.delete_count += 1
            return True
        return False

    async def update_access(
        self,
        tenant_id: str,
        node_id: str,
        stability_score: float,
        last_accessed_at: float,
        access_count: int,
    ) -> None:
        self.access_updates.append((tenant_id, node_id, stability_score))
        tenant_store = self.nodes.get(tenant_id, {})
        if node_id in tenant_store:
            node = tenant_store[node_id]
            node.stability_score = stability_score
            node.last_accessed_at = last_accessed_at
            node.access_count = access_count


@pytest.mark.asyncio
async def test_cognitive_memory_write_through_persistence() -> None:
    repo = FakeMemoryRepository()
    engine = CognitiveMemoryEngine(repository=repo)
    tenant_id = "tenant-persist-1"

    request = ConsolidationRequest(
        tenant_id=tenant_id,
        session_id="session-101",
        query="Postgres multi-tenancy RLS vs schema separation",
        turns=[
            {
                "thought": "Evaluate PostgreSQL RLS security policies",
                "tools_called": ["schema_inspector"],
                "observation": "SET LOCAL app.current_tenant enforces strict row isolation",
            }
        ],
        success=True,
    )

    result = await engine.consolidate_trace(tenant_id, request)
    assert result.status == "consolidated"
    assert result.node_id is not None

    # Verify write-through persistence into repository
    persisted = await repo.get_nodes(tenant_id)
    assert len(persisted) == 1
    assert persisted[0].id == result.node_id
    assert persisted[0].query == request.query
    assert repo.save_count == 1


@pytest.mark.asyncio
async def test_cognitive_memory_hydration_from_repo() -> None:
    repo = FakeMemoryRepository()
    tenant_id = "tenant-hydrate-2"

    # Pre-seed repo with existing memory node
    seeded_node = EpisodicMemoryNode(
        id="mem-seeded-001",
        tenant_id=tenant_id,
        memory_type=MemoryType.SEMANTIC,
        query="Enterprise contract terms and SLA guarantees",
        distilled_insight="High-availability SLA requires 99.99% uptime with failover replication",
        tool_chain=["policy_lookup"],
        success=True,
        importance_score=0.9,
    )
    await repo.save_node(seeded_node)

    # Fresh engine with empty in-memory state
    fresh_engine = CognitiveMemoryEngine(repository=repo)

    # List memories - should hydrate from repository
    memories = await fresh_engine.list_memories(tenant_id=tenant_id)
    assert len(memories) == 1
    assert memories[0].id == "mem-seeded-001"
    assert "SLA" in memories[0].distilled_insight

    # Retrieve guidance hit
    guidance = await fresh_engine.retrieve_guidance(
        tenant_id=tenant_id,
        query="SLA guarantees uptime",
        min_similarity=0.1,
    )
    assert len(guidance.relevant_nodes) >= 1
    assert guidance.relevant_nodes[0].node.id == "mem-seeded-001"


@pytest.mark.asyncio
async def test_cognitive_memory_delete_persists() -> None:
    repo = FakeMemoryRepository()
    engine = CognitiveMemoryEngine(repository=repo)
    tenant_id = "tenant-del-3"

    request = ConsolidationRequest(
        tenant_id=tenant_id,
        session_id="session-102",
        query="Temporary debugging session",
        turns=[
            {
                "thought": "Testing pool size",
                "tools_called": ["load_tester"],
                "observation": "Success",
            }
        ],
        success=True,
    )
    result = await engine.consolidate_trace(tenant_id, request)

    nodes_before = await repo.get_nodes(tenant_id)
    assert len(nodes_before) == 1

    # Delete memory
    deleted = await engine.delete_memory(tenant_id=tenant_id, node_id=result.node_id)
    assert deleted is True

    nodes_after = await repo.get_nodes(tenant_id)
    assert len(nodes_after) == 0
    assert repo.delete_count == 1
