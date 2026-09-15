"""FastAPI Router for Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus (M117).

Exposes:
- Shard partition topology and virtual node hash ring status (`/v1/shards/topology`)
- Parallel scatter-gather vector search across partitions (`/v1/shards/query`)
- Replicated vector index mutations via Raft consensus (`/v1/shards/mutate`)
- Cluster-wide Raft consensus telemetry and terms (`/v1/shards/raft/status`)
- Online zero-downtime shard rebalancing and migration (`/v1/shards/rebalance`)
- Shard partition state snapshot capture (`/v1/shards/{shard_id}/snapshot`)
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.container import container
from src.domain.abstractions.exceptions import (
    LeaderNotElectedError,
    RaftQuorumNotReachedError,
    ShardNotFoundError,
    ShardRebalanceConflictError,
    VectorShardingError,
)
from src.domain.abstractions.vector_sharding import (
    RaftConsensusStatus,
    ScatterGatherQuery,
    ScatterGatherResponse,
    ShardMutationRequest,
    ShardMutationResponse,
    ShardPartition,
    ShardRebalancePlan,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/shards", tags=["Decentralized Vector Sharding & Raft"])


class ShardTopologyResponse(BaseModel):
    """Cluster-wide vector shard partitions and hash ring topology."""

    cluster_id: str
    total_shards: int
    replication_factor: int
    shards: list[ShardPartition] = Field(default_factory=list)
    skew_metrics: dict[str, Any] = Field(default_factory=dict)


class TriggerRebalancePayload(BaseModel):
    """Optional payload specifying manual source/target nodes and shard ID for rebalancing."""

    source_node_id: str | None = None
    target_node_id: str | None = None
    shard_id: str | None = None


class ElectionPayload(BaseModel):
    """Payload to trigger leader election for a candidate node."""

    candidate_node_id: str


@router.get(
    "/topology",
    response_model=ShardTopologyResponse,
    summary="Get Shard Topology & Consistent Hash Partitions",
)
async def get_shard_topology() -> ShardTopologyResponse:
    """Return all active vector shard partitions, hash ranges, leaders, and replicas."""
    service = container.vector_raft_sharding_service
    shards = service.list_shards()
    skew = service.evaluate_cluster_skew()
    return ShardTopologyResponse(
        cluster_id=service.cluster_id,
        total_shards=len(shards),
        replication_factor=service.replication_factor,
        shards=shards,
        skew_metrics=skew,
    )


@router.post(
    "/query",
    response_model=ScatterGatherResponse,
    summary="Scatter-Gather Parallel Vector Search",
)
async def query_sharded_vectors(query: ScatterGatherQuery) -> ScatterGatherResponse:
    """Execute parallel vector search across shard partitions with score fusion and quorum checks."""
    service = container.vector_raft_sharding_service
    try:
        return await service.scatter_gather_search(query)
    except RaftQuorumNotReachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except VectorShardingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/mutate",
    response_model=ShardMutationResponse,
    summary="Commit Vector Mutation via Raft Consensus",
)
async def mutate_sharded_vectors(request: ShardMutationRequest) -> ShardMutationResponse:
    """Replicate vector index insertions/deletions across replica group via Raft consensus log."""
    service = container.vector_raft_sharding_service
    try:
        return await service.commit_vector_mutation(request)
    except LeaderNotElectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except VectorShardingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/raft/status",
    response_model=RaftConsensusStatus,
    summary="Get Raft Consensus Engine State",
)
async def get_raft_consensus_status() -> RaftConsensusStatus:
    """Return cluster-wide Raft consensus telemetry, current term, leader ID, and recent log entries."""
    service = container.vector_raft_sharding_service
    return service.get_raft_status()


@router.post(
    "/election",
    summary="Trigger Raft Leader Election",
)
async def trigger_raft_election(payload: ElectionPayload) -> dict[str, Any]:
    """Simulate Raft leader election for a candidate node."""
    service = container.vector_raft_sharding_service
    try:
        success = service.trigger_election(payload.candidate_node_id)
        return {
            "success": success,
            "current_term": service.current_term,
            "active_leader_id": service.active_leader_id,
        }
    except ShardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/rebalance",
    response_model=ShardRebalancePlan,
    summary="Trigger Online Shard Rebalance & Migration",
)
async def rebalance_shards(payload: TriggerRebalancePayload | None = None) -> ShardRebalancePlan:
    """Execute two-phase online shard migration from source to target node to eliminate cluster skew."""
    service = container.vector_raft_sharding_service
    try:
        source = payload.source_node_id if payload else None
        target = payload.target_node_id if payload else None
        shard = payload.shard_id if payload else None
        return await service.trigger_shard_rebalance(source, target, shard)
    except ShardRebalanceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ShardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VectorShardingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{shard_id}/snapshot",
    summary="Capture Shard State Snapshot",
)
async def snapshot_shard(shard_id: str) -> dict[str, Any]:
    """Capture immutable snapshot of shard state and vector contents."""
    service = container.vector_raft_sharding_service
    try:
        return service.create_snapshot(shard_id)
    except ShardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
