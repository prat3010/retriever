"""Tests for Autonomous Mesh Dynamic Load-Balancing & Ephemeral Enclave Auto-Scaling (M116).

Verifies:
- Hexagonal boundary invariants (0 forbidden imports in load_balancer_service.py).
- Platform Battery #31 registration in BatteryService.
- Composite score formula and Power-of-Two-Choices (P2C) candidate selection.
- EWMA latency decay (alpha=0.2) and slot concurrency tracking.
- Adaptive load-shedding when all candidate nodes exceed 95% saturation.
- Autonomous scale-up enclave provisioning under high cluster pressure.
- Scale-to-zero reaping of idle ephemeral enclaves after 300s inactivity.
- FastAPI REST endpoints (/v1/mesh/load/*).
"""

import ast
import os

import pytest
from fastapi.testclient import TestClient

from src.container import battery_service, container
from src.domain.abstractions.exceptions import (
    MeshLoadSheddingError,
)
from src.domain.abstractions.mcp import McpToolDefinition
from src.domain.abstractions.mcp_mesh import (
    AutoscalingAction,
    AutoscalingPolicy,
    MeshNodeRole,
    MeshNodeStatus,
    MeshPeerNode,
    NodeCapacityMetrics,
)
from src.domain.mcp.load_balancer_service import (
    MeshLoadBalancerService,
    SovereignEnclaveProvisionerAdapter,
)
from src.domain.mcp.mesh_service import McpMeshService
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_mesh_load_balancer_hexagonal_architecture():
    """Verify load_balancer_service.py has zero forbidden framework dependencies."""
    base_dir = os.path.dirname(__file__)
    target_files = [
        "../src/domain/mcp/load_balancer_service.py",
    ]
    forbidden_prefixes = ("src.adapters", "src.routers", "sqlalchemy", "fastapi")

    for rel_path in target_files:
        filepath = os.path.join(base_dir, rel_path)
        assert os.path.exists(filepath), f"File {filepath} must exist"

        with open(filepath) as f:
            tree = ast.parse(f.read(), filename=filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_prefixes:
                        assert not alias.name.startswith(forbidden), (
                            f"Violation in {rel_path}: '{alias.name}' imports forbidden '{forbidden}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_prefixes:
                        assert not node.module.startswith(forbidden), (
                            f"Violation in {rel_path}: '{node.module}' imports forbidden '{forbidden}'"
                        )


def test_battery_31_registration():
    """Verify Platform Battery #31 (mesh_load_balancer) is actively registered in BatteryService."""
    battery = battery_service.get_battery("mesh_load_balancer")
    assert battery is not None, "Battery #31 'mesh_load_balancer' must be registered."
    assert battery.name == "Autonomous Mesh Dynamic Load-Balancing & Ephemeral Enclave Auto-Scaling"
    assert battery.category.value == "system_extensibility"
    assert battery.status.value == "active"
    assert battery.milestone.startswith("M116")
    assert battery.health_check_endpoint == "/v1/mesh/load/metrics"


def test_p2c_and_composite_score_calculation():
    """Verify composite load score math and Power-of-Two-Choices selection."""
    mesh_service = McpMeshService(
        local_node_id="local_primary",
        local_cluster_id="test_cluster",
    )
    lb = MeshLoadBalancerService(mesh_service=mesh_service, ewma_alpha=0.2)

    # Node A: low latency, 0 queue, 2/10 slots
    node_a = MeshPeerNode(
        node_id="node_a",
        cluster_id="test_cluster",
        endpoint_url="http://10.0.0.1:8000",
        role=MeshNodeRole.SEED_GATEWAY,
        status=MeshNodeStatus.ONLINE,
        advertised_tools=[McpToolDefinition(name="audit_tool", description="test")],
        latency_ms=10.0,
        capacity=NodeCapacityMetrics(
            active_execution_slots=2,
            max_execution_slots=10,
            queue_depth=0,
            ewma_latency_ms=10.0,
        ),
    )

    # Node B: high latency, queue depth 2, 8/10 slots
    node_b = MeshPeerNode(
        node_id="node_b",
        cluster_id="test_cluster",
        endpoint_url="http://10.0.0.2:8000",
        role=MeshNodeRole.EDGE_ENCLAVE,
        status=MeshNodeStatus.ONLINE,
        advertised_tools=[McpToolDefinition(name="audit_tool", description="test")],
        latency_ms=50.0,
        capacity=NodeCapacityMetrics(
            active_execution_slots=8,
            max_execution_slots=10,
            queue_depth=2,
            ewma_latency_ms=50.0,
        ),
    )

    score_a = lb.calculate_composite_load_score(node_a)
    score_b = lb.calculate_composite_load_score(node_b)

    # Score A: 10.0 * (1 + 0) * (1 + 0.2) = 12.0
    assert score_a == 12.0
    # Score B: 50.0 * (1 + 2) * (1 + 0.8) = 50 * 3 * 1.8 = 270.0
    assert score_b == 270.0

    # P2C between these two must choose node_a
    winner = lb.select_node_p2c([node_a, node_b])
    assert winner.node_id == "node_a"


def test_ewma_latency_decay_and_slot_tracking():
    """Verify EWMA updates with alpha=0.2 and active slot increment/decrement."""
    mesh_service = McpMeshService(
        local_node_id="local_primary",
        local_cluster_id="test_cluster",
    )
    lb = MeshLoadBalancerService(mesh_service=mesh_service, ewma_alpha=0.2)

    node = MeshPeerNode(
        node_id="test_node",
        cluster_id="test_cluster",
        endpoint_url="http://10.0.0.1:8000",
        role=MeshNodeRole.SEED_GATEWAY,
        status=MeshNodeStatus.ONLINE,
        advertised_tools=[],
        latency_ms=10.0,
        capacity=NodeCapacityMetrics(
            active_execution_slots=0,
            max_execution_slots=4,
            queue_depth=0,
            ewma_latency_ms=20.0,
        ),
    )
    mesh_service.register_node(node)

    # Acquire slot
    lb.acquire_slot("test_node")
    assert node.capacity.active_execution_slots == 1

    # Release slot with sample latency of 100ms
    # new_ewma = 0.2 * 100 + 0.8 * 20 = 20 + 16 = 36.0
    lb.release_slot("test_node", sample_latency_ms=100.0)
    assert node.capacity.active_execution_slots == 0
    assert node.capacity.ewma_latency_ms == 36.0

    # Release another slot with sample latency of 36ms -> EWMA remains 36.0
    lb.acquire_slot("test_node")
    lb.release_slot("test_node", sample_latency_ms=36.0)
    assert node.capacity.ewma_latency_ms == 36.0


def test_adaptive_load_shedding_at_95_percent():
    """Verify resolve_load_balanced_route triggers load shedding when all nodes exceed 95%."""
    mesh_service = McpMeshService(
        local_node_id="local_primary",
        local_cluster_id="test_cluster",
    )
    lb = MeshLoadBalancerService(mesh_service=mesh_service)

    # Register saturated node
    node = MeshPeerNode(
        node_id="saturated_node",
        cluster_id="test_cluster",
        endpoint_url="http://10.0.0.1:8000",
        role=MeshNodeRole.SEED_GATEWAY,
        status=MeshNodeStatus.ONLINE,
        advertised_tools=[McpToolDefinition(name="heavy_job", description="test")],
        latency_ms=10.0,
        capacity=NodeCapacityMetrics(
            active_execution_slots=10,
            max_execution_slots=10,  # 100% saturated >= 95%
            queue_depth=5,
            ewma_latency_ms=80.0,
        ),
    )
    mesh_service.register_node(node)

    with pytest.raises(MeshLoadSheddingError) as exc_info:
        lb.resolve_load_balanced_route("heavy_job", cluster_id="test_cluster")

    assert "Mesh cluster saturated" in str(exc_info.value)

    events = lb.get_events()
    assert len(events) >= 1
    shed_event = next(e for e in events if e.action == AutoscalingAction.SHED_LOAD)
    assert shed_event.trigger_metric == "slot_utilization_pct"


@pytest.mark.asyncio
async def test_autoscaling_scale_up_and_scale_to_zero():
    """Verify autonomous scale-up provisioning and scale-to-zero reaping."""
    mesh_service = McpMeshService(
        local_node_id="local_primary",
        local_cluster_id="seed_cluster",
    )
    provisioner = SovereignEnclaveProvisionerAdapter(mesh_service)
    policy = AutoscalingPolicy(
        scale_up_utilization_pct=80.0,
        scale_down_idle_seconds=60.0,
        max_ephemeral_enclaves=3,
    )
    lb = MeshLoadBalancerService(mesh_service=mesh_service, provisioner=provisioner, policy=policy)

    # Register initial node with 90% utilization in enclave_cluster (triggers scale-up)
    primary_node = MeshPeerNode(
        node_id="primary_node",
        cluster_id="enclave_cluster",
        endpoint_url="http://10.0.0.1:8000",
        role=MeshNodeRole.SEED_GATEWAY,
        status=MeshNodeStatus.ONLINE,
        advertised_tools=[McpToolDefinition(name="search_db", description="test")],
        latency_ms=10.0,
        capacity=NodeCapacityMetrics(
            active_execution_slots=9,
            max_execution_slots=10,
            ewma_latency_ms=25.0,
        ),
    )
    mesh_service.register_node(primary_node)

    # 1. Evaluate autoscaling -> should scale UP
    scale_up_events = await lb.evaluate_autoscaling("enclave_cluster")
    assert len(scale_up_events) == 1
    assert scale_up_events[0].action == AutoscalingAction.SCALE_UP
    enclave_id = scale_up_events[0].node_id
    assert enclave_id is not None
    assert mesh_service.get_node(enclave_id) is not None

    # Check that enclave is ephemeral
    enclave_node = mesh_service.get_node(enclave_id)
    assert enclave_node.capacity.is_ephemeral is True

    # 2. Simulate enclave idle time beyond threshold (e.g. 75s > 60s)
    enclave_node.capacity.active_execution_slots = 0
    enclave_node.capacity.ephemeral_idle_seconds = 75.0
    primary_node.capacity.active_execution_slots = 2  # Relieve primary load

    # 3. Evaluate autoscaling -> should reap to zero
    scale_down_events = await lb.evaluate_autoscaling("enclave_cluster")
    assert len(scale_down_events) == 1
    assert scale_down_events[0].action == AutoscalingAction.SCALE_DOWN
    assert scale_down_events[0].node_id == enclave_id

    # Node must be unregistered from mesh
    assert mesh_service.get_node(enclave_id) is None


def test_fastapi_rest_endpoints_load_balancer(client):
    """Test all M116 load balancer REST API endpoints."""
    # 1. GET /v1/mesh/load/metrics
    res_metrics = client.get("/v1/mesh/load/metrics")
    assert res_metrics.status_code == 200
    data = res_metrics.json()
    assert "total_nodes" in data
    assert "clusters" in data

    # 2. POST /v1/mesh/load/autoscaling/policy
    new_policy = {
        "scale_up_utilization_pct": 75.0,
        "scale_up_queue_depth": 8,
        "scale_up_latency_ms": 220.0,
        "scale_down_idle_seconds": 180.0,
        "min_enclaves": 0,
        "max_ephemeral_enclaves": 6,
        "load_shedding_threshold_pct": 92.0,
    }
    res_policy = client.post("/v1/mesh/load/autoscaling/policy", json=new_policy)
    assert res_policy.status_code == 200
    policy_resp = res_policy.json()
    assert policy_resp["scale_up_utilization_pct"] == 75.0
    assert policy_resp["scale_down_idle_seconds"] == 180.0

    # 3. POST /v1/mesh/load/heartbeat-telemetry
    local_id = container.mcp_mesh_service.local_node_id
    telemetry_payload = {
        "node_id": local_id,
        "metrics": {
            "cpu_utilization_pct": 25.5,
            "memory_utilization_pct": 40.0,
            "active_execution_slots": 1,
            "max_execution_slots": 16,
            "queue_depth": 0,
            "ewma_latency_ms": 12.5,
            "is_ephemeral": False,
            "ephemeral_idle_seconds": 0.0,
        },
    }
    res_telemetry = client.post("/v1/mesh/load/heartbeat-telemetry", json=telemetry_payload)
    assert res_telemetry.status_code == 200
    node_resp = res_telemetry.json()
    assert node_resp["capacity"]["cpu_utilization_pct"] == 25.5
    assert node_resp["capacity"]["ewma_latency_ms"] == 12.5

    # 4. POST /v1/mesh/load/scale-down/reap
    res_reap = client.post("/v1/mesh/load/scale-down/reap?cluster_id=cluster-primary")
    assert res_reap.status_code == 200
    assert isinstance(res_reap.json(), list)

    # 5. GET /v1/mesh/load/autoscaling/events
    res_events = client.get("/v1/mesh/load/autoscaling/events?limit=10")
    assert res_events.status_code == 200
    assert isinstance(res_events.json(), list)
