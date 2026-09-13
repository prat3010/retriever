"""FastAPI Router for Autonomous Edge Fleet Swarm Mesh & P2P Gossip Replication (M102).

Exposes administrative mesh orchestration and tenant-scoped synchronization endpoints:
- GET /v1/admin/swarm/topology: Cluster membership, peer states, RTT metrics & convergence
- POST /v1/admin/swarm/join: Dynamic peer node registration into the swarm mesh
- POST /v1/admin/swarm/leave: Graceful voluntary departure of a peer
- POST /v1/admin/swarm/probe: SWIM failure detector direct ping or indirect ping-req probe
- POST /v1/admin/swarm/refute: Suspicion rumor refutation with advanced incarnation
- POST /v1/admin/swarm/gossip: Epidemic gossip message ingestion
- POST /v1/admin/swarm/sync: Push-pull anti-entropy sequence exchange
- POST /v1/admin/swarm/partition-heal: Causal reconciliation of disconnected network partitions
- GET /v1/tenants/{tenantId}/swarm/status: Tenant-scoped mesh topology & sync health
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.swarm import (
    AntiEntropyDigest,
    AntiEntropySyncResult,
    GossipMessage,
    PartitionReconciliationReport,
    SwarmNode,
    SwarmNodeRole,
    SwarmTopology,
)

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/v1/admin/swarm",
    tags=["swarm", "admin"],
    dependencies=[Depends(verify_admin_key)],
)

tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/swarm",
    tags=["swarm", "tenant"],
    dependencies=[Depends(verify_tenant_or_admin)],
)


class RegisterSwarmNodeRequest(BaseModel):
    """Payload to register an edge device into the swarm mesh."""

    node_id: str = Field(..., min_length=2, max_length=128)
    tenant_id: str = Field(..., description="Scoped tenant UUID")
    device_name: str = Field(..., min_length=1, max_length=255)
    role: SwarmNodeRole = Field(default=SwarmNodeRole.CORE_PEER)
    address: str = Field(default="127.0.0.1")
    port: int = Field(default=7946, ge=1, le=65535)
    meta_data: dict[str, Any] = Field(default_factory=dict)


class ProbeSwarmNodeRequest(BaseModel):
    """Payload to trigger a SWIM failure detection probe."""

    tenant_id: str
    prober_node_id: str
    target_node_id: str
    simulated_ack: bool = Field(default=True, description="True for ping success; False for timeout/suspect")


class SyncAntiEntropyRequest(BaseModel):
    """Payload to trigger push-pull anti-entropy sequence exchange."""

    tenant_id: str
    sender_id: str
    target_id: str
    highest_sequence: int = Field(default=0, ge=0)
    target_sequences: list[int] | None = Field(default=None)


class PartitionHealRequest(BaseModel):
    """Payload to reconcile state between two reconnected peer groups."""

    tenant_id: str
    partition_a_nodes: list[str] = Field(..., min_length=1)
    partition_b_nodes: list[str] = Field(..., min_length=1)
    mutations_a: list[dict[str, Any]] | None = Field(default=None)
    mutations_b: list[dict[str, Any]] | None = Field(default=None)


# ── Administrative Swarm Endpoints ─────────────────────────────────────────


@admin_router.get("/topology", response_model=SwarmTopology)
async def get_swarm_topology(
    tenant_id: str = Query("default", description="Tenant UUID to query topology for"),
) -> SwarmTopology:
    """Retrieve full cluster membership, node states, and convergence metrics."""
    return container.swarm_mesh_adapter.get_topology(tenant_id=tenant_id)


@admin_router.post("/join", response_model=SwarmNode, status_code=status.HTTP_201_CREATED)
async def join_swarm_mesh(payload: RegisterSwarmNodeRequest) -> SwarmNode:
    """Register a new peer device into the swarm mesh."""
    node = SwarmNode(
        node_id=payload.node_id,
        tenant_id=payload.tenant_id,
        device_name=payload.device_name,
        role=payload.role,
        address=payload.address,
        port=payload.port,
        meta_data=payload.meta_data,
    )
    return container.swarm_mesh_adapter.register_node(node)


@admin_router.post("/leave")
async def leave_swarm_mesh(
    tenant_id: str = Query(...),
    node_id: str = Query(...),
) -> dict[str, Any]:
    """Gracefully detach an edge node from the swarm mesh."""
    success = container.swarm_mesh_adapter.deregister_node(tenant_id=tenant_id, node_id=node_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in tenant '{tenant_id}'",
        )
    return {"status": "left", "tenant_id": tenant_id, "node_id": node_id}


@admin_router.post("/probe", response_model=SwarmNode)
async def probe_swarm_node(payload: ProbeSwarmNodeRequest) -> SwarmNode:
    """Execute a SWIM direct ping or indirect ping-req probe against a peer."""
    try:
        return container.swarm_mesh_adapter.probe_node_swim(
            tenant_id=payload.tenant_id,
            prober_node_id=payload.prober_node_id,
            target_node_id=payload.target_node_id,
            simulated_ack=payload.simulated_ack,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@admin_router.post("/refute", response_model=SwarmNode)
async def refute_node_suspicion(
    tenant_id: str = Query(...),
    node_id: str = Query(...),
) -> SwarmNode:
    """Refute a suspicion rumor by advancing incarnation and restoring HEALTHY status."""
    try:
        return container.swarm_mesh_adapter.refute_suspicion(tenant_id=tenant_id, node_id=node_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@admin_router.post("/gossip")
async def ingest_gossip_message(message: GossipMessage) -> dict[str, Any]:
    """Process an inbound epidemic gossip message."""
    response = container.swarm_mesh_adapter.handle_gossip(message)
    if response:
        return {"status": "processed", "response": response.model_dump(mode="json")}
    return {"status": "processed", "response": None}


@admin_router.post("/sync", response_model=AntiEntropySyncResult)
async def sync_anti_entropy(payload: SyncAntiEntropyRequest) -> AntiEntropySyncResult:
    """Execute push-pull anti-entropy sequence exchange between two peers."""
    digest = AntiEntropyDigest(
        sender_id=payload.sender_id,
        tenant_id=payload.tenant_id,
        highest_sequence=payload.highest_sequence,
    )
    return container.swarm_mesh_adapter.sync_anti_entropy(
        tenant_id=payload.tenant_id,
        sender_id=payload.sender_id,
        target_id=payload.target_id,
        digest=digest,
        target_sequences=payload.target_sequences,
    )


@admin_router.post("/partition-heal", response_model=PartitionReconciliationReport)
async def reconcile_partitions(payload: PartitionHealRequest) -> PartitionReconciliationReport:
    """Reconcile diverged cluster partitions using causal vector clocks and deterministic LWW."""
    return container.swarm_mesh_adapter.reconcile_partitions(
        tenant_id=payload.tenant_id,
        partition_a_nodes=payload.partition_a_nodes,
        partition_b_nodes=payload.partition_b_nodes,
        mutations_a=payload.mutations_a,
        mutations_b=payload.mutations_b,
    )


# ── Tenant-Scoped Swarm Endpoints ──────────────────────────────────────────


@tenant_router.get("/status", response_model=SwarmTopology)
async def get_tenant_swarm_status(tenantId: str) -> SwarmTopology:
    """Retrieve tenant-scoped swarm mesh topology, active peers, and vector clocks."""
    return container.swarm_mesh_adapter.get_topology(tenant_id=tenantId)
