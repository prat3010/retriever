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
    """Verify that all 15 platform batteries exist, have valid fields, and active status."""
    resp = battery_service.get_platform_batteries()
    assert isinstance(resp, PlatformBatteriesResponse)
    assert resp.total_batteries == 15
    assert resp.active_count >= 12
    assert len(resp.batteries) == 15

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
        assert data["total_batteries"] == 15
        assert data["active_count"] >= 12
        assert len(data["batteries"]) == 15



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
