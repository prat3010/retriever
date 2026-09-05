"""Unit Test Suite for Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication (M99).

Verifies:
- Hexagonal domain boundary compliance (0 framework/DB imports in domain)
- Quorum consensus calculations and split-brain defense
- Automated circuit breaker trigger on health probe degradation
- Manual operator leader failover with generation term incrementation
- Turso / LibSQL embedded replica config and WAL frame tracking
- Platform Battery #19 catalog registration in BatteryService
- REST API responses across admin and tenant endpoints
"""

import ast
import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.abstractions.batteries import BatteryCategory, BatteryStatus
from src.domain.abstractions.multicloud import (
    CloudRegion,
    ClusterNodeRole,
    FailoverRequest,
    FailoverTriggerType,
    QuorumState,
    RegionHealthProbe,
)
from src.domain.batteries.battery_service import BatteryService
from src.domain.multicloud.failover_controller import FailoverController
from src.domain.multicloud.libsql_replication_service import LibsqlReplicationService
from src.main import app

# ---------------------------------------------------------------------------
# Test 1: Hexagonal Architecture Conformance
# ---------------------------------------------------------------------------


def test_multicloud_domain_abstractions_zero_framework_imports():
    """Verifies that src/domain/abstractions/multicloud.py has zero DB or web framework imports."""
    domain_path = os.path.join(
        os.path.dirname(__file__),
        "../src/domain/abstractions/multicloud.py",
    )
    with open(domain_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="multicloud.py")

    disallowed = {"fastapi", "sqlalchemy", "httpx", "redis", "celery", "pydantic_settings"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                root_pkg = name.name.split(".")[0]
                assert root_pkg not in disallowed, f"Disallowed import '{root_pkg}' in multicloud abstractions"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in disallowed, f"Disallowed import from '{root_pkg}' in multicloud abstractions"


# ---------------------------------------------------------------------------
# Test 2: Quorum Calculations & Split-Brain Defense
# ---------------------------------------------------------------------------


def test_quorum_consensus_and_split_brain_defense():
    """Verifies that failover requires majority (>50%) voting quorum and avoids split-brain."""
    controller = FailoverController()
    topology = controller.get_topology()

    assert topology.has_quorum is True
    assert topology.quorum_state == QuorumState.CONSENSUS_REACHED
    assert topology.active_leader_region == CloudRegion.OCI_BOM
    assert topology.generation_term == 1

    # Simulate network partition where 2 out of 3 voting nodes are degraded
    controller.nodes["node-aws-iad-01"].role = ClusterNodeRole.DEGRADED
    controller.nodes["node-fly-fra-01"].role = ClusterNodeRole.DEGRADED

    degraded_topology = controller.get_topology()
    assert degraded_topology.has_quorum is False
    assert degraded_topology.quorum_state == QuorumState.QUORUM_LOST

    # Attempt failover without force flag -> MUST be rejected to avoid split-brain
    failover_req = FailoverRequest(
        target_region=CloudRegion.FLY_FRA,
        reason="Partitioned failover attempt",
        force=False,
    )
    result = controller.execute_failover(failover_req)

    assert result.success is False
    assert result.quorum_state == QuorumState.SPLIT_BRAIN_AVOIDED
    assert "Split-brain avoided" in result.message
    # Leader must remain unchanged
    assert controller.active_leader_region == CloudRegion.OCI_BOM


# ---------------------------------------------------------------------------
# Test 3: Automated Circuit Breaker on Health Probe Degradation
# ---------------------------------------------------------------------------


def test_automated_circuit_breaker_on_probe_failures():
    """Verifies that consecutive probe failures on primary leader trigger automatic failover."""
    controller = FailoverController(failover_threshold_failures=2)
    assert controller.active_leader_region == CloudRegion.OCI_BOM

    # Probe 1 failure
    probe_fail_1 = RegionHealthProbe(
        node_id="node-oci-bom-01",
        region=CloudRegion.OCI_BOM,
        probe_url="https://rag.prateeq.in/health/liveness",
        latency_ms=1800.0,
        status_code=504,
        is_healthy=False,
        failure_reason="Gateway Timeout",
        probed_at="2026-09-05T15:00:00Z",
        is_simulated=True,
    )
    res1 = controller.record_probe_result(probe_fail_1)
    assert res1 is None  # Threshold not yet reached (1/2)

    # Probe 2 failure -> Should trigger automatic election of AWS US-East (weight 90)
    probe_fail_2 = RegionHealthProbe(
        node_id="node-oci-bom-01",
        region=CloudRegion.OCI_BOM,
        probe_url="https://rag.prateeq.in/health/liveness",
        latency_ms=2000.0,
        status_code=503,
        is_healthy=False,
        failure_reason="Service Unavailable",
        probed_at="2026-09-05T15:00:10Z",
        is_simulated=True,
    )
    res2 = controller.record_probe_result(probe_fail_2)

    assert res2 is not None
    assert res2.success is True
    assert res2.old_leader == CloudRegion.OCI_BOM
    assert res2.new_leader == CloudRegion.AWS_IAD
    assert controller.active_leader_region == CloudRegion.AWS_IAD
    assert controller.generation_term == 2


# ---------------------------------------------------------------------------
# Test 4: Manual Operator Failover Transition
# ---------------------------------------------------------------------------


def test_manual_operator_failover():
    """Verifies intentional operator-driven leader failover and term increments."""
    controller = FailoverController()
    assert controller.active_leader_region == CloudRegion.OCI_BOM

    req = FailoverRequest(
        target_region=CloudRegion.FLY_FRA,
        reason="Scheduled maintenance on Mumbai VPS",
        trigger_type=FailoverTriggerType.MANUAL_OPERATOR_OVERRIDE,
        operator_id="prateek_admin",
    )
    result = controller.execute_failover(req)

    assert result.success is True
    assert result.old_leader == CloudRegion.OCI_BOM
    assert result.new_leader == CloudRegion.FLY_FRA
    assert result.generation_term == 2
    assert result.quorum_votes_acquired >= 2
    assert controller.active_leader_region == CloudRegion.FLY_FRA


# ---------------------------------------------------------------------------
# Test 5: LibSQL Embedded Replica Configuration & Token Derivation
# ---------------------------------------------------------------------------


def test_libsql_replica_config_and_token():
    """Verifies tenant replica credentials and deterministic sync auth token."""
    service = LibsqlReplicationService()
    config = service.get_replica_config(
        tenant_id="tenant_alpha_01",
        active_leader_url="https://rag.prateeq.in",
        active_leader_region=CloudRegion.OCI_BOM,
    )

    assert config.tenant_id == "tenant_alpha_01"
    assert config.primary_url == "https://rag.prateeq.in"
    assert "tenant_alpha_01" in config.replica_url
    assert config.auth_token.startswith("tkn_libsql_")
    assert config.read_local is True
    assert config.write_proxy_to_primary is True
    assert "tenant_a" in config.db_file_path


# ---------------------------------------------------------------------------
# Test 6: LibSQL Replication Lag Tracking & Cycle Advances
# ---------------------------------------------------------------------------


def test_libsql_replication_lag_and_cycle():
    """Verifies WAL frame advance, sub-1ms replication metrics, and write tracking."""
    service = LibsqlReplicationService()
    initial_stats = service.get_replication_stats("tenant_beta_02")

    assert initial_stats.primary_wal_frame == 1280
    assert initial_stats.replication_lag_frames == 0
    assert initial_stats.replication_lag_ms < 1.0

    # Advance sync cycle
    updated_stats = service.record_sync_cycle("tenant_beta_02", frames_synced=15, sync_duration_ms=0.72)
    assert updated_stats.primary_wal_frame == 1295
    assert updated_stats.local_wal_frame == 1295
    assert updated_stats.replication_lag_frames == 0
    assert updated_stats.sync_status == "synced"

    # Forward a write
    write_stats = service.record_write_forwarded("tenant_beta_02")
    assert write_stats.writes_forwarded == 15
    assert write_stats.replication_lag_frames == 1
    assert write_stats.sync_status == "catching_up"


# ---------------------------------------------------------------------------
# Test 7: Platform Battery #19 Catalog Registration
# ---------------------------------------------------------------------------


def test_battery_19_registration():
    """Verifies Platform Battery #19 is registered under EDGE_DISTRIBUTION in BatteryService."""
    battery_service = BatteryService()
    batteries = battery_service.get_platform_batteries().batteries

    battery_19 = next((b for b in batteries if b.id == "multicloud_failover_libsql"), None)
    assert battery_19 is not None, "Battery #19 'multicloud_failover_libsql' not found in catalog"
    assert battery_19.category == BatteryCategory.EDGE_DISTRIBUTION
    assert battery_19.status == BatteryStatus.ACTIVE
    assert "LibSQL" in battery_19.algorithm_foundation
    assert battery_19.milestone == "M99 (v0.84.0)"
    assert battery_19.health_check_endpoint == "/v1/admin/multicloud/clusters"


# ---------------------------------------------------------------------------
# Test 8: REST API Endpoints Integration (Admin & Tenant)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multicloud_rest_api_endpoints():
    """Verifies /v1/admin/multicloud/* and /v1/tenants/{id}/multicloud/* routes."""
    from src.config import settings
    transport = ASGITransport(app=app)
    admin_headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin clusters overview
        resp = await client.get("/v1/admin/multicloud/clusters", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "topology" in data
        assert data["topology"]["cluster_id"] == "retriever-global-mesh"
        assert len(data["topology"]["nodes"]) >= 4
        assert data["active_battery"]["id"] == "multicloud_failover_libsql"

        # 2. Admin trigger health probes
        probe_resp = await client.post("/v1/admin/multicloud/probe", headers=admin_headers)
        assert probe_resp.status_code == 200
        probes = probe_resp.json()
        assert len(probes) >= 4
        assert any(p["region"] == "oci-bom" for p in probes)

        # 3. Admin replication status
        repl_resp = await client.get("/v1/admin/multicloud/replication-status", headers=admin_headers)
        assert repl_resp.status_code == 200
        repl_data = repl_resp.json()
        assert repl_data["engine"] == "libsql_embedded_wal"
        assert "global_wal_frame" in repl_data

        # 4. Tenant replica config
        cfg_resp = await client.get(
            "/v1/tenants/00000000-0000-0000-0000-000000000001/multicloud/replica-config",
            headers=admin_headers,
        )
        assert cfg_resp.status_code == 200
        cfg_data = cfg_resp.json()
        assert cfg_data["tenant_id"] == "00000000-0000-0000-0000-000000000001"
        assert cfg_data["read_local"] is True

        # 5. Tenant force sync
        sync_resp = await client.post(
            "/v1/tenants/00000000-0000-0000-0000-000000000001/multicloud/sync",
            headers=admin_headers,
        )
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["sync_status"] == "synced"
        assert sync_data["replication_lag_ms"] <= 2.0
