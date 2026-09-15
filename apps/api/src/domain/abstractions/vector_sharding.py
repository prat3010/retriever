"""Domain Abstractions for Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus (M117).

Conforms strictly to Hexagonal Architecture boundaries:
- Pure Pydantic models, StrEnums, and standard library typing.
- Zero infrastructure, framework, or database dependencies.
- Enforces multi-tenancy isolation and consistent hash partitioning.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ShardStatus(StrEnum):
    """Operational health state of a vector partition shard."""

    HEALTHY = "healthy"
    REBALANCING = "rebalancing"
    SNAPSHOT_SYNC = "snapshot_sync"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class RaftRole(StrEnum):
    """Raft consensus protocol state of a cluster node."""

    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


class ReadQuorum(StrEnum):
    """Consistency level for scatter-gather vector read queries."""

    LOCAL = "local"  # Lowest latency; local node replica only
    ONE = "one"  # First available replica response
    QUORUM = "quorum"  # Majority of shard replicas must respond
    ALL = "all"  # Strict consistency; all replicas must respond


class WriteQuorum(StrEnum):
    """Consistency level required for vector index mutations."""

    ONE = "one"  # Leader commit only
    QUORUM = "quorum"  # Majority consensus across replica group
    ALL = "all"  # Replicated to all active replicas before commit


class ShardPartition(BaseModel):
    """A horizontal vector index partition mapped across consistent hash boundaries."""

    shard_id: str
    tenant_id: str | None = None  # None for shared tenant shards; specific ID for dedicated tenant shards
    hash_range_start: int = Field(ge=0, le=4294967295)  # 32-bit FNV-1a / Murmur ring range
    hash_range_end: int = Field(ge=0, le=4294967295)
    leader_node_id: str
    replica_node_ids: list[str] = Field(default_factory=list)
    status: ShardStatus = ShardStatus.HEALTHY
    vector_count: int = Field(default=0, ge=0)
    index_size_bytes: int = Field(default=0, ge=0)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class RaftLogEntry(BaseModel):
    """An immutable entry in the replicated Raft log for vector index mutations."""

    index: int = Field(ge=1)
    term: int = Field(ge=1)
    command_type: str  # INSERT_VECTORS, DELETE_VECTORS, REBUILD_INDEX, ADD_REPLICA, REMOVE_REPLICA
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class RaftNodeState(BaseModel):
    """Raft consensus engine state for a single cluster participant."""

    node_id: str
    current_term: int = Field(default=1, ge=1)
    voted_for: str | None = None
    role: RaftRole = RaftRole.FOLLOWER
    commit_index: int = Field(default=0, ge=0)
    last_applied: int = Field(default=0, ge=0)
    leader_id: str | None = None
    log_length: int = Field(default=0, ge=0)
    heartbeat_timestamp: float = Field(default_factory=time.time)


class RaftConsensusStatus(BaseModel):
    """Cluster-wide Raft consensus telemetry and health metrics."""

    cluster_id: str
    current_term: int
    active_leader_id: str | None
    total_nodes: int
    leader_elected: bool
    quorum_healthy: bool
    nodes: list[RaftNodeState] = Field(default_factory=list)
    recent_log_entries: list[RaftLogEntry] = Field(default_factory=list)


class ScatterGatherQuery(BaseModel):
    """Structured query for parallel vector search across distributed shard partitions."""

    tenant_id: str
    query_vector: list[float] = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    read_quorum: ReadQuorum = ReadQuorum.QUORUM
    filter_metadata: dict[str, Any] = Field(default_factory=dict)


class ShardCandidate(BaseModel):
    """A single vector candidate retrieved from an individual shard partition."""

    chunk_id: str
    score: float
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    shard_id: str
    node_id: str


class ShardQueryBreakdown(BaseModel):
    """Execution telemetry for a single shard partition involved in a query."""

    shard_id: str
    node_id: str
    latency_ms: float
    candidates_count: int
    status: str = "success"


class ScatterGatherResponse(BaseModel):
    """Globally merged and normalized results from a distributed scatter-gather query."""

    query_id: str
    tenant_id: str
    total_shards_queried: int
    successful_shards: int
    quorum_achieved: bool
    total_latency_ms: float
    shard_breakdown: list[ShardQueryBreakdown] = Field(default_factory=list)
    results: list[ShardCandidate] = Field(default_factory=list)


class ShardRebalancePlan(BaseModel):
    """Specification and execution status for migrating a shard across cluster nodes."""

    plan_id: str
    source_node_id: str
    target_node_id: str
    shard_id: str
    status: str = "planned"  # planned, in_progress, completed, failed
    vectors_transferred: int = 0
    total_vectors: int = 0
    start_time: float = Field(default_factory=time.time)
    completion_time: float | None = None
    error_message: str | None = None


class ShardMutationRequest(BaseModel):
    """Request to commit vector mutations to a target shard via Raft consensus."""

    tenant_id: str
    document_id: str
    vectors: list[dict[str, Any]]  # List of chunk vectors: [{"chunk_id": str, "vector": list[float], "text": str, "metadata": dict}]
    write_quorum: WriteQuorum = WriteQuorum.QUORUM


class ShardMutationResponse(BaseModel):
    """Result of committing vector mutations to a shard."""

    shard_id: str
    committed_log_index: int
    term: int
    vectors_written: int
    quorum_achieved: bool
    elapsed_ms: float


class VectorStoragePort(Protocol):
    """Abstract port for low-level vector persistence and local nearest-neighbor search."""

    async def insert_vectors(self, shard_id: str, vectors: list[dict[str, Any]]) -> int:
        ...

    async def search_vectors(
        self,
        shard_id: str,
        query_vector: list[float],
        top_k: int,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[ShardCandidate]:
        ...

    async def snapshot_shard(self, shard_id: str) -> dict[str, Any]:
        ...

    async def restore_snapshot(self, shard_id: str, snapshot_data: dict[str, Any]) -> bool:
        ...
