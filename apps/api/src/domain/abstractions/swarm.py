"""Domain Abstractions for Autonomous Edge Fleet Swarm Mesh & P2P Gossip Replication (M102).

Pure domain layer with zero infrastructure or framework imports.
Defines contracts for:
- Lamport Vector Clocks with causal happened-before and concurrent conflict comparisons
- Structured Weakly-Consistent Infection-Style (SWIM) failure detection states
- Epidemic peer gossip message dissemination and incarnation refutation
- Push-pull anti-entropy sequence exchange and SQLite delta synchronization
- Partition-healing state reconciliation across disconnected edge clusters
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SwarmNodeRole(StrEnum):
    """Hierarchical operational role of an edge node in the swarm mesh."""

    SEED_LEADER = "seed_leader"
    CORE_PEER = "core_peer"
    EDGE_LEAF = "edge_leaf"
    PARTITION_MEMBER = "partition_member"


class SwarmNodeState(StrEnum):
    """Operational liveness state under the SWIM failure detection protocol."""

    HEALTHY = "healthy"
    SUSPECT = "suspect"
    DEAD = "dead"
    LEFT = "left"


class GossipMessageType(StrEnum):
    """Types of epidemic gossip messages exchanged between swarm peers."""

    PING = "ping"
    ACK = "ack"
    PING_REQ = "ping_req"
    SUSPECT = "suspect"
    ALIVE = "alive"
    DEAD = "dead"
    ANTI_ENTROPY = "anti_entropy"
    PARTITION_MERGE = "partition_merge"


class VectorClockComparison(StrEnum):
    """Causal relationship between two vector clocks."""

    BEFORE = "before"
    AFTER = "after"
    IDENTICAL = "identical"
    CONCURRENT = "concurrent"


class VectorClock(BaseModel):
    """Lamport Vector Clock tracking causal event ordering across swarm peers."""

    clock: dict[str, int] = Field(default_factory=dict)

    def tick(self, node_id: str) -> None:
        """Increment monotonic counter for the specified local node."""
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def get(self, node_id: str) -> int:
        """Get the current logical sequence counter for a node."""
        return self.clock.get(node_id, 0)

    def merge(self, other: "VectorClock") -> None:
        """Merge another vector clock by taking the pairwise maximum of all counters."""
        for nid, val in other.clock.items():
            self.clock[nid] = max(self.clock.get(nid, 0), val)

    def compare(self, other: "VectorClock") -> VectorClockComparison:
        """Determine causal relationship with another vector clock.

        Returns:
            BEFORE if self strictly happened-before other.
            AFTER if self strictly happened-after other.
            IDENTICAL if both clocks are equal.
            CONCURRENT if causal branches diverged concurrently (conflict).
        """
        all_keys = set(self.clock.keys()) | set(other.clock.keys())
        if not all_keys:
            return VectorClockComparison.IDENTICAL

        has_less = False
        has_greater = False

        for k in all_keys:
            v_self = self.clock.get(k, 0)
            v_other = other.clock.get(k, 0)
            if v_self < v_other:
                has_less = True
            elif v_self > v_other:
                has_greater = True

        if not has_less and not has_greater:
            return VectorClockComparison.IDENTICAL
        if has_less and not has_greater:
            return VectorClockComparison.BEFORE
        if has_greater and not has_less:
            return VectorClockComparison.AFTER
        return VectorClockComparison.CONCURRENT

    def to_dict(self) -> dict[str, int]:
        return dict(self.clock)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "VectorClock":
        return cls(clock={str(k): int(v) for k, v in data.items()})


class SwarmNode(BaseModel):
    """Registered peer node within the decentralized edge swarm mesh."""

    node_id: str = Field(..., description="Unique client machine/device identifier")
    tenant_id: str = Field(..., description="Scoped tenant UUID")
    device_name: str = Field(..., description="Human-readable device alias")
    role: SwarmNodeRole = Field(default=SwarmNodeRole.CORE_PEER)
    state: SwarmNodeState = Field(default=SwarmNodeState.HEALTHY)
    address: str = Field(default="127.0.0.1", description="IP address or hostname")
    port: int = Field(default=7946, description="Gossip listener port")
    incarnation: int = Field(default=0, description="Monotonic incarnation number for refuting suspect rumors")
    vector_clock: VectorClock = Field(default_factory=VectorClock)
    rtt_ms: float = Field(default=5.0, description="Observed round-trip ping latency in milliseconds")
    last_heartbeat_at: datetime = Field(default_factory=_utc_now)
    last_state_change_at: datetime = Field(default_factory=_utc_now)
    suspect_by_node_id: str | None = Field(default=None, description="Node that originated suspicion")
    meta_data: dict[str, Any] = Field(default_factory=dict)


class GossipMessage(BaseModel):
    """Epidemic gossip message packet propagated across swarm nodes."""

    message_id: str = Field(..., description="Unique message UUID")
    msg_type: GossipMessageType
    sender_id: str
    target_id: str | None = Field(default=None, description="Target peer if direct or ping-req; None if broadcast")
    tenant_id: str
    incarnation: int = Field(default=0)
    vector_clock: VectorClock = Field(default_factory=VectorClock)
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class AntiEntropyDigest(BaseModel):
    """Digest of local sequence numbers and vector clocks exchanged during push-pull sync."""

    sender_id: str
    tenant_id: str
    vector_clock: VectorClock = Field(default_factory=VectorClock)
    highest_sequence: int = 0
    chunk_checksums: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=_utc_now)


class AntiEntropySyncResult(BaseModel):
    """Result of an anti-entropy synchronization exchange."""

    sender_id: str
    target_id: str
    tenant_id: str
    missing_sequences: list[int] = Field(default_factory=list)
    missing_chunk_ids: list[str] = Field(default_factory=list)
    replayed_mutations_count: int = 0
    converged_clock: VectorClock = Field(default_factory=VectorClock)
    is_converged: bool = True
    synchronized_at: datetime = Field(default_factory=_utc_now)


class PartitionReconciliationReport(BaseModel):
    """Report generated when two disconnected network partitions merge and reconcile."""

    tenant_id: str
    partition_a_nodes: list[str] = Field(default_factory=list)
    partition_b_nodes: list[str] = Field(default_factory=list)
    clock_a: VectorClock = Field(default_factory=VectorClock)
    clock_b: VectorClock = Field(default_factory=VectorClock)
    comparison: VectorClockComparison
    conflicts_detected: int = 0
    conflicts_resolved_via_lww: int = 0
    mutations_replayed: int = 0
    merged_clock: VectorClock = Field(default_factory=VectorClock)
    reconciled_at: datetime = Field(default_factory=_utc_now)


class SwarmTopology(BaseModel):
    """System-wide view of swarm mesh cluster membership and telemetry."""

    tenant_id: str
    total_nodes: int = 0
    active_healthy_count: int = 0
    suspect_count: int = 0
    dead_count: int = 0
    left_count: int = 0
    cluster_convergence_pct: float = 100.0
    average_rtt_ms: float = 0.0
    generation: int = 1
    nodes: list[SwarmNode] = Field(default_factory=list)


class SwarmMeshProtocol(Protocol):
    """Abstract protocol for autonomous edge fleet swarm mesh operations."""

    def register_node(self, node: SwarmNode) -> SwarmNode:
        """Register a new peer into the swarm mesh."""
        ...

    def deregister_node(self, tenant_id: str, node_id: str) -> bool:
        """Mark a node as gracefully left the swarm mesh."""
        ...

    def handle_gossip(self, message: GossipMessage) -> GossipMessage | None:
        """Process an inbound epidemic gossip message and update state."""
        ...

    def probe_node_swim(
        self,
        tenant_id: str,
        prober_node_id: str,
        target_node_id: str,
        simulated_ack: bool = True,
    ) -> SwarmNode:
        """Execute a SWIM direct ping or indirect ping-req probe."""
        ...

    def sync_anti_entropy(
        self,
        tenant_id: str,
        sender_id: str,
        target_id: str,
        digest: AntiEntropyDigest,
        target_sequences: list[int] | None = None,
    ) -> AntiEntropySyncResult:
        """Execute push-pull anti-entropy delta synchronization."""
        ...

    def reconcile_partitions(
        self,
        tenant_id: str,
        partition_a_nodes: list[str],
        partition_b_nodes: list[str],
        mutations_a: list[dict[str, Any]] | None = None,
        mutations_b: list[dict[str, Any]] | None = None,
    ) -> PartitionReconciliationReport:
        """Merge disconnected partitions using vector clocks and causal conflict resolution."""
        ...

    def get_topology(self, tenant_id: str) -> SwarmTopology:
        """Retrieve current swarm topology and telemetry."""
        ...
