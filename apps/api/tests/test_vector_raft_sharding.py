"""Tests for Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus (M117).

Verifies:
- Consistent virtual-node hash partitioning across 64 vnodes.
- Raft consensus state machine, term advancement, and leader election.
- Vector index mutations replicated via Raft log requiring majority quorum.
- Parallel scatter-gather vector search with score fusion and tunable read quorums.
- Online zero-downtime shard rebalancing and migration.
- Platform Battery #32 registration in BatteryService.
- FastAPI REST endpoints in apps/api/src/routers/vector_sharding.py.
"""

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.exceptions import (
    RaftQuorumNotReachedError,
    ShardNotFoundError,
    ShardRebalanceConflictError,
)
from src.domain.abstractions.vector_sharding import (
    RaftRole,
    ReadQuorum,
    ScatterGatherQuery,
    ShardMutationRequest,
    ShardStatus,
    WriteQuorum,
)
from src.domain.batteries.battery_service import (
    BatteryCategory,
    BatteryService,
    BatteryStatus,
)
from src.domain.retrieval.vector_raft_sharding_service import VectorRaftShardingService
from src.main import app


@pytest.fixture
def sharding_service() -> VectorRaftShardingService:
    """Provide a fresh VectorRaftShardingService instance for testing."""
    return VectorRaftShardingService(
        cluster_id="test_cluster",
        num_shards=8,
        vnodes_per_shard=64,
        replication_factor=3,
    )


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient for API router testing."""
    return TestClient(app)


def test_battery_32_registration():
    """Verify Battery #32 (vector_raft_sharding) is registered in BatteryService."""
    service = BatteryService()
    batteries = service.get_platform_batteries().batteries
    battery_map = {b.id: b for b in batteries}

    assert "vector_raft_sharding" in battery_map
    b32 = battery_map["vector_raft_sharding"]
    assert b32.name == "Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus"
    assert b32.category == BatteryCategory.EDGE_DISTRIBUTION
    assert b32.status == BatteryStatus.ACTIVE
    assert b32.milestone == "M117 (v1.7.0-alpha1)"
    assert b32.health_check_endpoint == "/v1/shards/topology"
    assert b32.active_parameters["total_shards"] == 8
    assert b32.active_parameters["replication_factor"] == 3
    assert b32.active_parameters["vnodes_per_shard"] == 64


def test_consistent_hashing_topology(sharding_service: VectorRaftShardingService):
    """Verify consistent hashing ring and shard partition initialization."""
    shards = sharding_service.list_shards()
    assert len(shards) == 8
    assert len(sharding_service._vnode_ring) == 8 * 64

    # Shard hash boundaries should cover full 32-bit integer range
    assert shards[0].hash_range_start == 0
    assert shards[-1].hash_range_end == 4294967295

    # Deterministic mapping for keys
    s1 = sharding_service.get_shard_for_key("tenant_acme", "doc_001")
    s2 = sharding_service.get_shard_for_key("tenant_acme", "doc_001")
    assert s1.shard_id == s2.shard_id

    # Different doc keys can map to different or same valid shards
    s3 = sharding_service.get_shard_for_key("tenant_acme", "doc_999")
    assert s3.shard_id in [s.shard_id for s in shards]


def test_raft_leader_election(sharding_service: VectorRaftShardingService):
    """Verify Raft leader election, terms, and node state transitions."""
    status = sharding_service.get_raft_status()
    assert status.total_nodes == 3
    assert status.current_term == 1
    assert status.active_leader_id == "node_core_01"
    assert status.leader_elected is True
    assert status.quorum_healthy is True

    # Trigger election for node_core_02
    success = sharding_service.trigger_election("node_core_02")
    assert success is True
    assert sharding_service.current_term == 2
    assert sharding_service.active_leader_id == "node_core_02"

    new_status = sharding_service.get_raft_status()
    assert new_status.active_leader_id == "node_core_02"
    assert new_status.nodes[1].role == RaftRole.LEADER
    assert new_status.nodes[0].role == RaftRole.FOLLOWER

    # Invalid node candidate should raise error
    with pytest.raises(ShardNotFoundError):
        sharding_service.trigger_election("invalid_node_99")


@pytest.mark.asyncio
async def test_vector_mutation_and_replication(sharding_service: VectorRaftShardingService):
    """Verify vector index mutations are committed through the Raft consensus log."""
    vectors = [
        {"chunk_id": "chunk_1", "vector": [0.1, 0.2, 0.3], "text": "Doc 1 text", "metadata": {"tag": "alpha"}},
        {"chunk_id": "chunk_2", "vector": [0.4, 0.5, 0.6], "text": "Doc 2 text", "metadata": {"tag": "beta"}},
    ]
    req = ShardMutationRequest(
        tenant_id="tenant_acme",
        document_id="doc_101",
        vectors=vectors,
        write_quorum=WriteQuorum.QUORUM,
    )

    res = await sharding_service.commit_vector_mutation(req)
    assert res.committed_log_index == 1
    assert res.term == 1
    assert res.vectors_written == 2
    assert res.quorum_achieved is True
    assert res.elapsed_ms >= 0.0

    # Verify Raft log entry
    assert len(sharding_service.replicated_log) == 1
    entry = sharding_service.replicated_log[0]
    assert entry.command_type == "INSERT_VECTORS"
    assert entry.payload["tenant_id"] == "tenant_acme"
    assert entry.payload["vector_count"] == 2

    # Verify shard count updated
    shard = sharding_service.get_shard(res.shard_id)
    assert shard.vector_count == 2
    assert shard.index_size_bytes > 0


@pytest.mark.asyncio
async def test_scatter_gather_search_and_fusion(sharding_service: VectorRaftShardingService):
    """Verify parallel scatter-gather vector query executes and ranks results across shards."""
    # Insert vectors across 2 distinct documents
    await sharding_service.commit_vector_mutation(
        ShardMutationRequest(
            tenant_id="tenant_globex",
            document_id="doc_a",
            vectors=[
                {"chunk_id": "c_a1", "vector": [1.0, 0.0, 0.0], "text": "Exact query vector match"},
                {"chunk_id": "c_a2", "vector": [0.0, 1.0, 0.0], "text": "Orthogonal vector"},
            ],
        )
    )
    await sharding_service.commit_vector_mutation(
        ShardMutationRequest(
            tenant_id="tenant_globex",
            document_id="doc_b",
            vectors=[
                {"chunk_id": "c_b1", "vector": [0.95, 0.05, 0.0], "text": "Very close match"},
            ],
        )
    )

    # Search with query vector [1.0, 0.0, 0.0]
    query = ScatterGatherQuery(
        tenant_id="tenant_globex",
        query_vector=[1.0, 0.0, 0.0],
        top_k=5,
        read_quorum=ReadQuorum.QUORUM,
    )

    res = await sharding_service.scatter_gather_search(query)
    assert res.total_shards_queried == 8
    assert res.successful_shards == 8
    assert res.quorum_achieved is True
    assert len(res.results) == 3

    # Top candidate should be c_a1 with score 1.0
    assert res.results[0].chunk_id == "c_a1"
    assert res.results[0].score == 1.0

    # Second candidate should be c_b1 with high similarity
    assert res.results[1].chunk_id == "c_b1"
    assert res.results[1].score > 0.9

    # Third candidate is orthogonal (0.0)
    assert res.results[2].chunk_id == "c_a2"
    assert res.results[2].score == 0.0


@pytest.mark.asyncio
async def test_read_quorum_enforcement(sharding_service: VectorRaftShardingService):
    """Verify ReadQuorum.ALL raises RaftQuorumNotReachedError when a shard is degraded or offline."""
    # Mark one shard offline
    sharding_service.shards["shard_000"].status = ShardStatus.OFFLINE

    query = ScatterGatherQuery(
        tenant_id="tenant_globex",
        query_vector=[1.0, 0.0, 0.0],
        top_k=5,
        read_quorum=ReadQuorum.ALL,
    )

    with pytest.raises(RaftQuorumNotReachedError) as exc_info:
        await sharding_service.scatter_gather_search(query)
    assert "Read quorum 'all' requires" in str(exc_info.value)


@pytest.mark.asyncio
async def test_online_shard_rebalancing(sharding_service: VectorRaftShardingService):
    """Verify online shard migration executes without data loss and updates leader/replica mapping."""
    # Add vectors to shard_000
    target_shard = sharding_service.get_shard("shard_000")
    source_node = target_shard.leader_node_id
    target_node = next(n for n in sharding_service.nodes if n != source_node)

    await sharding_service.commit_vector_mutation(
        ShardMutationRequest(
            tenant_id="tenant_acme",
            document_id="doc_x",
            vectors=[{"chunk_id": "cx_1", "vector": [0.5, 0.5, 0.0], "text": "Shard rebalancing test"}],
        )
    )

    plan = await sharding_service.trigger_shard_rebalance(
        source_node_id=source_node,
        target_node_id=target_node,
        shard_id="shard_000",
    )

    assert plan.status == "completed"
    assert plan.source_node_id == source_node
    assert plan.target_node_id == target_node
    assert plan.shard_id == "shard_000"
    assert plan.completion_time is not None

    # Verify shard now led by target_node
    updated_shard = sharding_service.get_shard("shard_000")
    assert updated_shard.leader_node_id == target_node
    assert updated_shard.status == ShardStatus.HEALTHY
    assert source_node in updated_shard.replica_node_ids

    # Same source and target should conflict
    with pytest.raises(ShardRebalanceConflictError):
        await sharding_service.trigger_shard_rebalance(target_node, target_node, "shard_000")


def test_shard_snapshot(sharding_service: VectorRaftShardingService):
    """Verify snapshot generation captures vector counts and partition boundaries."""
    snap = sharding_service.create_snapshot("shard_001")
    assert snap["shard_id"] == "shard_001"
    assert "snapshot_id" in snap
    assert snap["hash_range_start"] >= 0
    assert isinstance(snap["vectors"], list)


def test_fastapi_endpoints(client: TestClient):
    """Verify REST API endpoints under /v1/shards/*."""
    # 1. GET /v1/shards/topology
    r_topo = client.get("/v1/shards/topology")
    assert r_topo.status_code == 200
    data_topo = r_topo.json()
    assert data_topo["total_shards"] == 8
    assert len(data_topo["shards"]) == 8

    # 2. GET /v1/shards/raft/status
    r_raft = client.get("/v1/shards/raft/status")
    assert r_raft.status_code == 200
    data_raft = r_raft.json()
    assert data_raft["leader_elected"] is True
    assert len(data_raft["nodes"]) == 3

    # 3. POST /v1/shards/mutate
    r_mutate = client.post(
        "/v1/shards/mutate",
        json={
            "tenant_id": "tenant_api_test",
            "document_id": "doc_rest_1",
            "vectors": [{"chunk_id": "api_c1", "vector": [0.2, 0.4, 0.6], "text": "API test chunk"}],
            "write_quorum": "quorum",
        },
    )
    assert r_mutate.status_code == 200
    data_mutate = r_mutate.json()
    assert data_mutate["vectors_written"] == 1
    assert data_mutate["quorum_achieved"] is True

    # 4. POST /v1/shards/query
    r_query = client.post(
        "/v1/shards/query",
        json={
            "tenant_id": "tenant_api_test",
            "query_vector": [0.2, 0.4, 0.6],
            "top_k": 3,
            "read_quorum": "quorum",
        },
    )
    assert r_query.status_code == 200
    data_query = r_query.json()
    assert data_query["total_shards_queried"] == 8
    assert len(data_query["results"]) >= 1
    assert data_query["results"][0]["chunk_id"] == "api_c1"

    # 5. POST /v1/shards/rebalance
    r_reb = client.post(
        "/v1/shards/rebalance",
        json={"source_node_id": "node_core_01", "target_node_id": "node_core_02", "shard_id": "shard_002"},
    )
    assert r_reb.status_code == 200
    data_reb = r_reb.json()
    assert data_reb["status"] == "completed"

    # 6. POST /v1/shards/{shard_id}/snapshot
    r_snap = client.post("/v1/shards/shard_000/snapshot")
    assert r_snap.status_code == 200
    assert r_snap.json()["shard_id"] == "shard_000"
