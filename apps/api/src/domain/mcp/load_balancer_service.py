"""Pure Domain Service for MCP Mesh Load Balancing & Ephemeral Enclave Auto-Scaling (M116).

Conforms strictly to Hexagonal Architecture boundaries:
- Zero framework or external infrastructure dependencies.
- Implements Power-of-Two-Choices (P2C) algorithm minimizing composite load score.
- Implements Exponentially Weighted Moving Average (EWMA) latency decay.
- Evaluates autonomous scale-up, scale-to-zero reaping, and adaptive load shedding.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from typing import Any

from src.domain.abstractions.exceptions import (
    MeshLoadSheddingError,
    MeshNodeUnreachableError,
)
from src.domain.abstractions.mcp_mesh import (
    AutoscalingAction,
    AutoscalingEvent,
    AutoscalingPolicy,
    EnclaveProvisionerPort,
    MeshNodeRole,
    MeshNodeStatus,
    MeshPeerNode,
    NodeCapacityMetrics,
)
from src.domain.mcp.mesh_service import McpMeshService

logger = logging.getLogger(__name__)


class SovereignEnclaveProvisionerAdapter(EnclaveProvisionerPort):
    """In-process sovereign provisioner for spawning and terminating ephemeral enclaves."""

    def __init__(self, mesh_service: McpMeshService) -> None:
        self.mesh_service = mesh_service
        self._spawned_count = 0

    async def provision_ephemeral_enclave(
        self,
        cluster_id: str,
        template: dict[str, Any] | None = None,
    ) -> MeshPeerNode:
        self._spawned_count += 1
        node_id = f"ephemeral_enclave_{cluster_id}_{uuid.uuid4().hex[:8]}"
        enclave_node = MeshPeerNode(
            node_id=node_id,
            cluster_id=cluster_id,
            endpoint_url=f"http://127.0.0.1:{8100 + self._spawned_count}",
            role=MeshNodeRole.EDGE_ENCLAVE,
            status=MeshNodeStatus.ONLINE,
            advertised_tools=list(self.mesh_service.local_node.advertised_tools),
            latency_ms=2.0,
            capacity=NodeCapacityMetrics(
                cpu_utilization_pct=10.0,
                memory_utilization_pct=15.0,
                active_execution_slots=0,
                max_execution_slots=16,
                queue_depth=0,
                ewma_latency_ms=5.0,
                is_ephemeral=True,
                ephemeral_idle_seconds=0.0,
            ),
            metadata={"ephemeral": True, "created_at": time.time()},
        )
        self.mesh_service.register_node(enclave_node)
        logger.info(f"Provisioned ephemeral enclave '{node_id}' in cluster '{cluster_id}'")
        return enclave_node

    async def terminate_ephemeral_enclave(self, node_id: str) -> bool:
        success = self.mesh_service.unregister_node(node_id)
        if success:
            logger.info(f"Terminated ephemeral enclave '{node_id}'")
        return success


class MeshLoadBalancerService:
    """Domain service governing dynamic load balancing and scale-to-zero enclave autoscaling."""

    def __init__(
        self,
        mesh_service: McpMeshService,
        provisioner: EnclaveProvisionerPort | None = None,
        policy: AutoscalingPolicy | None = None,
        ewma_alpha: float = 0.2,
    ) -> None:
        self.mesh_service = mesh_service
        self.provisioner = provisioner or SovereignEnclaveProvisionerAdapter(mesh_service)
        self.policy = policy or AutoscalingPolicy()
        self.ewma_alpha = max(0.01, min(0.99, ewma_alpha))

        # In-memory audit trail of autoscaling events
        self._events: list[AutoscalingEvent] = []

    def get_policy(self) -> AutoscalingPolicy:
        """Return the active autoscaling thresholds."""
        return self.policy

    def update_policy(self, updated: AutoscalingPolicy) -> AutoscalingPolicy:
        """Update cluster autoscaling parameters."""
        self.policy = updated
        logger.info(f"Updated mesh autoscaling policy: {self.policy.model_dump()}")
        return self.policy

    def get_events(self, limit: int = 50) -> list[AutoscalingEvent]:
        """Return recent autoscaling and load-shedding events ordered newest first."""
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def record_event(self, event: AutoscalingEvent) -> None:
        """Record an autoscaling or shedding event in the audit ledger."""
        self._events.append(event)
        if len(self._events) > 500:
            self._events = self._events[-500:]

    def calculate_composite_load_score(self, node: MeshPeerNode) -> float:
        """Calculate composite load score using EWMA latency, queue depth, and slot saturation.

        Formula:
            LoadScore = EWMA * (1 + queue_depth) * (1 + (active_slots / max_slots))
        """
        cap = node.capacity
        active_ratio = cap.active_execution_slots / max(1, cap.max_execution_slots)
        queue_multiplier = 1.0 + float(cap.queue_depth)
        slot_multiplier = 1.0 + active_ratio
        base_latency = max(0.1, cap.ewma_latency_ms)

        # Penalize degraded or non-online nodes
        status_penalty = 1.0 if node.status == MeshNodeStatus.ONLINE else 10.0

        return round(base_latency * queue_multiplier * slot_multiplier * status_penalty, 3)

    def select_node_p2c(self, candidates: list[MeshPeerNode]) -> MeshPeerNode:
        """Select optimal execution node via Power-of-Two-Choices (P2C) algorithm."""
        if not candidates:
            raise MeshNodeUnreachableError("No candidate nodes available for load balancing.")

        if len(candidates) == 1:
            return candidates[0]

        # Sample two distinct candidate nodes at random
        sampled = random.sample(candidates, 2)
        node_a, node_b = sampled[0], sampled[1]

        score_a = self.calculate_composite_load_score(node_a)
        score_b = self.calculate_composite_load_score(node_b)

        winner = node_a if score_a <= score_b else node_b
        logger.debug(
            f"P2C selection between '{node_a.node_id}' ({score_a}) vs "
            f"'{node_b.node_id}' ({score_b}) -> Winner: '{winner.node_id}'"
        )
        return winner

    def resolve_load_balanced_route(
        self,
        tool_name: str,
        cluster_id: str | None = None,
    ) -> MeshPeerNode:
        """Resolve the optimal node advertising tool_name under EWMA load-balanced policy."""
        # Query active online nodes from the mesh directory
        all_nodes = self.mesh_service.list_nodes(online_only=True)

        # Filter nodes by tool capability and optional cluster scope
        matching_nodes: list[MeshPeerNode] = []
        for n in all_nodes:
            if cluster_id and n.cluster_id != cluster_id:
                continue
            for tool in n.advertised_tools:
                if tool.name == tool_name:
                    matching_nodes.append(n)
                    break

        if not matching_nodes:
            raise MeshNodeUnreachableError(
                f"No reachable peer node in mesh advertises tool '{tool_name}'"
                + (f" for cluster '{cluster_id}'." if cluster_id else ".")
            )

        # Check for global saturation across all matching candidate nodes
        all_saturated = True
        for n in matching_nodes:
            utilization = (n.capacity.active_execution_slots / max(1, n.capacity.max_execution_slots)) * 100.0
            if utilization < self.policy.load_shedding_threshold_pct:
                all_saturated = False
                break

        if all_saturated:
            # Emit load-shedding event
            event = AutoscalingEvent(
                event_id=f"evt_shed_{uuid.uuid4().hex[:8]}",
                timestamp=time.time(),
                cluster_id=cluster_id or "global_mesh",
                action=AutoscalingAction.SHED_LOAD,
                reason=f"All {len(matching_nodes)} nodes advertising '{tool_name}' exceed {self.policy.load_shedding_threshold_pct}% saturation.",
                trigger_metric="slot_utilization_pct",
                metric_value=100.0,
            )
            self.record_event(event)
            raise MeshLoadSheddingError(
                f"Mesh cluster saturated: all nodes for '{tool_name}' exceeded "
                f"{self.policy.load_shedding_threshold_pct}% load-shedding threshold."
            )

        return self.select_node_p2c(matching_nodes)

    def acquire_slot(self, node_id: str) -> None:
        """Reserve a concurrent execution slot on the selected node."""
        node = self.mesh_service.get_node(node_id)
        if not node:
            return

        node.capacity.active_execution_slots += 1
        if node.capacity.is_ephemeral:
            node.capacity.ephemeral_idle_seconds = 0.0

        if node.capacity.active_execution_slots > node.capacity.max_execution_slots:
            node.capacity.queue_depth += 1

    def release_slot(self, node_id: str, sample_latency_ms: float) -> None:
        """Release an execution slot and update the Exponentially Weighted Moving Average (EWMA) latency."""
        node = self.mesh_service.get_node(node_id)
        if not node:
            return

        # Decrement active slots safely
        node.capacity.active_execution_slots = max(0, node.capacity.active_execution_slots - 1)
        if node.capacity.queue_depth > 0:
            node.capacity.queue_depth -= 1

        # Update EWMA latency
        # EWMA_t = alpha * Sample + (1 - alpha) * EWMA_{t-1}
        prev_ewma = node.capacity.ewma_latency_ms
        new_ewma = (self.ewma_alpha * sample_latency_ms) + ((1.0 - self.ewma_alpha) * prev_ewma)
        node.capacity.ewma_latency_ms = round(new_ewma, 2)

    def update_node_telemetry(
        self,
        node_id: str,
        metrics: NodeCapacityMetrics,
    ) -> MeshPeerNode:
        """Update live telemetry reported by an edge node heartbeat."""
        node = self.mesh_service.get_node(node_id)
        if not node:
            raise MeshNodeUnreachableError(f"Node '{node_id}' not found in mesh registry.")

        node.capacity = metrics
        node.last_heartbeat = time.time()
        return node

    async def evaluate_autoscaling(self, cluster_id: str) -> list[AutoscalingEvent]:
        """Inspect cluster load metrics and trigger autonomous scale-up or scale-to-zero reaping."""
        nodes = [n for n in self.mesh_service.list_nodes(online_only=True) if n.cluster_id == cluster_id]
        if not nodes:
            return []

        events: list[AutoscalingEvent] = []

        total_active_slots = sum(n.capacity.active_execution_slots for n in nodes)
        total_max_slots = sum(max(1, n.capacity.max_execution_slots) for n in nodes)
        cluster_utilization_pct = (total_active_slots / max(1, total_max_slots)) * 100.0
        max_queue = max((n.capacity.queue_depth for n in nodes), default=0)
        avg_ewma_ms = sum(n.capacity.ewma_latency_ms for n in nodes) / len(nodes)

        ephemeral_nodes = [n for n in nodes if n.capacity.is_ephemeral]
        current_ephemeral_count = len(ephemeral_nodes)

        # 1. Scale-Up Check:
        should_scale_up = (
            cluster_utilization_pct >= self.policy.scale_up_utilization_pct
            or max_queue >= self.policy.scale_up_queue_depth
            or avg_ewma_ms >= self.policy.scale_up_latency_ms
        )

        if should_scale_up:
            if current_ephemeral_count < self.policy.max_ephemeral_enclaves:
                trigger_metric = (
                    "utilization_pct"
                    if cluster_utilization_pct >= self.policy.scale_up_utilization_pct
                    else ("queue_depth" if max_queue >= self.policy.scale_up_queue_depth else "ewma_latency_ms")
                )
                trigger_val = (
                    cluster_utilization_pct
                    if trigger_metric == "utilization_pct"
                    else (float(max_queue) if trigger_metric == "queue_depth" else avg_ewma_ms)
                )

                new_node = await self.provisioner.provision_ephemeral_enclave(cluster_id)
                event = AutoscalingEvent(
                    event_id=f"evt_scaleup_{uuid.uuid4().hex[:8]}",
                    timestamp=time.time(),
                    cluster_id=cluster_id,
                    action=AutoscalingAction.SCALE_UP,
                    reason=f"Cluster load triggered scale-up (util: {cluster_utilization_pct:.1f}%, queue: {max_queue}, latency: {avg_ewma_ms:.1f}ms).",
                    node_id=new_node.node_id,
                    trigger_metric=trigger_metric,
                    metric_value=round(trigger_val, 2),
                    details={"total_ephemeral": current_ephemeral_count + 1},
                )
                self.record_event(event)
                events.append(event)
            else:
                logger.warning(
                    f"Cluster '{cluster_id}' needs scale-up but reached max_ephemeral_enclaves "
                    f"({self.policy.max_ephemeral_enclaves})."
                )

        # 2. Scale-Down (Scale-to-Zero) Reaping Check:
        for encl in ephemeral_nodes:
            if encl.capacity.active_execution_slots == 0:
                if encl.capacity.ephemeral_idle_seconds >= self.policy.scale_down_idle_seconds:
                    await self.provisioner.terminate_ephemeral_enclave(encl.node_id)
                    event = AutoscalingEvent(
                        event_id=f"evt_scaledown_{uuid.uuid4().hex[:8]}",
                        timestamp=time.time(),
                        cluster_id=cluster_id,
                        action=AutoscalingAction.SCALE_DOWN,
                        reason=f"Ephemeral enclave '{encl.node_id}' idle for {encl.capacity.ephemeral_idle_seconds:.1f}s (timeout: {self.policy.scale_down_idle_seconds}s).",
                        node_id=encl.node_id,
                        trigger_metric="ephemeral_idle_seconds",
                        metric_value=encl.capacity.ephemeral_idle_seconds,
                    )
                    self.record_event(event)
                    events.append(event)

        return events

    def get_cluster_load_summary(self) -> dict[str, Any]:
        """Aggregate real-time capacity and load metrics across all clusters in the mesh."""
        all_nodes = self.mesh_service.list_nodes(online_only=False)
        clusters: dict[str, list[MeshPeerNode]] = {}
        for n in all_nodes:
            clusters.setdefault(n.cluster_id, []).append(n)

        summary: dict[str, Any] = {
            "total_nodes": len(all_nodes),
            "online_nodes": sum(1 for n in all_nodes if n.status == MeshNodeStatus.ONLINE),
            "ephemeral_nodes": sum(1 for n in all_nodes if n.capacity.is_ephemeral),
            "clusters": {},
        }

        for cid, nodes in clusters.items():
            online_c_nodes = [n for n in nodes if n.status == MeshNodeStatus.ONLINE]
            active_slots = sum(n.capacity.active_execution_slots for n in online_c_nodes)
            max_slots = sum(max(1, n.capacity.max_execution_slots) for n in online_c_nodes)
            utilization = (active_slots / max(1, max_slots)) * 100.0
            avg_ewma = (
                sum(n.capacity.ewma_latency_ms for n in online_c_nodes) / len(online_c_nodes)
                if online_c_nodes
                else 0.0
            )

            summary["clusters"][cid] = {
                "total_nodes": len(nodes),
                "online_nodes": len(online_c_nodes),
                "ephemeral_nodes": sum(1 for n in nodes if n.capacity.is_ephemeral),
                "active_execution_slots": active_slots,
                "max_execution_slots": max_slots,
                "utilization_pct": round(utilization, 1),
                "avg_ewma_latency_ms": round(avg_ewma, 1),
                "queue_depth": sum(n.capacity.queue_depth for n in online_c_nodes),
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "role": n.role.value,
                        "status": n.status.value,
                        "is_ephemeral": n.capacity.is_ephemeral,
                        "active_slots": n.capacity.active_execution_slots,
                        "max_slots": n.capacity.max_execution_slots,
                        "cpu_pct": n.capacity.cpu_utilization_pct,
                        "ewma_latency_ms": n.capacity.ewma_latency_ms,
                        "queue_depth": n.capacity.queue_depth,
                        "idle_seconds": n.capacity.ephemeral_idle_seconds,
                    }
                    for n in nodes
                ],
            }

        return summary
