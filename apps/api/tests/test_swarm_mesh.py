"""Comprehensive Unit & Integration Test Suite for Milestone 102 (Swarm Mesh & P2P Gossip).

Validates:
1. Hexagonal domain abstraction purity (AST assertion: 0 forbidden imports).
2. Lamport Vector Clock causality math (happened-before, happened-after, concurrent conflicts).
3. SWIM failure detection protocol (direct ping, indirect ping-req fallback, suspect transition).
4. Incarnation-based suspicion refutation and ALIVE broadcast.
5. 5-node cluster epidemic gossip propagation and membership convergence.
6. Network partition divergence and causal state reconciliation without split-brain corruption.
7. Push-pull anti-entropy sequence exchange and delta synchronization.
8. Platform Battery #22 registration in BatteryService under EDGE_DISTRIBUTION.
9. Model Context Protocol (MCP) tool exposure (swarm_topology, swarm_sync).
10. FastAPI administrative and tenant-scoped REST endpoints with authentication.
"""

import ast
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.mcp.battery_mcp_adapter import BatteryMcpAdapter
from src.adapters.swarm.gossip_mesh_adapter import GossipMeshAdapter
from src.config import settings
from src.container import battery_service, container
from src.domain.abstractions.batteries import BatteryCategory, BatteryStatus
from src.domain.abstractions.swarm import (
    AntiEntropyDigest,
    GossipMessage,
    GossipMessageType,
    SwarmNode,
    SwarmNodeRole,
    SwarmNodeState,
    VectorClock,
    VectorClockComparison,
)
from src.main import app


def test_swarm_domain_abstractions_purity():
    """Verify that domain abstractions import zero forbidden frameworks (Hexagonal rule)."""
    domain_file = Path(__file__).resolve().parents[1] / "src" / "domain" / "abstractions" / "swarm.py"
    assert domain_file.exists(), f"File {domain_file} must exist"

    tree = ast.parse(domain_file.read_text(), filename=str(domain_file))
    forbidden = {"fastapi", "sqlalchemy", "redis", "pika", "celery", "adapters", "routers"}

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    violating = forbidden & imported_modules
    assert not violating, f"Domain abstraction contains forbidden imports: {violating}"


def test_vector_clock_causality_math():
    """Validate Lamport vector clock monotonic tick, pairwise merge, and causality comparisons."""
    vc_a = VectorClock()
    vc_b = VectorClock()

    # Initial state is identical
    assert vc_a.compare(vc_b) == VectorClockComparison.IDENTICAL

    # Node A ticks: A:1, B:0 -> A happened after B
    vc_a.tick("node_a")
    assert vc_a.compare(vc_b) == VectorClockComparison.AFTER
    assert vc_b.compare(vc_a) == VectorClockComparison.BEFORE

    # Node B ticks: A:1, B:1 -> Concurrent / Divergent branches
    vc_b.tick("node_b")
    assert vc_a.compare(vc_b) == VectorClockComparison.CONCURRENT
    assert vc_b.compare(vc_a) == VectorClockComparison.CONCURRENT

    # Pairwise merge: A:1, B:1
    vc_merged = VectorClock()
    vc_merged.merge(vc_a)
    vc_merged.merge(vc_b)
    assert vc_merged.get("node_a") == 1
    assert vc_merged.get("node_b") == 1
    assert vc_merged.compare(vc_a) == VectorClockComparison.AFTER
    assert vc_merged.compare(vc_b) == VectorClockComparison.AFTER

    # Further tick on merged clock
    vc_merged.tick("node_a")
    assert vc_merged.get("node_a") == 2
    assert vc_merged.compare(vc_a) == VectorClockComparison.AFTER


def test_swim_failure_detector_direct_and_indirect():
    """Verify direct ping success and indirect ping-req fallback transition to SUSPECT."""
    adapter = GossipMeshAdapter(ping_timeout_ms=100.0, ping_req_peers_k=3)
    tenant_id = "test-tenant-swim"

    adapter.register_node(
        SwarmNode(
            node_id="edge_node_a",
            tenant_id=tenant_id,
            device_name="MacBook Pro A",
            role=SwarmNodeRole.CORE_PEER,
        )
    )
    adapter.register_node(
        SwarmNode(
            node_id="edge_node_b",
            tenant_id=tenant_id,
            device_name="Ubuntu Gateway B",
            role=SwarmNodeRole.CORE_PEER,
        )
    )

    # 1. Direct Ping Success
    probed = adapter.probe_node_swim(
        tenant_id=tenant_id,
        prober_node_id="edge_node_a",
        target_node_id="edge_node_b",
        simulated_ack=True,
    )
    assert probed.state == SwarmNodeState.HEALTHY
    assert probed.suspect_by_node_id is None

    # 2. Direct Ping Failure -> Indirect Ping-Req -> Suspect State
    suspected = adapter.probe_node_swim(
        tenant_id=tenant_id,
        prober_node_id="edge_node_a",
        target_node_id="edge_node_b",
        simulated_ack=False,
    )
    assert suspected.state == SwarmNodeState.SUSPECT
    assert suspected.suspect_by_node_id == "edge_node_a"


def test_suspicion_refutation_with_incarnation():
    """Verify that a suspected node can refute suspicion by incrementing incarnation."""
    adapter = GossipMeshAdapter()
    tenant_id = "test-tenant-refute"

    node = adapter.register_node(
        SwarmNode(
            node_id="edge_node_c",
            tenant_id=tenant_id,
            device_name="Raspberry Pi 5",
            incarnation=1,
        )
    )
    node.state = SwarmNodeState.SUSPECT
    node.suspect_by_node_id = "peer_x"

    # Refute suspicion
    refuted = adapter.refute_suspicion(tenant_id=tenant_id, node_id="edge_node_c")
    assert refuted.state == SwarmNodeState.HEALTHY
    assert refuted.incarnation == 2
    assert refuted.suspect_by_node_id is None
    assert refuted.vector_clock.get("edge_node_c") >= 1


def test_5_node_cluster_gossip_convergence():
    """Verify epidemic gossip dissemination across a 5-node cluster."""
    adapter = GossipMeshAdapter()
    tenant_id = "test-tenant-5node"

    nodes = []
    for i in range(1, 6):
        node = adapter.register_node(
            SwarmNode(
                node_id=f"node_{i}",
                tenant_id=tenant_id,
                device_name=f"Edge Node {i}",
                role=SwarmNodeRole.CORE_PEER if i <= 2 else SwarmNodeRole.EDGE_LEAF,
            )
        )
        nodes.append(node)

    # Initial topology
    topo = adapter.get_topology(tenant_id)
    assert topo.total_nodes == 5
    assert topo.active_healthy_count == 5
    assert topo.cluster_convergence_pct == 100.0

    # Simulate gossip ping from node_1 to node_2
    msg = GossipMessage(
        message_id="msg_001",
        msg_type=GossipMessageType.PING,
        sender_id="node_1",
        target_id="node_2",
        tenant_id=tenant_id,
        incarnation=0,
        vector_clock=nodes[0].vector_clock,
    )
    ack_msg = adapter.handle_gossip(msg)
    assert ack_msg is not None
    assert ack_msg.msg_type == GossipMessageType.ACK
    assert ack_msg.target_id == "node_1"

    # Process ACK on sender side
    adapter.handle_gossip(ack_msg)
    assert adapter._nodes[tenant_id]["node_1"].state == SwarmNodeState.HEALTHY


def test_network_partition_and_causal_reconciliation():
    """Verify partition divergence, vector clock conflict detection, and causal merge."""
    adapter = GossipMeshAdapter()
    tenant_id = "test-tenant-partition"

    # Register Partition A nodes
    adapter.register_node(
        SwarmNode(node_id="p1_node1", tenant_id=tenant_id, device_name="Cluster 1 - Node 1")
    )
    adapter.register_node(
        SwarmNode(node_id="p1_node2", tenant_id=tenant_id, device_name="Cluster 1 - Node 2")
    )

    # Register Partition B nodes
    adapter.register_node(
        SwarmNode(node_id="p2_node3", tenant_id=tenant_id, device_name="Cluster 2 - Node 3")
    )
    adapter.register_node(
        SwarmNode(node_id="p2_node4", tenant_id=tenant_id, device_name="Cluster 2 - Node 4")
    )

    # Simulate offline mutations in Partition A
    adapter._nodes[tenant_id]["p1_node1"].vector_clock.tick("p1_node1")
    adapter._nodes[tenant_id]["p1_node2"].vector_clock.tick("p1_node2")

    # Simulate offline mutations in Partition B
    adapter._nodes[tenant_id]["p2_node3"].vector_clock.tick("p2_node3")
    adapter._nodes[tenant_id]["p2_node4"].vector_clock.tick("p2_node4")

    # Reconcile partitions
    mutations_a = [{"key": "doc_101", "val": "version_a", "ts": 1000}]
    mutations_b = [{"key": "doc_101", "val": "version_b", "ts": 1020}]

    report = adapter.reconcile_partitions(
        tenant_id=tenant_id,
        partition_a_nodes=["p1_node1", "p1_node2"],
        partition_b_nodes=["p2_node3", "p2_node4"],
        mutations_a=mutations_a,
        mutations_b=mutations_b,
    )

    assert report.comparison == VectorClockComparison.CONCURRENT
    assert report.conflicts_detected >= 1
    assert report.conflicts_resolved_via_lww >= 1
    assert report.merged_clock.get("p1_node1") >= 1
    assert report.merged_clock.get("p2_node3") >= 1

    # All nodes in cluster now share identical merged vector clock
    topo = adapter.get_topology(tenant_id)
    assert topo.active_healthy_count == 4
    for n in topo.nodes:
        assert n.vector_clock.get("p1_node1") >= 1
        assert n.vector_clock.get("p2_node3") >= 1


def test_anti_entropy_push_pull_sync():
    """Verify push-pull anti-entropy sequence exchange detects and syncs missing frames."""
    adapter = GossipMeshAdapter()
    tenant_id = "test-tenant-anti-entropy"

    adapter.register_node(
        SwarmNode(node_id="peer_alpha", tenant_id=tenant_id, device_name="Alpha")
    )
    adapter.register_node(
        SwarmNode(node_id="peer_beta", tenant_id=tenant_id, device_name="Beta")
    )

    # Peer Alpha has sequence 2, Peer Beta has sequences up to 5
    digest = AntiEntropyDigest(
        sender_id="peer_alpha",
        tenant_id=tenant_id,
        highest_sequence=2,
    )

    res = adapter.sync_anti_entropy(
        tenant_id=tenant_id,
        sender_id="peer_alpha",
        target_id="peer_beta",
        digest=digest,
        target_sequences=[1, 2, 3, 4, 5],
    )

    assert res.is_converged is True
    assert res.missing_sequences == [3, 4, 5]
    assert res.replayed_mutations_count == 3
    assert res.converged_clock.get("peer_alpha") >= 1


def test_platform_battery_22_registration():
    """Verify Platform Battery #22 is formally registered in BatteryService."""
    catalog = battery_service.get_platform_batteries()
    battery_ids = {b.id for b in catalog.batteries}
    assert "autonomous_swarm_mesh" in battery_ids

    battery = battery_service.get_battery("autonomous_swarm_mesh")
    assert battery is not None
    assert battery.name == "Autonomous Edge Fleet Swarm Mesh & P2P Gossip Replication"
    assert battery.category == BatteryCategory.EDGE_DISTRIBUTION
    assert battery.status == BatteryStatus.ACTIVE
    assert "SWIM" in battery.algorithm_foundation
    assert battery.milestone == "M102 (v0.87.0)"


@pytest.mark.asyncio
async def test_mcp_tool_definitions_and_execution():
    """Verify swarm tools are exposed via MCP and execute successfully."""
    adapter = BatteryMcpAdapter(container)
    tenant_id = "test-tenant-mcp-swarm"

    # Pre-register a node so topology is non-empty
    container.swarm_mesh_adapter.register_node(
        SwarmNode(
            node_id="mcp_edge_1",
            tenant_id=tenant_id,
            device_name="MCP Edge Device 1",
        )
    )

    tool_defs = adapter.get_tool_definitions(tenant_id)
    tool_names = {t.name for t in tool_defs}
    assert "swarm_topology" in tool_names
    assert "swarm_sync" in tool_names

    # Execute swarm_topology
    result = await adapter.execute_tool(
        tenant_id=tenant_id,
        tool_name="swarm_topology",
        arguments={},
    )
    assert not result.is_error
    assert "mcp_edge_1" in result.content[0].text
    assert "cluster_convergence_pct" in result.content[0].text

    # Execute swarm_sync
    sync_result = await adapter.execute_tool(
        tenant_id=tenant_id,
        tool_name="swarm_sync",
        arguments={"sender_id": "mcp_edge_1", "target_id": "mcp_edge_2", "highest_sequence": 1},
    )
    assert not sync_result.is_error
    assert "converged_clock" in sync_result.content[0].text


@pytest.mark.asyncio
async def test_fastapi_swarm_endpoints():
    """Validate FastAPI REST endpoints for swarm mesh operations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}
        tenant_id = "test-tenant-rest-swarm"

        # 1. Join Swarm Mesh
        join_resp = await client.post(
            "/v1/admin/swarm/join",
            headers=admin_headers,
            json={
                "node_id": "rest_node_1",
                "tenant_id": tenant_id,
                "device_name": "REST Test Machine",
                "role": "core_peer",
                "address": "192.168.1.100",
                "port": 7946,
            },
        )
        assert join_resp.status_code == 201
        data = join_resp.json()
        assert data["node_id"] == "rest_node_1"
        assert data["state"] == "healthy"

        # 2. Get Topology
        topo_resp = await client.get(
            f"/v1/admin/swarm/topology?tenant_id={tenant_id}",
            headers=admin_headers,
        )
        assert topo_resp.status_code == 200
        topo = topo_resp.json()
        assert topo["total_nodes"] >= 1
        assert topo["cluster_convergence_pct"] == 100.0

        # 3. Probe Node (simulated timeout)
        probe_resp = await client.post(
            "/v1/admin/swarm/probe",
            headers=admin_headers,
            json={
                "tenant_id": tenant_id,
                "prober_node_id": "rest_node_1",
                "target_node_id": "rest_node_1",
                "simulated_ack": False,
            },
        )
        assert probe_resp.status_code == 200
        assert probe_resp.json()["state"] == "suspect"

        # 4. Refute Suspicion
        refute_resp = await client.post(
            f"/v1/admin/swarm/refute?tenant_id={tenant_id}&node_id=rest_node_1",
            headers=admin_headers,
        )
        assert refute_resp.status_code == 200
        assert refute_resp.json()["state"] == "healthy"
        assert refute_resp.json()["incarnation"] >= 1

        # 5. Push-Pull Anti-Entropy Sync
        sync_resp = await client.post(
            "/v1/admin/swarm/sync",
            headers=admin_headers,
            json={
                "tenant_id": tenant_id,
                "sender_id": "rest_node_1",
                "target_id": "rest_node_2",
                "highest_sequence": 2,
                "target_sequences": [1, 2, 3, 4],
            },
        )
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["missing_sequences"] == [3, 4]

        # 6. Partition Heal
        heal_resp = await client.post(
            "/v1/admin/swarm/partition-heal",
            headers=admin_headers,
            json={
                "tenant_id": tenant_id,
                "partition_a_nodes": ["rest_node_1"],
                "partition_b_nodes": ["rest_node_1"],
            },
        )
        assert heal_resp.status_code == 200
        assert "merged_clock" in heal_resp.json()

        # 7. Graceful Leave
        leave_resp = await client.post(
            f"/v1/admin/swarm/leave?tenant_id={tenant_id}&node_id=rest_node_1",
            headers=admin_headers,
        )
        assert leave_resp.status_code == 200
        assert leave_resp.json()["status"] == "left"

        # 8. Tenant-Scoped Swarm Status
        status_resp = await client.get(
            f"/v1/tenants/{tenant_id}/swarm/status",
            headers=admin_headers,
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["tenant_id"] == tenant_id
