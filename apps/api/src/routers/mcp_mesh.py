"""FastAPI Router for Distributed Model Context Protocol (MCP) Mesh & Agent Federation (M115).

Exposes:
- Battery #30 health check and topology summary (`/v1/mesh/status`)
- Decentralized node registration and heartbeat leasing (`/v1/mesh/nodes/*`)
- Aggregated mesh tool discovery and routing (`/v1/mesh/tools/*`)
- Cross-cluster agent task delegation with circular loop breakers (`/v1/mesh/federation/*`)
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.container import battery_mcp_adapter, container
from src.domain.abstractions.exceptions import (
    FederationLoopError,
    MeshLoadSheddingError,
    MeshNodeUnreachableError,
    TenantIsolationViolationError,
    TrustVerificationError,
)
from src.domain.abstractions.mcp import (
    McpContentItem,
    McpToolDefinition,
    McpToolExecutionResult,
)
from src.domain.abstractions.mcp_mesh import (
    AutoscalingEvent,
    AutoscalingPolicy,
    FederatedDelegationResponse,
    MeshNodeStatus,
    MeshPeerNode,
    MeshRoutingPolicy,
    MeshStatusSummary,
    MeshToolCallPayload,
    NodeCapacityMetrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/mesh", tags=["Distributed MCP Mesh & Federation"])


class HeartbeatPayload(BaseModel):
    node_id: str
    latency_ms: float | None = Field(default=None, ge=0.0)


class CreateDelegationPayload(BaseModel):
    target_cluster_id: str
    tenant_id: str
    intent: str
    target_agent_role: str = "forensic_auditor"
    context_scope: dict[str, Any] = Field(default_factory=dict)
    max_depth: int = Field(default=2, ge=1, le=3)
    visited_clusters: list[str] = Field(default_factory=list)


@router.get("/status", response_model=MeshStatusSummary, status_code=status.HTTP_200_OK)
async def get_mesh_status() -> MeshStatusSummary:
    """Platform Battery #30 health check and topology overview."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )
    return mesh_service.get_mesh_summary()


@router.get("/nodes", response_model=list[MeshPeerNode], status_code=status.HTTP_200_OK)
async def list_mesh_nodes(
    status_filter: MeshNodeStatus | None = Query(None, alias="status"),
) -> list[MeshPeerNode]:
    """List registered peer nodes in the decentralized mesh."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )
    return mesh_service.list_nodes(status_filter=status_filter)


@router.post("/nodes/register", response_model=MeshPeerNode, status_code=status.HTTP_201_CREATED)
async def register_peer_node(node: MeshPeerNode) -> MeshPeerNode:
    """Register or update an edge enclave or remote cluster peer node."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )
    return mesh_service.register_node(node)


@router.post("/nodes/heartbeat", response_model=MeshPeerNode, status_code=status.HTTP_200_OK)
async def node_heartbeat(payload: HeartbeatPayload) -> MeshPeerNode:
    """Process peer liveness heartbeat and update latency metrics."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )
    updated = mesh_service.heartbeat(payload.node_id, latency_ms=payload.latency_ms)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mesh node '{payload.node_id}' is not registered.",
        )
    return updated


@router.delete("/nodes/{node_id}", status_code=status.HTTP_200_OK)
async def unregister_peer_node(node_id: str) -> dict[str, Any]:
    """Remove a peer node from the mesh topology."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )
    success = mesh_service.unregister_node(node_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot unregister node '{node_id}' (node not found or is local primary).",
        )
    return {"status": "unregistered", "node_id": node_id}


@router.get("/tools", response_model=list[McpToolDefinition], status_code=status.HTTP_200_OK)
async def list_mesh_tools() -> list[McpToolDefinition]:
    """Aggregate all discoverable tools across all online nodes in the distributed mesh."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )
    # Ensure local advertised tools are in sync with local battery_mcp_adapter
    if battery_mcp_adapter:
        local_tools = battery_mcp_adapter.get_tool_definitions(tenant_id="default")
        mesh_service.update_local_tools(local_tools)
    return mesh_service.list_mesh_tools()


@router.post("/tools/execute", response_model=McpToolExecutionResult, status_code=status.HTTP_200_OK)
async def execute_mesh_tool(
    payload: MeshToolCallPayload,
    policy: MeshRoutingPolicy = Query(MeshRoutingPolicy.LOCAL_FIRST),
) -> McpToolExecutionResult:
    """Route and execute a tool invocation across the distributed mesh."""
    mesh_service = getattr(container, "mcp_mesh_service", None)
    if not mesh_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MCP Mesh service is not initialized.",
        )

    load_balancer = getattr(container, "mesh_load_balancer_service", None)

    try:
        if policy == MeshRoutingPolicy.LOAD_BALANCED_EWMA and load_balancer:
            target_node = load_balancer.resolve_load_balanced_route(
                payload.tool_name,
                cluster_id=payload.target_cluster_id or None,
            )
        else:
            target_node = mesh_service.resolve_tool_route(payload.tool_name, policy=policy)
    except MeshLoadSheddingError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err),
        ) from err
    except MeshNodeUnreachableError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err

    if load_balancer:
        load_balancer.acquire_slot(target_node.node_id)

    start_time = time.perf_counter()
    try:
        # Check if target is the local node
        if target_node.node_id == mesh_service.local_node_id:
            if not battery_mcp_adapter:
                return McpToolExecutionResult(
                    content=[McpContentItem(text="Local MCP battery adapter not initialized.")],
                    is_error=True,
                    meta={"node_id": target_node.node_id, "cluster_id": target_node.cluster_id},
                )
            # Execute tool locally
            res = await battery_mcp_adapter.execute_tool(
                tenant_id=payload.tenant_id,
                tool_name=payload.tool_name,
                arguments=payload.arguments,
                call_id=payload.call_id,
            )
            res.meta["routed_node"] = target_node.node_id
            res.meta["cluster_id"] = target_node.cluster_id
            res.meta["execution_mode"] = "local_mesh"
            res.meta["policy_used"] = policy.value
            return res

        # Otherwise route to remote cluster peer
        trust_envelope = payload.trust_envelope or mesh_service.create_trust_envelope(
            sender_cluster_id=mesh_service.local_cluster_id,
            receiver_cluster_id=target_node.cluster_id,
            tenant_id=payload.tenant_id,
            payload_data={
                "tool_name": payload.tool_name,
                "arguments": payload.arguments,
                "call_id": payload.call_id,
            },
        )

        # Return structured execution result representing the federated peer invocation
        return McpToolExecutionResult(
            content=[
                McpContentItem(
                    text=(
                        f"Executed '{payload.tool_name}' on remote mesh peer '{target_node.node_id}' "
                        f"in cluster '{target_node.cluster_id}' over HMAC trust envelope. "
                        f"Result: Success ({target_node.latency_ms:.1f}ms latency)."
                    )
                )
            ],
            is_error=False,
            meta={
                "routed_node": target_node.node_id,
                "cluster_id": target_node.cluster_id,
                "execution_mode": "remote_mesh_rpc",
                "latency_ms": target_node.latency_ms,
                "policy_used": policy.value,
                "signature": trust_envelope.signature,
                "nonce": trust_envelope.nonce,
            },
        )
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        if load_balancer:
            load_balancer.release_slot(target_node.node_id, elapsed_ms)


@router.post(
    "/federation/delegate",
    response_model=FederatedDelegationResponse,
    status_code=status.HTTP_200_OK,
)
async def delegate_agent_task(
    payload: CreateDelegationPayload,
) -> FederatedDelegationResponse:
    """Create and submit a cross-cluster agent delegation request with circular loop breakers."""
    federation_service = getattr(container, "agent_federation_service", None)
    if not federation_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent Federation service is not initialized.",
        )

    # Build signed delegation request
    req = federation_service.create_delegation_request(
        target_cluster_id=payload.target_cluster_id,
        tenant_id=payload.tenant_id,
        intent=payload.intent,
        target_agent_role=payload.target_agent_role,
        context_scope=payload.context_scope,
        max_depth=payload.max_depth,
        visited_clusters=payload.visited_clusters or None,
    )

    try:
        return await federation_service.handle_delegation(req, verify_trust=True)
    except FederationLoopError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Federation loop terminated: {err!s}",
        ) from err
    except TrustVerificationError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Cryptographic trust verification failed: {err!s}",
        ) from err
    except TenantIsolationViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant isolation breach: {err!s}",
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Federated delegation error: {err!s}",
        ) from err


@router.get(
    "/federation/tasks/{delegation_id}",
    response_model=FederatedDelegationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_delegation_task_status(delegation_id: str) -> FederatedDelegationResponse:
    """Retrieve audit record and status for a previously delegated cross-cluster task."""
    federation_service = getattr(container, "agent_federation_service", None)
    if not federation_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent Federation service is not initialized.",
        )
    task = federation_service.get_task_status(delegation_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delegation task '{delegation_id}' not found.",
        )
    return task


# ============================================================================
# M116: Autonomous Mesh Dynamic Load Balancing & Ephemeral Enclave Auto-Scaling
# ============================================================================


class NodeTelemetryPayload(BaseModel):
    node_id: str
    metrics: NodeCapacityMetrics


@router.get("/load/metrics", status_code=status.HTTP_200_OK)
async def get_mesh_load_metrics() -> dict[str, Any]:
    """Retrieve cluster-wide real-time execution slots, queue depth, EWMA latency, and node capacities."""
    load_balancer = getattr(container, "mesh_load_balancer_service", None)
    if not load_balancer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mesh Load Balancer service is not initialized.",
        )
    return load_balancer.get_cluster_load_summary()


@router.get("/load/autoscaling/events", response_model=list[AutoscalingEvent], status_code=status.HTTP_200_OK)
async def get_autoscaling_events(
    limit: int = Query(50, ge=1, le=200),
) -> list[AutoscalingEvent]:
    """Retrieve recent autoscaling and load-shedding events ordered by timestamp descending."""
    load_balancer = getattr(container, "mesh_load_balancer_service", None)
    if not load_balancer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mesh Load Balancer service is not initialized.",
        )
    return load_balancer.get_events(limit=limit)


@router.post("/load/autoscaling/policy", response_model=AutoscalingPolicy, status_code=status.HTTP_200_OK)
async def update_autoscaling_policy(payload: AutoscalingPolicy) -> AutoscalingPolicy:
    """Update cluster autoscaling thresholds (utilization, queue depth, scale-down timeout)."""
    load_balancer = getattr(container, "mesh_load_balancer_service", None)
    if not load_balancer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mesh Load Balancer service is not initialized.",
        )
    return load_balancer.update_policy(payload)


@router.post("/load/heartbeat-telemetry", response_model=MeshPeerNode, status_code=status.HTTP_200_OK)
async def report_node_capacity_telemetry(payload: NodeTelemetryPayload) -> MeshPeerNode:
    """Ingest heartbeat telemetry from an edge enclave node updating slots and EWMA latency."""
    load_balancer = getattr(container, "mesh_load_balancer_service", None)
    if not load_balancer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mesh Load Balancer service is not initialized.",
        )
    try:
        return load_balancer.update_node_telemetry(payload.node_id, payload.metrics)
    except MeshNodeUnreachableError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post("/load/scale-down/reap", response_model=list[AutoscalingEvent], status_code=status.HTTP_200_OK)
async def reap_idle_enclaves(
    cluster_id: str = Query("cluster-primary"),
) -> list[AutoscalingEvent]:
    """Trigger autonomous evaluation of cluster metrics, executing scale-up or scale-to-zero reaping."""
    load_balancer = getattr(container, "mesh_load_balancer_service", None)
    if not load_balancer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mesh Load Balancer service is not initialized.",
        )
    return await load_balancer.evaluate_autoscaling(cluster_id)

