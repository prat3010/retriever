"""FastAPI Router for Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication (M99).

Exposes administrative observability and tenant-scoped endpoints for:
- Multi-cloud cluster topology and region node status
- Active-active quorum consensus health probing
- Manual and automated leader failover transitions
- Turso / LibSQL embedded replica credentials and WAL synchronization
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.multicloud import (
    ClusterTopology,
    FailoverRequest,
    FailoverResult,
    LibsqlReplicaConfig,
    LibsqlReplicationStats,
    RegionHealthProbe,
)

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/v1/admin/multicloud",
    tags=["multicloud", "admin"],
    dependencies=[Depends(verify_admin_key)],
)

tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/multicloud",
    tags=["multicloud", "tenant"],
    dependencies=[Depends(verify_tenant_or_admin)],
)

# Access domain services & adapters via container
_failover_controller = container.multicloud_failover_controller
_probe_adapter = container.multicloud_health_probe_adapter
_replication_service = container.libsql_replication_service
_replica_adapter = container.libsql_replica_adapter
_battery_service = container.battery_service


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------


class MultiCloudClusterOverviewResponse(BaseModel):
    """Administrative cluster overview containing topology and Battery #19 telemetry."""

    topology: ClusterTopology
    active_battery: dict[str, Any]
    probes_summary: dict[str, Any]


@admin_router.get(
    "/clusters",
    response_model=MultiCloudClusterOverviewResponse,
    summary="Get Multi-Cloud Topology & Quorum Health",
)
async def get_multicloud_clusters() -> MultiCloudClusterOverviewResponse:
    """Returns the complete distributed multi-cloud topology, active leader, and region health."""
    topology = _failover_controller.get_topology()
    battery = _battery_service.get_battery("multicloud_failover_libsql")

    battery_dict = (
        {
            "id": battery.id,
            "name": battery.name,
            "status": battery.status.value,
            "algorithm_foundation": battery.algorithm_foundation,
            "latency_profile": battery.latency_profile,
            "milestone": battery.milestone,
            "active_parameters": battery.active_parameters,
        }
        if battery
        else {}
    )

    probes_summary = {
        "total_nodes": len(topology.nodes),
        "healthy_count": topology.healthy_nodes,
        "voting_quorum_ratio": f"{topology.healthy_nodes}/{topology.total_nodes}",
        "quorum_state": topology.quorum_state.value,
        "environment_mode": topology.environment_mode,
    }

    return MultiCloudClusterOverviewResponse(
        topology=topology,
        active_battery=battery_dict,
        probes_summary=probes_summary,
    )


@admin_router.post(
    "/probe",
    response_model=list[RegionHealthProbe],
    summary="Trigger Immediate Cross-Region Health Probes",
)
async def trigger_multicloud_probes() -> list[RegionHealthProbe]:
    """Concurrently probes all configured cloud regions and updates failover state."""
    nodes = list(_failover_controller.nodes.values())
    probes = await _probe_adapter.probe_all_regions(nodes)

    for p in probes:
        _failover_controller.record_probe_result(p)

    return probes


@admin_router.post(
    "/failover",
    response_model=FailoverResult,
    summary="Trigger Leader Failover Transition",
)
async def trigger_multicloud_failover(request: FailoverRequest) -> FailoverResult:
    """Executes a leader transition to a target cloud region with quorum consensus checks."""
    result = _failover_controller.execute_failover(request)
    if not result.success and not request.force:
        logger.warning("Failover rejected: %s", result.message)
    return result


@admin_router.get(
    "/replication-status",
    response_model=dict[str, Any],
    summary="Get Global LibSQL Replication Stats",
)
async def get_multicloud_replication_status() -> dict[str, Any]:
    """Returns global LibSQL replication lag, WAL streaming offsets, and tenant stats."""
    # Aggregate summary
    sample_stats = _replication_service.get_replication_stats("system_global")
    return {
        "engine": "libsql_embedded_wal",
        "turso_cluster_url": _replication_service.turso_cluster_url,
        "primary_endpoint": _failover_controller.nodes.get(
            _failover_controller.active_leader_node_id,
            next(iter(_failover_controller.nodes.values())),
        ).endpoint_url,
        "active_leader_region": _failover_controller.active_leader_region.value,
        "global_wal_frame": sample_stats.primary_wal_frame,
        "average_lag_ms": sample_stats.replication_lag_ms,
        "sync_status": sample_stats.sync_status,
        "reads_served_locally": sample_stats.reads_served_locally,
        "writes_forwarded": sample_stats.writes_forwarded,
    }


# ---------------------------------------------------------------------------
# Tenant Endpoints
# ---------------------------------------------------------------------------


@tenant_router.get(
    "/replica-config",
    response_model=LibsqlReplicaConfig,
    summary="Get Embedded LibSQL Replica Credentials",
)
async def get_tenant_replica_config(tenantId: str) -> LibsqlReplicaConfig:
    """Returns connection parameters and sync auth token for a tenant's embedded replica."""
    leader_node = _failover_controller.nodes.get(_failover_controller.active_leader_node_id)
    leader_url = leader_node.endpoint_url if leader_node else "https://rag.prateeq.in"

    return _replica_adapter.get_replica_config(
        tenant_id=tenantId,
        active_leader_url=leader_url,
        active_leader_region=_failover_controller.active_leader_region,
    )


@tenant_router.post(
    "/sync",
    response_model=LibsqlReplicationStats,
    summary="Force Sync Embedded LibSQL Replica",
)
async def sync_tenant_replica(tenantId: str) -> LibsqlReplicationStats:
    """Forces synchronization of the tenant's embedded replica against remote WAL stream."""
    return await _replica_adapter.sync_replica(tenantId)


@tenant_router.get(
    "/health",
    response_model=dict[str, Any],
    summary="Check Health from Nearest Cloud Region",
)
async def check_tenant_multicloud_health(tenantId: str) -> dict[str, Any]:
    """Returns health and latency from the nearest edge cloud region for this tenant."""
    leader_node = _failover_controller.nodes.get(_failover_controller.active_leader_node_id)
    stats = await _replica_adapter.get_replication_stats(tenantId)

    return {
        "tenant_id": tenantId,
        "active_leader_region": _failover_controller.active_leader_region.value,
        "active_leader_endpoint": leader_node.endpoint_url if leader_node else "https://rag.prateeq.in",
        "replica_wal_frame": stats.local_wal_frame,
        "replication_lag_ms": stats.replication_lag_ms,
        "status": "healthy",
    }
