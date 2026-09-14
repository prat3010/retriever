"""Decentralized Model Context Protocol (MCP) Mesh Service (M115).

Conforms strictly to Hexagonal Architecture boundaries:
- Pure Python and standard library cryptography (hashlib, hmac).
- Zero web framework or database dependencies.
- Enforces dynamic capability advertisement, latency-weighted routing,
  and HMAC-SHA256 mutual trust verification with nonce replay protection.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any
from uuid import uuid4

from src.domain.abstractions.exceptions import (
    MeshNodeUnreachableError,
    TrustVerificationError,
)
from src.domain.abstractions.mcp import McpToolDefinition
from src.domain.abstractions.mcp_mesh import (
    MeshNodeRole,
    MeshNodeStatus,
    MeshPeerNode,
    MeshRoutingPolicy,
    MeshStatusSummary,
    TrustEnvelope,
)

logger = logging.getLogger(__name__)

# Default internal cluster shared secret for HMAC trust verification
DEFAULT_CLUSTER_SECRET = "retriever_mcp_mesh_internal_trust_key_v1"


def _canonical_json(data: dict[str, Any]) -> bytes:
    """Deterministic canonical JSON serialization for signature calculation."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


class McpMeshService:
    """Pure domain service managing decentralized MCP peer nodes, routing, and trust."""

    def __init__(
        self,
        local_node_id: str = "node_local_primary",
        local_cluster_id: str = "cluster_local_seed",
        endpoint_url: str = "http://localhost:8000",
        cluster_secret: str = DEFAULT_CLUSTER_SECRET,
        default_policy: MeshRoutingPolicy = MeshRoutingPolicy.LOCAL_FIRST,
    ) -> None:
        self.local_node_id = local_node_id
        self.local_cluster_id = local_cluster_id
        self.cluster_secret = cluster_secret
        self.default_policy = default_policy

        # In-memory registry of peer nodes: node_id -> MeshPeerNode
        self._nodes: dict[str, MeshPeerNode] = {}

        # Nonce replay prevention: nonce -> expiration_timestamp
        self._nonce_cache: dict[str, float] = {}

        # Register local node as primary seed gateway
        self._register_local_node(endpoint_url)

    def _register_local_node(self, endpoint_url: str) -> None:
        local_node = MeshPeerNode(
            node_id=self.local_node_id,
            cluster_id=self.local_cluster_id,
            endpoint_url=endpoint_url,
            role=MeshNodeRole.SEED_GATEWAY,
            status=MeshNodeStatus.ONLINE,
            latency_ms=1.0,
            last_heartbeat=time.time(),
            public_key_fingerprint=hashlib.sha256(self.local_node_id.encode()).hexdigest()[:16],
            metadata={"is_local": True},
        )
        self._nodes[self.local_node_id] = local_node

    @property
    def local_node(self) -> MeshPeerNode:
        """Return the local node representation."""
        return self._nodes[self.local_node_id]

    def update_local_tools(self, tools: list[McpToolDefinition]) -> None:
        """Update advertised capabilities for the local node."""
        if self.local_node_id in self._nodes:
            self._nodes[self.local_node_id].advertised_tools = tools

    def register_node(self, node: MeshPeerNode) -> MeshPeerNode:
        """Register or update a peer node in the mesh catalog."""
        node.last_heartbeat = time.time()
        self._nodes[node.node_id] = node
        logger.info(
            f"Registered MCP mesh peer '{node.node_id}' in cluster '{node.cluster_id}' "
            f"advertising {len(node.advertised_tools)} tools (latency: {node.latency_ms}ms)"
        )
        return node

    def unregister_node(self, node_id: str) -> bool:
        """Remove a node from the mesh catalog (cannot unregister local primary)."""
        if node_id == self.local_node_id:
            return False
        return self._nodes.pop(node_id, None) is not None

    def heartbeat(self, node_id: str, latency_ms: float | None = None) -> MeshPeerNode | None:
        """Process peer heartbeat, refresh liveness lease, and optionally update latency."""
        node = self._nodes.get(node_id)
        if not node:
            return None
        node.last_heartbeat = time.time()
        node.status = MeshNodeStatus.ONLINE
        if latency_ms is not None:
            node.latency_ms = max(0.1, latency_ms)
        return node

    def list_nodes(
        self,
        status_filter: MeshNodeStatus | None = None,
        online_only: bool = False,
    ) -> list[MeshPeerNode]:
        """List registered peer nodes, optionally filtered by health status."""
        self.evict_stale_nodes()
        if online_only or status_filter == MeshNodeStatus.ONLINE:
            return [n for n in self._nodes.values() if n.status == MeshNodeStatus.ONLINE]
        if status_filter:
            return [n for n in self._nodes.values() if n.status == status_filter]
        return list(self._nodes.values())

    def get_node(self, node_id: str) -> MeshPeerNode | None:
        """Retrieve a specific peer node by ID."""
        return self._nodes.get(node_id)

    def list_mesh_tools(self) -> list[McpToolDefinition]:
        """Aggregate unique advertised tools across all online mesh nodes."""
        self.evict_stale_nodes()
        unique_tools: dict[str, McpToolDefinition] = {}
        for node in self._nodes.values():
            if node.status in (MeshNodeStatus.ONLINE, MeshNodeStatus.DEGRADED):
                for tool in node.advertised_tools:
                    if tool.name not in unique_tools:
                        unique_tools[tool.name] = tool
        return list(unique_tools.values())

    def resolve_tool_route(
        self,
        tool_name: str,
        policy: MeshRoutingPolicy | None = None,
    ) -> MeshPeerNode:
        """Determine the optimal execution node for a tool according to routing policy."""
        self.evict_stale_nodes()
        effective_policy = policy or self.default_policy

        # Check local node first if policy is LOCAL_FIRST
        if effective_policy == MeshRoutingPolicy.LOCAL_FIRST:
            local = self._nodes.get(self.local_node_id)
            if local and any(t.name == tool_name for t in local.advertised_tools):
                return local

        # Collect candidate online nodes that advertise this tool
        candidates = [
            n for n in self._nodes.values()
            if n.status in (MeshNodeStatus.ONLINE, MeshNodeStatus.DEGRADED)
            and any(t.name == tool_name for t in n.advertised_tools)
        ]

        if not candidates:
            raise MeshNodeUnreachableError(
                f"No online mesh peer currently advertises capability '{tool_name}'."
            )

        if effective_policy == MeshRoutingPolicy.LOAD_BALANCED_EWMA:
            # Sort candidates by composite load score: EWMA * (1 + queue_depth) * (1 + active/max)
            candidates.sort(
                key=lambda n: (
                    n.capacity.ewma_latency_ms
                    * (1.0 + float(n.capacity.queue_depth))
                    * (1.0 + (n.capacity.active_execution_slots / max(1, n.capacity.max_execution_slots)))
                    * (1.0 if n.status == MeshNodeStatus.ONLINE else 10.0)
                )
            )
            return candidates[0]

        if effective_policy in (MeshRoutingPolicy.LOWEST_LATENCY, MeshRoutingPolicy.LOCAL_FIRST):
            # Pick node with lowest latency
            candidates.sort(key=lambda n: n.latency_ms)
            return candidates[0]

        # Round-robin or first available fallback
        return candidates[0]

    def create_trust_envelope(
        self,
        sender_cluster_id: str,
        receiver_cluster_id: str,
        tenant_id: str,
        payload_data: dict[str, Any],
    ) -> TrustEnvelope:
        """Generate a cryptographically signed HMAC-SHA256 trust envelope."""
        nonce = uuid4().hex
        ts = time.time()
        payload_bytes = _canonical_json(payload_data)
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Compute HMAC signature over canonical context
        signing_content = (
            f"{sender_cluster_id}:{receiver_cluster_id}:{tenant_id}:{nonce}:{ts:.4f}:{payload_hash}"
        ).encode()
        signature = hmac.new(
            self.cluster_secret.encode("utf-8"),
            signing_content,
            hashlib.sha256,
        ).hexdigest()

        return TrustEnvelope(
            sender_cluster_id=sender_cluster_id,
            receiver_cluster_id=receiver_cluster_id,
            tenant_id=tenant_id,
            timestamp=ts,
            nonce=nonce,
            signature=signature,
            payload_hash=payload_hash,
        )

    def verify_trust_envelope(
        self,
        envelope: TrustEnvelope,
        payload_data: dict[str, Any],
        max_skew_seconds: float = 60.0,
    ) -> bool:
        """Validate cryptographic HMAC signature and nonce replay protection."""
        now = time.time()

        # 1. Verify clock skew
        if abs(now - envelope.timestamp) > max_skew_seconds:
            raise TrustVerificationError(
                f"Trust envelope expired or clock skew exceeded ({abs(now - envelope.timestamp):.1f}s > {max_skew_seconds}s)."
            )

        # 2. Nonce replay check
        self._prune_nonces(now, max_skew_seconds)
        if envelope.nonce in self._nonce_cache:
            raise TrustVerificationError(
                f"Replay attack detected: nonce '{envelope.nonce}' has already been processed."
            )
        self._nonce_cache[envelope.nonce] = envelope.timestamp + max_skew_seconds

        # 3. Payload hash integrity
        payload_bytes = _canonical_json(payload_data)
        expected_hash = hashlib.sha256(payload_bytes).hexdigest()
        if not hmac.compare_digest(envelope.payload_hash, expected_hash):
            raise TrustVerificationError("Payload integrity hash mismatch.")

        # 4. HMAC signature verification
        signing_content = (
            f"{envelope.sender_cluster_id}:{envelope.receiver_cluster_id}:{envelope.tenant_id}:"
            f"{envelope.nonce}:{envelope.timestamp:.4f}:{expected_hash}"
        ).encode()
        expected_sig = hmac.new(
            self.cluster_secret.encode("utf-8"),
            signing_content,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(envelope.signature, expected_sig):
            raise TrustVerificationError("Invalid cryptographic HMAC-SHA256 signature.")

        return True

    def _prune_nonces(self, now: float, window: float) -> None:
        """Prune expired nonces from sliding window memory."""
        expired = [nonce for nonce, exp in self._nonce_cache.items() if exp < now]
        for nonce in expired:
            self._nonce_cache.pop(nonce, None)

    def evict_stale_nodes(self, timeout_seconds: float = 120.0) -> int:
        """Mark nodes with elapsed heartbeat leases as UNREACHABLE."""
        now = time.time()
        evicted = 0
        for nid, node in self._nodes.items():
            if nid == self.local_node_id:
                continue
            if node.status == MeshNodeStatus.ONLINE and (now - node.last_heartbeat) > timeout_seconds:
                node.status = MeshNodeStatus.UNREACHABLE
                evicted += 1
        return evicted

    def get_mesh_summary(self) -> MeshStatusSummary:
        """Compile live Platform Battery #30 health check summary."""
        self.evict_stale_nodes()
        nodes = list(self._nodes.values())
        active = sum(1 for n in nodes if n.status in (MeshNodeStatus.ONLINE, MeshNodeStatus.DEGRADED))
        total_tools = len(self.list_mesh_tools())
        return MeshStatusSummary(
            battery_id="distributed_mcp_mesh",
            status="active",
            total_nodes=len(nodes),
            active_nodes=active,
            total_mesh_tools=total_tools,
            routing_policy=self.default_policy,
            nodes=nodes,
        )
