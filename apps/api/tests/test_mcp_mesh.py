"""Tests for Distributed Model Context Protocol (MCP) Mesh & Agent Federation (M115).

Verifies:
- Pure Hexagonal Architecture boundary invariants (0 forbidden imports in domain).
- Platform Battery #30 registration in BatteryService.
- Peer node discovery, heartbeat liveness, and lease eviction.
- Latency-weighted routing across local and remote cluster nodes.
- HMAC-SHA256 cryptographic trust envelopes and nonce replay prevention.
- Cross-cluster agent federation with circular loop breakers (FederationLoopError).
- Multi-tenancy isolation enforcement.
- FastAPI REST endpoints (/v1/mesh/*).
"""

import ast
import os
import time

import pytest
from fastapi.testclient import TestClient

from src.container import battery_service, container
from src.domain.abstractions.exceptions import (
    FederationLoopError,
    MeshNodeUnreachableError,
    TenantIsolationViolationError,
    TrustVerificationError,
)
from src.domain.abstractions.mcp import McpToolDefinition
from src.domain.abstractions.mcp_mesh import (
    FederatedDelegationRequest,
    FederatedTaskStatus,
    MeshNodeRole,
    MeshNodeStatus,
    MeshPeerNode,
    MeshRoutingPolicy,
)
from src.domain.mcp.federation_service import AgentFederationService
from src.domain.mcp.mesh_service import McpMeshService
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_mcp_mesh_hexagonal_architecture():
    """Verify domain abstractions and services have zero forbidden framework dependencies."""
    base_dir = os.path.dirname(__file__)
    target_files = [
        "../src/domain/abstractions/mcp_mesh.py",
        "../src/domain/mcp/mesh_service.py",
        "../src/domain/mcp/federation_service.py",
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
                            f"Forbidden import '{alias.name}' in {filepath}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_prefixes:
                    assert not node.module.startswith(forbidden), (
                        f"Forbidden import '{node.module}' in {filepath}"
                    )


def test_platform_battery_30_registration():
    """Verify Platform Battery #30 (distributed_mcp_mesh) is active in BatteryService."""
    battery = battery_service.get_battery("distributed_mcp_mesh")
    assert battery is not None, "Battery #30 'distributed_mcp_mesh' must be cataloged"
    assert battery.name == "Distributed Model Context Protocol (MCP) Mesh & Agent Federation"
    assert battery.category == "system_extensibility"
    assert battery.status == "active"
    assert battery.milestone.startswith("M115")
    assert battery.health_check_endpoint == "/v1/mesh/status"
    assert "protocol" in battery.active_parameters
    assert battery.active_parameters["trust_envelope"] == "hmac_sha256"


def test_mesh_service_node_lifecycle():
    """Test node registration, heartbeat renewal, and stale node lease eviction."""
    svc = McpMeshService(
        local_node_id="node_us_primary",
        local_cluster_id="cluster_us_east",
    )

    # Local node registered
    nodes = svc.list_nodes()
    assert len(nodes) == 1
    assert nodes[0].node_id == "node_us_primary"
    assert nodes[0].role == MeshNodeRole.SEED_GATEWAY

    # Register remote peer
    remote_node = MeshPeerNode(
        node_id="node_eu_01",
        cluster_id="cluster_eu_central",
        endpoint_url="https://eu.rag.internal",
        role=MeshNodeRole.SOVEREIGN_NODE,
        status=MeshNodeStatus.ONLINE,
        latency_ms=25.0,
        advertised_tools=[
            McpToolDefinition(name="gdpr_compliance_check", description="Audit GDPR residency"),
        ],
    )
    svc.register_node(remote_node)

    assert len(svc.list_nodes()) == 2
    assert svc.get_node("node_eu_01") is not None

    # Heartbeat
    updated = svc.heartbeat("node_eu_01", latency_ms=22.5)
    assert updated is not None
    assert updated.latency_ms == 22.5

    # Stale eviction simulation
    remote_node.last_heartbeat = time.time() - 200.0  # Expired lease
    evicted_count = svc.evict_stale_nodes(timeout_seconds=120.0)
    assert evicted_count == 1
    assert svc.get_node("node_eu_01").status == MeshNodeStatus.UNREACHABLE


def test_latency_weighted_tool_routing():
    """Test resolving optimal execution node for tools based on latency policies."""
    svc = McpMeshService(local_node_id="node_local", local_cluster_id="cluster_local")

    # Local node advertises 'calculator'
    svc.update_local_tools([
        McpToolDefinition(name="calculator", description="Math eval"),
    ])

    # Remote nodes advertise 'specialist_analysis' with different latencies
    peer_fast = MeshPeerNode(
        node_id="node_fast",
        cluster_id="cluster_fast",
        endpoint_url="https://fast.internal",
        latency_ms=15.0,
        advertised_tools=[McpToolDefinition(name="specialist_analysis", description="Analysis")],
    )
    peer_slow = MeshPeerNode(
        node_id="node_slow",
        cluster_id="cluster_slow",
        endpoint_url="https://slow.internal",
        latency_ms=85.0,
        advertised_tools=[McpToolDefinition(name="specialist_analysis", description="Analysis")],
    )
    svc.register_node(peer_fast)
    svc.register_node(peer_slow)

    # Policy 1: LOCAL_FIRST -> calculator should resolve to local node
    route_calc = svc.resolve_tool_route("calculator", policy=MeshRoutingPolicy.LOCAL_FIRST)
    assert route_calc.node_id == "node_local"

    # Policy 2: LOWEST_LATENCY -> specialist_analysis should route to peer_fast
    route_spec = svc.resolve_tool_route("specialist_analysis", policy=MeshRoutingPolicy.LOWEST_LATENCY)
    assert route_spec.node_id == "node_fast"

    # Unadvertised tool raises MeshNodeUnreachableError
    with pytest.raises(MeshNodeUnreachableError):
        svc.resolve_tool_route("nonexistent_unknown_tool")


def test_cryptographic_trust_envelope_and_nonce_replay():
    """Verify HMAC-SHA256 signature verification and replay attack prevention."""
    svc = McpMeshService(cluster_secret="test_secret_key_123")

    payload = {"query": "SELECT * FROM audit", "tenant_id": "tn_test_01"}
    envelope = svc.create_trust_envelope(
        sender_cluster_id="cluster_a",
        receiver_cluster_id="cluster_b",
        tenant_id="tn_test_01",
        payload_data=payload,
    )

    assert envelope.signature is not None
    assert len(envelope.signature) == 64  # SHA256 hex string

    # 1. Valid verification
    assert svc.verify_trust_envelope(envelope, payload) is True

    # 2. Nonce replay detection
    with pytest.raises(TrustVerificationError, match="Replay attack detected"):
        svc.verify_trust_envelope(envelope, payload)

    # 3. Payload tampering detection
    tampered_envelope = svc.create_trust_envelope(
        sender_cluster_id="cluster_a",
        receiver_cluster_id="cluster_b",
        tenant_id="tn_test_01",
        payload_data=payload,
    )
    tampered_payload = {"query": "SELECT * FROM audit; DROP TABLE users;", "tenant_id": "tn_test_01"}
    with pytest.raises(TrustVerificationError, match="Payload integrity hash mismatch"):
        svc.verify_trust_envelope(tampered_envelope, tampered_payload)


@pytest.mark.asyncio
async def test_agent_federation_lifecycle_and_loop_breaker():
    """Test cross-cluster agent delegation, completion signature, and circular loop breaker."""
    mesh_svc = McpMeshService(local_cluster_id="cluster_eu_enclave")
    fed_svc = AgentFederationService(mesh_service=mesh_svc)

    # 1. Valid delegation
    req = fed_svc.create_delegation_request(
        target_cluster_id="cluster_eu_enclave",
        tenant_id="tn_enterprise_corp",
        intent="Audit compliance with sovereign data residency bounds",
        target_agent_role="forensic_auditor",
        max_depth=2,
        visited_clusters=["cluster_us_gateway"],
    )

    resp = await fed_svc.handle_delegation(req, verify_trust=True)
    assert resp.status == FederatedTaskStatus.COMPLETED
    assert resp.target_cluster_id == "cluster_eu_enclave"
    assert "FORENSIC_AUDITOR" in resp.synthesis
    assert len(resp.tool_trace_summary) >= 1
    assert resp.signature != ""

    # Check task retrieval
    retrieved = fed_svc.get_task_status(req.delegation_id)
    assert retrieved is not None
    assert retrieved.delegation_id == req.delegation_id

    # 2. Circular loop breaker: target cluster already visited
    loop_req = fed_svc.create_delegation_request(
        target_cluster_id="cluster_us_gateway",
        tenant_id="tn_enterprise_corp",
        intent="Loop back to gateway",
        max_depth=3,
        visited_clusters=["cluster_us_gateway", "cluster_eu_enclave"],
    )
    with pytest.raises(FederationLoopError, match="Circular delegation loop detected"):
        await fed_svc.handle_delegation(loop_req, verify_trust=False)

    # 3. Maximum depth breaker
    deep_req = fed_svc.create_delegation_request(
        target_cluster_id="cluster_apac_node",
        tenant_id="tn_enterprise_corp",
        intent="Deep hop",
        max_depth=2,
        visited_clusters=["cluster_us", "cluster_eu"],
    )
    with pytest.raises(FederationLoopError, match="Maximum cross-cluster delegation depth"):
        await fed_svc.handle_delegation(deep_req, verify_trust=False)

    # 4. Multi-tenancy isolation invariant: missing tenant_id
    invalid_tenant_req = FederatedDelegationRequest(
        delegation_id="del_bad",
        source_cluster_id="cluster_a",
        target_cluster_id="cluster_b",
        tenant_id="",  # Empty tenant ID
        intent="Query",
    )
    with pytest.raises(TenantIsolationViolationError):
        await fed_svc.handle_delegation(invalid_tenant_req, verify_trust=False)


def test_fastapi_mcp_mesh_endpoints(client: TestClient):
    """Test /v1/mesh/* REST API endpoints."""
    # 1. GET /v1/mesh/status
    res_status = client.get("/v1/mesh/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["battery_id"] == "distributed_mcp_mesh"
    assert data_status["status"] == "active"
    assert data_status["total_nodes"] >= 1

    # 2. GET /v1/mesh/nodes
    res_nodes = client.get("/v1/mesh/nodes")
    assert res_nodes.status_code == 200
    assert isinstance(res_nodes.json(), list)

    # 3. POST /v1/mesh/nodes/register
    peer_payload = {
        "node_id": "test_remote_peer_node",
        "cluster_id": "cluster_test_remote",
        "endpoint_url": "https://remote.test.io",
        "role": "edge_enclave",
        "status": "online",
        "advertised_tools": [
            {
                "name": "remote_echo_calc",
                "description": "Echo calculation tool",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            }
        ],
        "latency_ms": 18.5,
    }
    res_reg = client.post("/v1/mesh/nodes/register", json=peer_payload)
    assert res_reg.status_code == 201
    assert res_reg.json()["node_id"] == "test_remote_peer_node"

    # 4. POST /v1/mesh/nodes/heartbeat
    res_hb = client.post(
        "/v1/mesh/nodes/heartbeat",
        json={"node_id": "test_remote_peer_node", "latency_ms": 17.2},
    )
    assert res_hb.status_code == 200
    assert res_hb.json()["latency_ms"] == 17.2

    # 5. GET /v1/mesh/tools
    res_tools = client.get("/v1/mesh/tools")
    assert res_tools.status_code == 200
    tools = res_tools.json()
    assert any(t["name"] == "remote_echo_calc" for t in tools)

    # 6. POST /v1/mesh/tools/execute
    exec_payload = {
        "call_id": "call_mesh_01",
        "tool_name": "remote_echo_calc",
        "arguments": {"test_arg": "sample"},
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "source_cluster_id": "cluster_local",
        "target_cluster_id": "cluster_test_remote",
    }
    res_exec = client.post("/v1/mesh/tools/execute", json=exec_payload)
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["is_error"] is False
    assert "remote_echo_calc" in exec_data["content"][0]["text"]
    assert exec_data["meta"]["execution_mode"] == "remote_mesh_rpc"

    # 7. POST /v1/mesh/federation/delegate
    del_payload = {
        "target_cluster_id": container.mcp_mesh_service.local_cluster_id,
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "intent": "Verify compliance audit trail",
        "target_agent_role": "forensic_auditor",
        "max_depth": 2,
        "visited_clusters": ["external_cluster_01"],
    }
    res_del = client.post("/v1/mesh/federation/delegate", json=del_payload)
    assert res_del.status_code == 200
    del_data = res_del.json()
    assert del_data["status"] == "completed"
    assert del_data["target_cluster_id"] == container.mcp_mesh_service.local_cluster_id

    # 8. GET /v1/mesh/federation/tasks/{id}
    res_task = client.get(f"/v1/mesh/federation/tasks/{del_data['delegation_id']}")
    assert res_task.status_code == 200
    assert res_task.json()["delegation_id"] == del_data["delegation_id"]
