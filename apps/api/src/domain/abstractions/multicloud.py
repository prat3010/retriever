"""Domain Abstractions for Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication (M99).

Defines pure domain entities, enums, data models, and abstract protocols for:
- Multi-cloud cluster topology and region node status
- Active-active quorum consensus and leader election
- Automated circuit breaker and latency-driven failover
- Embedded Turso / LibSQL replica synchronization and WAL streaming
- Local read routing (<1ms) and write proxying to active leader

Strictly Hexagonal: Zero database, ORM, or web framework imports.
"""

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class CloudRegion(StrEnum):
    """Supported multi-cloud geographic regions."""

    OCI_BOM = "oci-bom"  # Oracle Cloud Mumbai (Primary Cloud VPS)
    AWS_IAD = "aws-iad"  # AWS US-East Northern Virginia (Secondary Hot Standby)
    FLY_FRA = "fly-fra"  # Fly.io Frankfurt (European Edge Cluster)
    CF_GLOBAL = "cf-global"  # Cloudflare Global Anycast Edge Network


class ClusterNodeRole(StrEnum):
    """Operational role of a node within the multi-cloud cluster."""

    PRIMARY_LEADER = "primary_leader"
    STANDBY_REPLICA = "standby_replica"
    EDGE_FOLLOWER = "edge_follower"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class FailoverTriggerType(StrEnum):
    """Trigger source initiating a cluster leader failover."""

    AUTOMATIC_HEALTH_CHECK = "automatic_health_check"
    LATENCY_THRESHOLD_EXCEEDED = "latency_threshold_exceeded"
    MANUAL_OPERATOR_OVERRIDE = "manual_operator_override"
    SIMULATED_CHAOS_TEST = "simulated_chaos_test"


class ReplicationEngineType(StrEnum):
    """Database replication driver engine."""

    LIBSQL_EMBEDDED = "libsql_embedded"
    PG_LOGICAL_STREAM = "pg_logical_stream"
    SQLITE_STANDALONE_FALLBACK = "sqlite_standalone_fallback"


class QuorumState(StrEnum):
    """Quorum consensus status for leader election."""

    CONSENSUS_REACHED = "consensus_reached"
    QUORUM_LOST = "quorum_lost"
    SPLIT_BRAIN_AVOIDED = "split_brain_avoided"
    ELECTION_IN_PROGRESS = "election_in_progress"


class CloudRegionNode(BaseModel):
    """Registered node or region within the distributed multi-cloud topology."""

    node_id: str
    cloud_provider: str = "oracle"  # "oracle", "aws", "fly_io", "cloudflare"
    region: CloudRegion = CloudRegion.OCI_BOM
    endpoint_url: str
    role: ClusterNodeRole = ClusterNodeRole.STANDBY_REPLICA
    is_voting_member: bool = True
    priority_weight: int = 100  # Higher weight preferred for leader election
    latency_ms: float = 12.0
    consecutive_failures: int = 0
    last_heartbeat_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.role not in (ClusterNodeRole.DEGRADED, ClusterNodeRole.OFFLINE) and self.consecutive_failures == 0


class RegionHealthProbe(BaseModel):
    """Point-in-time health probe result for a cloud region."""

    node_id: str
    region: CloudRegion
    probe_url: str
    latency_ms: float
    status_code: int = 200
    is_healthy: bool = True
    failure_reason: str | None = None
    probed_at: str
    is_simulated: bool = False  # Explicitly labeled in dev/test environments


class ClusterTopology(BaseModel):
    """Full-spectrum distributed multi-cloud topology state."""

    cluster_id: str = "retriever-global-mesh"
    active_leader_region: CloudRegion = CloudRegion.OCI_BOM
    active_leader_node_id: str = "node-oci-bom-01"
    generation_term: int = 1  # Raft-inspired monotonic generation counter
    total_nodes: int = 4
    healthy_nodes: int = 4
    quorum_state: QuorumState = QuorumState.CONSENSUS_REACHED
    nodes: list[CloudRegionNode] = Field(default_factory=list)
    last_failover_at: str | None = None
    last_failover_reason: str | None = None
    environment_mode: str = "hybrid_testnet"  # "production_live" or "hybrid_testnet"

    @property
    def has_quorum(self) -> bool:
        voting_nodes = [n for n in self.nodes if n.is_voting_member]
        if not voting_nodes:
            return False
        healthy_voting = [n for n in voting_nodes if n.is_healthy]
        return (len(healthy_voting) / len(voting_nodes)) > 0.5


class FailoverRequest(BaseModel):
    """Payload to trigger or simulate a cluster leader transition."""

    target_region: CloudRegion
    reason: str = "Manual operator traffic diversion"
    trigger_type: FailoverTriggerType = FailoverTriggerType.MANUAL_OPERATOR_OVERRIDE
    force: bool = False
    operator_id: str = "admin"


class FailoverResult(BaseModel):
    """Outcome of a leader election or failover execution."""

    success: bool
    old_leader: CloudRegion
    new_leader: CloudRegion
    generation_term: int
    duration_ms: float
    quorum_votes_acquired: int
    total_voting_nodes: int
    quorum_state: QuorumState
    message: str
    audit_event_id: str


class LibsqlReplicaConfig(BaseModel):
    """Configuration credentials for a tenant or edge embedded LibSQL replica."""

    tenant_id: str
    primary_url: str
    replica_url: str
    auth_token: str
    sync_interval_seconds: int = 10
    read_local: bool = True
    write_proxy_to_primary: bool = True
    db_file_path: str = "retriever_edge_replica.db"
    replication_engine: ReplicationEngineType = ReplicationEngineType.LIBSQL_EMBEDDED


class LibsqlReplicationStats(BaseModel):
    """Real-time LibSQL WAL streaming and replication lag metrics."""

    tenant_id: str
    primary_wal_frame: int = 1048
    local_wal_frame: int = 1048
    replication_lag_frames: int = 0
    replication_lag_ms: float = 0.8
    sync_status: str = "synced"  # "synced", "catching_up", "lagging", "disconnected"
    last_synced_at: str = ""
    is_embedded: bool = True
    writes_forwarded: int = 0
    reads_served_locally: int = 0


# ---------------------------------------------------------------------------
# Abstract Protocols (Ports)
# ---------------------------------------------------------------------------


class MultiCloudHealthProbeProtocol(Protocol):
    """Abstract protocol for executing multi-cloud liveness & latency probes."""

    async def probe_node(self, node: CloudRegionNode) -> RegionHealthProbe: ...

    async def probe_all_regions(self, nodes: list[CloudRegionNode]) -> list[RegionHealthProbe]: ...


class FailoverControllerProtocol(Protocol):
    """Abstract protocol for cluster state evaluation and failover execution."""

    async def evaluate_topology(self) -> ClusterTopology: ...

    async def execute_failover(self, request: FailoverRequest) -> FailoverResult: ...

    async def record_heartbeat(self, node_id: str, latency_ms: float, is_healthy: bool) -> None: ...


class LibsqlReplicationProtocol(Protocol):
    """Abstract protocol for Turso / LibSQL embedded replica management."""

    def get_replica_config(self, tenant_id: str) -> LibsqlReplicaConfig: ...

    async def sync_replica(self, tenant_id: str) -> LibsqlReplicationStats: ...

    async def get_replication_stats(self, tenant_id: str) -> LibsqlReplicationStats: ...
