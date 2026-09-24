import ast
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.container import battery_service
from src.domain.abstractions.batteries import (
    BatteryCategory,
    BatteryStatus,
    PlatformBatteriesResponse,
)
from src.main import app


def test_platform_batteries_inventory_completeness():
    """Verify that all 38 platform batteries exist, have valid fields, and active status."""
    resp = battery_service.get_platform_batteries()
    assert isinstance(resp, PlatformBatteriesResponse)
    assert resp.total_batteries == 40
    assert resp.active_count >= 24
    assert len(resp.batteries) == 40

    # Check key expected battery IDs
    expected_ids = {
        "bm25_sparse_retrieval",
        "pgvector_hnsw_dense",
        "colbert_maxsim_reranker",
        "docling_layout_ocr",
        "rlm_python_repl",
        "graphrag_hdbscan_clustering",
        "neo4j_cypher_graph",
        "isolation_forest_sentinel",
        "quantile_effort_regressor",
        "kmeans_persona_classifier",
        "token_shield_rate_limiter",
        "llama_guard_safety_rails",
        "longllmlingua_compression",
        "nemo_conversational_guardrails",
        "durable_workflow_engine",
        "serverless_gpu_vllm",
        "autonomous_fde_metaprogrammer",
        "sovereign_edge_sync",
        "multicloud_failover_libsql",
        "sovereign_edge_voice",
        "zero_trust_micro_enclave",
        "autonomous_swarm_mesh",
        "universal_mcp_server",
        "react_execution_loop",
        "cognitive_agent_memory",
        "multi_agent_swarm_quorum",
        "cdc_community_connectors",
        "kubernetes_native_operator",
        "multimodal_vision_graphrag",
        "distributed_mcp_mesh",
        "mesh_load_balancer",
        "vector_raft_sharding",
        "zkp_vector_attestation",
        "enterprise_identity_federation",
        "continuous_preference_tuning",
        "confidential_mpc_enclave",
        "autonomous_benchmark_gatekeeper",
        "hierarchical_memory_got_planner",
        "enterprise_saas_connectors_acl",
        "visual_dag_workflow_composer",
    }
    actual_ids = {b.id for b in resp.batteries}
    assert expected_ids == actual_ids

    for battery in resp.batteries:
        assert battery.name
        assert battery.category in BatteryCategory
        assert battery.status in BatteryStatus
        assert battery.algorithm_foundation
        assert battery.milestone
        assert battery.latency_profile
        assert battery.description


def test_battery_categories_coverage():
    """Verify that all five architectural categories are populated."""
    resp = battery_service.get_platform_batteries()
    categories_present = {b.category for b in resp.batteries}
    assert BatteryCategory.RETRIEVAL in categories_present
    assert BatteryCategory.ML_INTELLIGENCE in categories_present
    assert BatteryCategory.SAFETY_DEFENSE in categories_present
    assert BatteryCategory.COMPUTATION_GRAPH in categories_present
    assert BatteryCategory.BACKGROUND_WORKFLOWS in categories_present


def test_admin_batteries_endpoint():
    """Verify GET /v1/admin/platform/batteries returns HTTP 200 with admin key."""
    client = TestClient(app)
    headers = {"X-Admin-Master-Key": "test_admin_key"}

    with patch("src.config.settings.ADMIN_MASTER_KEY", "test_admin_key"):
        resp = client.get("/v1/admin/platform/batteries", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_batteries"] == 40
        assert data["active_count"] >= 24
        assert len(data["batteries"]) == 40


def test_enterprise_saas_connectors_acl_battery():
    """Verify Battery #39: Turn-Key Enterprise SaaS Connectors with Document-Level ACL Inheritance."""
    resp = battery_service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "enterprise_saas_connectors_acl"), None)
    assert battery is not None
    assert "Enterprise SaaS Connectors" in battery.name
    assert battery.category == BatteryCategory.SYSTEM_EXTENSIBILITY
    assert battery.status == BatteryStatus.ACTIVE
    assert "M125" in battery.milestone
    assert "confluence" in battery.active_parameters["supported_connectors"]
    assert "jira" in battery.active_parameters["supported_connectors"]
    assert "microsoft365" in battery.active_parameters["supported_connectors"]
    assert battery.active_parameters["zero_toy_verified"] is True


def test_multimodal_vision_graphrag_battery():
    """Verify Battery #29: Multimodal Vision GraphRAG & Schematic Ingestion properties."""
    resp = battery_service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "multimodal_vision_graphrag"), None)
    assert battery is not None
    assert battery.name == "Multimodal Vision GraphRAG & Schematic Ingestion"
    assert battery.category == BatteryCategory.COMPUTATION_GRAPH
    assert battery.status == BatteryStatus.ACTIVE
    assert "M113" in battery.milestone
    assert battery.active_parameters["bounding_box_normalized"] is True


def test_kubernetes_native_operator_battery():
    """Verify Battery #28: Kubernetes Native Operator & Helm Cluster Orchestrator properties."""
    resp = battery_service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "kubernetes_native_operator"), None)
    assert battery is not None
    assert battery.name == "Kubernetes Native Operator & Helm Cluster Orchestrator"
    assert battery.category == BatteryCategory.SYSTEM_EXTENSIBILITY
    assert battery.milestone == "M112 (v1.2.0-alpha1)"
    assert battery.active_parameters["crd_group"] == "retriever.run"
    assert battery.active_parameters["crd_version"] == "v1alpha1"
    assert battery.active_parameters["helm_chart_version"] == "1.2.0-alpha1"
    assert battery.health_check_endpoint == "/v1/admin/operator/status"


def test_cdc_community_connectors_battery():
    """Verify Battery #27: Enterprise CDC & Community Connectors Ecosystem properties."""
    resp = battery_service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "cdc_community_connectors"), None)
    assert battery is not None
    assert battery.name == "Enterprise CDC & Community Connectors Ecosystem"
    assert battery.category == BatteryCategory.SYSTEM_EXTENSIBILITY
    assert battery.latency_profile == "<15ms polling & discovery overhead"
    assert "postgres_cdc" in battery.active_parameters["supported_connectors"]
    assert battery.health_check_endpoint == "/v1/admin/connectors/manifests"


def test_neo4j_cypher_graph_battery():
    """Verify Battery #14: Neo4j Cypher Labeled Property Graph Engine properties."""
    resp = battery_service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "neo4j_cypher_graph"), None)
    assert battery is not None
    assert battery.name == "Neo4j Cypher Labeled Property Graph Engine"
    assert battery.category == BatteryCategory.COMPUTATION_GRAPH
    assert battery.latency_profile == "<5ms"
    assert battery.active_parameters["fallback_engine"] == "postgres_recursive_cte"
    assert "capabilities" in (battery.health_check_endpoint or "")


def test_visual_dag_workflow_composer_battery():
    """Verify Battery #40: Visual DAG Workflow Canvas & Agentic Graph Composer properties."""
    resp = battery_service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "visual_dag_workflow_composer"), None)
    assert battery is not None
    assert battery.name == "Visual DAG Workflow Canvas & Agentic Graph Composer"
    assert battery.category == BatteryCategory.SYSTEM_EXTENSIBILITY
    assert battery.status == BatteryStatus.ACTIVE
    assert "kahn_topological_sort" in battery.active_parameters["compiler_algorithm"]
    assert battery.active_parameters["enterprise_templates_count"] == 4
    assert battery.active_parameters["zero_toy_verified"] is True
    assert "/workflows/dag/templates" in (battery.health_check_endpoint or "")


def test_hexagonal_architecture_batteries():
    """Ensure domain/batteries and abstractions/batteries have zero forbidden imports."""
    domain_file = os.path.join(os.path.dirname(__file__), "../src/domain/batteries/battery_service.py")
    abstraction_file = os.path.join(os.path.dirname(__file__), "../src/domain/abstractions/batteries.py")

    for filepath in [domain_file, abstraction_file]:
        with open(filepath) as f:
            tree = ast.parse(f.read(), filename=filepath)

        forbidden_prefixes = ("src.adapters", "src.routers", "sqlalchemy", "fastapi")
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
