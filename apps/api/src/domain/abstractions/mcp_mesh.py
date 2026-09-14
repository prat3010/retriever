"""Domain Abstractions for Distributed Model Context Protocol (MCP) Mesh & Agent Federation (M115).

Conforms strictly to Hexagonal Architecture boundaries:
- Pure Pydantic models, StrEnums, and standard library typing.
- Zero infrastructure, framework, or database dependencies.
- Enforces mutual trust envelopes, loop detection, and multi-tenant isolation.
"""

from __future__ import annotations

import time
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
