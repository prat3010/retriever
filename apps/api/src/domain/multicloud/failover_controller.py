"""Domain Service for Multi-Cloud Cluster State & Quorum Failover (M99).

Pure domain logic implementing:
- Quorum-based leader election (>50% majority consensus)
- Split-brain defense under network partitions
- Exponential Weighted Moving Average (EWMA) latency smoothing
- Automated circuit-breaker trigger on consecutive health probe failures
- Monotonic generation term incrementation and audit trail tracking

Strictly Hexagonal: Zero framework or database imports.
"""

import time
import uuid
from datetime import UTC, datetime

from src.domain.abstractions.multicloud import (
    CloudRegion,
    CloudRegionNode,
    ClusterNodeRole,
    ClusterTopology,
    FailoverRequest,
    FailoverResult,
    FailoverTriggerType,
    QuorumState,
    RegionHealthProbe,
)


class FailoverController:
    """Pure domain service orchestrating multi-cloud leader election and failover."""

    def __init__(
        self,
        cluster_id: str = "retriever-global-mesh",
        failover_threshold_failures: int = 3,
        latency_threshold_ms: float = 1500.0,
        ewma_alpha: float = 0.3,
        environment_mode: str = "hybrid_testnet",
    ) -> None:
        self.cluster_id = cluster_id
        self.failover_threshold_failures = failover_threshold_failures
        self.latency_threshold_ms = latency_threshold_ms
        self.ewma_alpha = ewma_alpha
        self.environment_mode = environment_mode

        self.generation_term = 1
        self.active_leader_region = CloudRegion.OCI_BOM
        self.active_leader_node_id = "node-oci-bom-01"
        self.last_failover_at: str | None = None
        self.last_failover_reason: str | None = None

        # Initialize default multi-cloud topology
        self.nodes: dict[str, CloudRegionNode] = self._build_default_nodes()

    def _build_default_nodes(self) -> dict[str, CloudRegionNode]:
        now_str = datetime.now(UTC).isoformat()
        return {
            "node-oci-bom-01": CloudRegionNode(
                node_id="node-oci-bom-01",
                cloud_provider="oracle",
                region=CloudRegion.OCI_BOM,
                endpoint_url="https://rag.prateeq.in",
                role=ClusterNodeRole.PRIMARY_LEADER,
                is_voting_member=True,
                priority_weight=100,
                latency_ms=12.0,
                consecutive_failures=0,
                last_heartbeat_at=now_str,
                metadata={"datacenter": "mumbai-1", "tier": "bare_metal_arm"},
            ),
            "node-aws-iad-01": CloudRegionNode(
                node_id="node-aws-iad-01",
                cloud_provider="aws",
                region=CloudRegion.AWS_IAD,
                endpoint_url="https://us-east.rag.prateeq.in",
                role=ClusterNodeRole.STANDBY_REPLICA,
                is_voting_member=True,
                priority_weight=90,
                latency_ms=184.0,
                consecutive_failures=0,
                last_heartbeat_at=now_str,
                metadata={"datacenter": "us-east-1", "tier": "ec2_c7g"},
            ),
            "node-fly-fra-01": CloudRegionNode(
                node_id="node-fly-fra-01",
                cloud_provider="fly_io",
                region=CloudRegion.FLY_FRA,
                endpoint_url="https://fra.rag.prateeq.in",
                role=ClusterNodeRole.STANDBY_REPLICA,
                is_voting_member=True,
                priority_weight=80,
                latency_ms=138.0,
                consecutive_failures=0,
                last_heartbeat_at=now_str,
                metadata={"datacenter": "fra-frankfurt", "tier": "performance_2x"},
            ),
            "node-cf-global-01": CloudRegionNode(
                node_id="node-cf-global-01",
                cloud_provider="cloudflare",
                region=CloudRegion.CF_GLOBAL,
                endpoint_url="https://edge.rag.prateeq.in",
                role=ClusterNodeRole.EDGE_FOLLOWER,
                is_voting_member=False,  # Edge follower does not vote in cloud quorum
                priority_weight=50,
                latency_ms=8.0,
                consecutive_failures=0,
                last_heartbeat_at=now_str,
                metadata={"network": "anycast_edge", "locations": 310},
            ),
        }

    def get_topology(self) -> ClusterTopology:
        """Returns the current multi-cloud topology with computed quorum state."""
        node_list = list(self.nodes.values())
        voting_nodes = [n for n in node_list if n.is_voting_member]
        healthy_voting = [n for n in voting_nodes if n.is_healthy]

        if not voting_nodes or (len(healthy_voting) / len(voting_nodes)) <= 0.5:
            quorum_state = QuorumState.QUORUM_LOST
        else:
            quorum_state = QuorumState.CONSENSUS_REACHED

        return ClusterTopology(
            cluster_id=self.cluster_id,
            active_leader_region=self.active_leader_region,
            active_leader_node_id=self.active_leader_node_id,
            generation_term=self.generation_term,
            total_nodes=len(node_list),
            healthy_nodes=sum(1 for n in node_list if n.is_healthy),
            quorum_state=quorum_state,
            nodes=node_list,
            last_failover_at=self.last_failover_at,
            last_failover_reason=self.last_failover_reason,
            environment_mode=self.environment_mode,
        )

    def record_probe_result(self, probe: RegionHealthProbe) -> FailoverResult | None:
        """Updates health status for a probed region and evaluates automated failover."""
        node = self.nodes.get(probe.node_id)
        if not node:
            return None

        # EWMA latency calculation
        node.latency_ms = round(
            (self.ewma_alpha * probe.latency_ms) + ((1.0 - self.ewma_alpha) * node.latency_ms),
            2,
        )
        node.last_heartbeat_at = probe.probed_at

        if probe.is_healthy:
            node.consecutive_failures = 0
            if node.role == ClusterNodeRole.DEGRADED:
                # Node recovered
                node.role = ClusterNodeRole.STANDBY_REPLICA
        else:
            node.consecutive_failures += 1
            if node.consecutive_failures >= self.failover_threshold_failures:
                node.role = ClusterNodeRole.DEGRADED

        # Trigger automatic failover if primary leader degraded
        if node.node_id == self.active_leader_node_id and not node.is_healthy:
            if node.consecutive_failures >= self.failover_threshold_failures or node.latency_ms > self.latency_threshold_ms:
                return self.execute_automated_failover(
                    reason=f"Primary leader {node.region} degraded after {node.consecutive_failures} failures (latency: {node.latency_ms}ms)",
                    trigger_type=FailoverTriggerType.AUTOMATIC_HEALTH_CHECK,
                )

        return None

    def execute_automated_failover(
        self,
        reason: str,
        trigger_type: FailoverTriggerType = FailoverTriggerType.AUTOMATIC_HEALTH_CHECK,
    ) -> FailoverResult:
        """Selects the best standby candidate and triggers failover."""
        candidates = [
            n
            for n in self.nodes.values()
            if n.node_id != self.active_leader_node_id and n.is_voting_member and n.is_healthy
        ]

        if not candidates:
            # Quorum lost: Cannot failover safely without candidates
            return FailoverResult(
                success=False,
                old_leader=self.active_leader_region,
                new_leader=self.active_leader_region,
                generation_term=self.generation_term,
                duration_ms=0.0,
                quorum_votes_acquired=0,
                total_voting_nodes=len([n for n in self.nodes.values() if n.is_voting_member]),
                quorum_state=QuorumState.QUORUM_LOST,
                message="Quorum lost: No healthy voting candidates available for leader election.",
                audit_event_id=f"failover-err-{uuid.uuid4().hex[:8]}",
            )

        # Select candidate with highest priority weight
        candidates.sort(key=lambda x: x.priority_weight, reverse=True)
        best_candidate = candidates[0]

        return self.execute_failover(
            FailoverRequest(
                target_region=best_candidate.region,
                reason=reason,
                trigger_type=trigger_type,
                force=False,
                operator_id="system_sentinel",
            )
        )

    def execute_failover(self, request: FailoverRequest) -> FailoverResult:
        """Executes a leader transition to the requested region with quorum enforcement."""
        start_time = time.perf_counter()
        voting_nodes = [n for n in self.nodes.values() if n.is_voting_member]
        total_voting = len(voting_nodes)

        # Find candidate node for target region
        target_nodes = [n for n in self.nodes.values() if n.region == request.target_region]
        if not target_nodes:
            return FailoverResult(
                success=False,
                old_leader=self.active_leader_region,
                new_leader=self.active_leader_region,
                generation_term=self.generation_term,
                duration_ms=0.0,
                quorum_votes_acquired=0,
                total_voting_nodes=total_voting,
                quorum_state=QuorumState.QUORUM_LOST,
                message=f"Target region '{request.target_region}' not found in cluster registry.",
                audit_event_id=f"failover-err-{uuid.uuid4().hex[:8]}",
            )

        target_node = target_nodes[0]
        old_leader_region = self.active_leader_region

        # Calculate quorum votes among healthy voting nodes
        healthy_voting = [n for n in voting_nodes if n.is_healthy or request.force]
        votes_acquired = len(healthy_voting)

        # Check majority consensus (>50%)
        if not request.force and (votes_acquired / total_voting) <= 0.5:
            return FailoverResult(
                success=False,
                old_leader=old_leader_region,
                new_leader=old_leader_region,
                generation_term=self.generation_term,
                duration_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                quorum_votes_acquired=votes_acquired,
                total_voting_nodes=total_voting,
                quorum_state=QuorumState.SPLIT_BRAIN_AVOIDED,
                message=f"Split-brain avoided: Failover rejected. Acquired {votes_acquired}/{total_voting} votes, requiring majority (>50%).",
                audit_event_id=f"failover-veto-{uuid.uuid4().hex[:8]}",
            )

        # Demote old leader
        old_leader_node = self.nodes.get(self.active_leader_node_id)
        if old_leader_node:
            old_leader_node.role = (
                ClusterNodeRole.STANDBY_REPLICA if old_leader_node.is_healthy else ClusterNodeRole.DEGRADED
            )

        # Promote new leader
        target_node.role = ClusterNodeRole.PRIMARY_LEADER
        self.active_leader_region = target_node.region
        self.active_leader_node_id = target_node.node_id
        self.generation_term += 1
        self.last_failover_at = datetime.now(UTC).isoformat()
        self.last_failover_reason = request.reason

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        audit_id = f"failover-evt-{uuid.uuid4().hex[:8]}"

        return FailoverResult(
            success=True,
            old_leader=old_leader_region,
            new_leader=self.active_leader_region,
            generation_term=self.generation_term,
            duration_ms=elapsed_ms,
            quorum_votes_acquired=votes_acquired,
            total_voting_nodes=total_voting,
            quorum_state=QuorumState.CONSENSUS_REACHED,
            message=f"Quorum consensus approved: Leader transitioned from {old_leader_region} to {self.active_leader_region} in {elapsed_ms}ms (Term {self.generation_term}).",
            audit_event_id=audit_id,
        )
