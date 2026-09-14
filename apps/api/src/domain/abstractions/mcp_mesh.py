"""Domain Abstractions for Distributed Model Context Protocol (MCP) Mesh & Agent Federation (M115).

Conforms strictly to Hexagonal Architecture boundaries:
- Pure Pydantic models, StrEnums, and standard library typing.
- Zero infrastructure, framework, or database dependencies.
- Enforces mutual trust envelopes, loop detection, and multi-tenant isolation.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.domain.abstractions.mcp import McpToolDefinition


class MeshNodeRole(StrEnum):
    """Architectural role of a node within the decentralized MCP mesh."""

    SEED_GATEWAY = "seed_gateway"
    SOVEREIGN_NODE = "sovereign_node"
    EDGE_ENCLAVE = "edge_enclave"
    REMOTE_PEER = "remote_peer"


class MeshNodeStatus(StrEnum):
    """Operational health state of a peer node in the mesh."""

    ONLINE = "online"
    DEGRADED = "degraded"
    STANDBY = "standby"
    UNREACHABLE = "unreachable"


class MeshRoutingPolicy(StrEnum):
    """Traffic routing strategy for remote MCP tool dispatch."""

    LOCAL_FIRST = "local_first"
    LOWEST_LATENCY = "lowest_latency"
    LOAD_BALANCED_EWMA = "load_balanced_ewma"
    ROUND_ROBIN = "round_robin"
    FAILOVER = "failover"


class FederatedTaskStatus(StrEnum):
    """Execution lifecycle state of a cross-cluster agent delegation task."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class TrustEnvelope(BaseModel):
    """Cryptographic trust envelope securing inter-cluster tool RPC and delegation."""

    sender_cluster_id: str
    receiver_cluster_id: str
    tenant_id: str
    timestamp: float = Field(default_factory=time.time)
    nonce: str
    signature: str
    payload_hash: str


class NodeCapacityMetrics(BaseModel):
    """Dynamic utilization, concurrency, and EWMA latency metrics for a mesh node."""

    cpu_utilization_pct: float = Field(default=15.0, ge=0.0, le=100.0)
    memory_utilization_pct: float = Field(default=25.0, ge=0.0, le=100.0)
    active_execution_slots: int = Field(default=0, ge=0)
    max_execution_slots: int = Field(default=16, ge=1)
    queue_depth: int = Field(default=0, ge=0)
    ewma_latency_ms: float = Field(default=10.0, ge=0.0)
    is_ephemeral: bool = Field(default=False)
    ephemeral_idle_seconds: float = Field(default=0.0, ge=0.0)


class AutoscalingAction(StrEnum):
    """Actions performed by the autonomous mesh autoscaler."""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SHED_LOAD = "shed_load"
    NO_OP = "no_op"


class AutoscalingPolicy(BaseModel):
    """Dynamic threshold parameters governing automated scale-out and scale-to-zero."""

    scale_up_latency_ms: float = Field(default=150.0, ge=10.0)
    scale_up_queue_depth: int = Field(default=10, ge=1)
    scale_up_utilization_pct: float = Field(default=85.0, ge=10.0, le=100.0)
    scale_down_idle_seconds: float = Field(default=300.0, ge=10.0)
    max_ephemeral_enclaves: int = Field(default=4, ge=0)
    load_shedding_threshold_pct: float = Field(default=95.0, ge=50.0, le=100.0)


class AutoscalingEvent(BaseModel):
    """Audit record capturing an automated scale-up, scale-down, or load-shedding event."""

    event_id: str
    timestamp: float = Field(default_factory=time.time)
    cluster_id: str
    action: AutoscalingAction
    reason: str
    node_id: str = ""
    trigger_metric: str = ""
    metric_value: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class EnclaveProvisionerPort(ABC):
    """Abstract port for spinning up and tearing down ephemeral compute micro-enclaves."""

    @abstractmethod
    async def provision_ephemeral_enclave(
        self,
        cluster_id: str,
        template: dict[str, Any] | None = None,
    ) -> MeshPeerNode:
        """Provision and launch a new ephemeral compute enclave in the specified cluster."""
        ...

    @abstractmethod
    async def terminate_ephemeral_enclave(self, node_id: str) -> bool:
        """Gracefully terminate an ephemeral enclave and de-allocate its compute resources."""
        ...


class MeshPeerNode(BaseModel):
    """Identity, network location, and advertised capabilities of a mesh peer."""

    node_id: str
    cluster_id: str
    endpoint_url: str
    role: MeshNodeRole = MeshNodeRole.SOVEREIGN_NODE
    status: MeshNodeStatus = MeshNodeStatus.ONLINE
    advertised_tools: list[McpToolDefinition] = Field(default_factory=list)
    latency_ms: float = Field(default=10.0, ge=0.0)
    last_heartbeat: float = Field(default_factory=time.time)
    capacity: NodeCapacityMetrics = Field(default_factory=NodeCapacityMetrics)
    public_key_fingerprint: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeshToolCallPayload(BaseModel):
    """Payload for executing a tool across cluster boundaries."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str
    source_cluster_id: str
    target_cluster_id: str
    trust_envelope: TrustEnvelope | None = None


class FederatedDelegationRequest(BaseModel):
    """Structured request delegating a reasoning sub-goal to a remote cluster agent."""

    delegation_id: str
    source_cluster_id: str
    target_cluster_id: str
    tenant_id: str
    initiator_agent_role: str = "planner"
    target_agent_role: str = "forensic_auditor"
    intent: str
    context_scope: dict[str, Any] = Field(default_factory=dict)
    max_depth: int = Field(default=2, ge=1, le=3)
    visited_clusters: list[str] = Field(default_factory=list)
    trust_envelope: TrustEnvelope | None = None


class FederatedDelegationResponse(BaseModel):
    """Verifiable synthesis and execution trace returned from remote cluster sub-agent."""

    delegation_id: str
    status: FederatedTaskStatus
    source_cluster_id: str
    target_cluster_id: str
    tenant_id: str
    synthesis: str
    tool_trace_summary: list[dict[str, Any]] = Field(default_factory=list)
    execution_latency_ms: float = 0.0
    signature: str = ""
    error_message: str | None = None


class MeshStatusSummary(BaseModel):
    """Platform Battery #30 health check and topology overview."""

    battery_id: str = "distributed_mcp_mesh"
    status: str = "active"
    total_nodes: int
    active_nodes: int
    total_mesh_tools: int
    routing_policy: MeshRoutingPolicy
    nodes: list[MeshPeerNode] = Field(default_factory=list)
