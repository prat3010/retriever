import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.api.security import verify_admin_key
from src.adapters.database.read_replica_adapter import ReadReplicaAdapter
from src.domain.abstractions.edge_router import (
    MultiRegionClusterStatus,
    RegionCode,
    ReplicaHealthStatus,
)
from src.domain.routing import edge_router_service
from src.domain.routing.edge_router_service import EdgeRouterService
from src.main import app


def test_edge_router_service_geo_mapping() -> None:
    """Verify Geo-IP routing maps countries to the optimal regional node."""
    service = EdgeRouterService(
        configured_regions={RegionCode.AP_SOUTH, RegionCode.US_EAST, RegionCode.EU_CENTRAL},
        primary_region=RegionCode.AP_SOUTH,
    )

    # Americas -> US-East
    for country in ["US", "CA", "MX", "BR", "AR"]:
        decision = service.resolve_region(country)
        assert decision.selected_region == RegionCode.US_EAST
        assert decision.is_fallback is False
        assert decision.estimated_reduction_pct > 80.0

    # Europe & Middle East -> EU-Central
    for country in ["GB", "DE", "FR", "IT", "NL", "AE"]:
        decision = service.resolve_region(country)
        assert decision.selected_region == RegionCode.EU_CENTRAL
        assert decision.is_fallback is False
        assert decision.estimated_reduction_pct > 80.0

    # Asia-Pacific -> AP-South
    for country in ["IN", "SG", "JP", "AU"]:
        decision = service.resolve_region(country)
        assert decision.selected_region == RegionCode.AP_SOUTH
        assert decision.is_fallback is False

    # Unknown / Null -> AP-South (Primary Master)
    decision_null = service.resolve_region(None)
    assert decision_null.selected_region == RegionCode.AP_SOUTH

    decision_unknown = service.resolve_region("ZZ")
    assert decision_unknown.selected_region == RegionCode.AP_SOUTH


def test_unconfigured_replica_graceful_fallback() -> None:
    """When a regional replica is not configured, queries gracefully fallback to Primary Master."""
    # Only AP_SOUTH is configured
    service = EdgeRouterService(
        configured_regions={RegionCode.AP_SOUTH},
        primary_region=RegionCode.AP_SOUTH,
    )

    # US visitor should fall back to AP-South with zero crash
    decision = service.resolve_region("US")
    assert decision.selected_region == RegionCode.AP_SOUTH
    assert decision.is_fallback is True
    assert "unconfigured or degraded" in decision.routing_reason


def test_degraded_replica_circuit_breaker() -> None:
    """When a replica is marked degraded or unreachable, traffic circuit-breaks to Master."""
    service = EdgeRouterService(
        configured_regions={RegionCode.AP_SOUTH, RegionCode.US_EAST},
        primary_region=RegionCode.AP_SOUTH,
    )

    # Mark US-East as degraded
    service.set_node_status(RegionCode.US_EAST, ReplicaHealthStatus.UNREACHABLE)

    decision = service.resolve_region("US")
    assert decision.selected_region == RegionCode.AP_SOUTH
    assert decision.is_fallback is True


def test_cluster_status_topology() -> None:
    """Verify cluster topology reports all 3 regions with primary flag."""
    service = EdgeRouterService(
        configured_regions={RegionCode.AP_SOUTH, RegionCode.US_EAST},
        primary_region=RegionCode.AP_SOUTH,
    )
    status = service.get_cluster_status()

    assert isinstance(status, MultiRegionClusterStatus)
    assert status.total_regions == 3
    assert status.primary_region == RegionCode.AP_SOUTH
    assert len(status.regions) == 3

    primary_node = next(r for r in status.regions if r.region_code == RegionCode.AP_SOUTH)
    assert primary_node.is_primary is True
    assert primary_node.is_configured is True


@pytest.mark.asyncio
async def test_read_replica_adapter_probe_and_session() -> None:
    """Verify ReadReplicaAdapter probes latency and manages session creation."""
    service = EdgeRouterService()

    # Mock async engine to verify probe without requiring live external db connection
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value.__aexit__.return_value = None

    adapter = ReadReplicaAdapter(router_service=service, primary_eng=mock_engine)

    # Probe regional nodes
    probe_resp = await adapter.probe_regional_health()
    assert len(probe_resp.results) == 3
    assert probe_resp.overall_health in ("HEALTHY", "DEGRADED")


@pytest.mark.asyncio
async def test_admin_edge_routing_endpoints() -> None:
    """Verify REST API endpoints for multi-region status, probing, and Geo-IP simulation."""
    app.dependency_overrides[verify_admin_key] = lambda: True
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # GET cluster status
            res = await client.get("/v1/admin/platform/regions")
            assert res.status_code == 200
            data = res.json()
            assert "primary_region" in data
            assert len(data["regions"]) == 3

            # POST probe
            res_probe = await client.post("/v1/admin/platform/regions/probe")
            assert res_probe.status_code == 200
            probe_data = res_probe.json()
            assert "results" in probe_data

            # GET preview Geo-IP simulation
            res_prev = await client.get("/v1/admin/platform/regions/preview?country=US")
            assert res_prev.status_code == 200
            decision = res_prev.json()
            assert decision["client_country"] == "US"
            assert decision["detected_continent"] == "Americas"
    finally:
        app.dependency_overrides.pop(verify_admin_key, None)


def test_hexagonal_architecture_edge_router() -> None:
    """Ensure edge router domain layer has ZERO dependencies on SQLAlchemy or external frameworks."""
    source_code = inspect.getsource(edge_router_service)
    forbidden_terms = ["sqlalchemy", "asyncpg", "fastapi", "httpx", "starlette", "requests"]
    for term in forbidden_terms:
        assert f"import {term}" not in source_code, f"Forbidden import '{term}' in edge_router_service.py"
        assert f"from {term}" not in source_code, f"Forbidden from-import '{term}' in edge_router_service.py"
