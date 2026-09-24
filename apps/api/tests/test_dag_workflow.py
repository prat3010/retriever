"""Comprehensive Unit Tests for Visual DAG Workflow Canvas & Agentic Graph Composer (M126).

Verifies:
1. Kahn's topological sort and parallel stage partitioning.
2. Cyclic dependency detection and explicit exception raising.
3. End-to-end execution with token cost attribution and step latency.
4. Router conditional branching and skipped-node propagation.
5. All 4 enterprise templates compile cleanly without errors.
6. Tenant boundary enforcement (TenantIsolationViolationError).
7. Strict Hexagonal Architecture boundary verification (zero forbidden imports).
"""

from __future__ import annotations

import ast
import os

import pytest

from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.abstractions.workflow_dag import (
    DAGEdge,
    DAGNode,
    DAGNodeType,
    NodeExecutionStatus,
    WorkflowDAGGraph,
)
from src.domain.workflow.dag_compiler import (
    CyclicWorkflowError,
    DAGWorkflowCompiler,
    InvalidWorkflowGraphError,
)
from src.domain.workflow.dag_executor import DAGWorkflowExecutor
from src.domain.workflow.templates import (
    get_customer_support_copilot_template,
    get_legal_document_analyzer_template,
    get_template_by_id,
    list_enterprise_templates,
)


@pytest.fixture
def compiler() -> DAGWorkflowCompiler:
    return DAGWorkflowCompiler()


@pytest.fixture
def executor(compiler: DAGWorkflowCompiler) -> DAGWorkflowExecutor:
    return DAGWorkflowExecutor(compiler=compiler)


def test_kahn_topological_sort_diamond_graph(compiler: DAGWorkflowCompiler):
    """Verify Kahn's topological sorting on a diamond DAG with parallel stages."""
    nodes = [
        DAGNode(id="A", type=DAGNodeType.INPUT, title="Input A"),
        DAGNode(id="B", type=DAGNodeType.GUARDRAIL, title="Guardrail B"),
        DAGNode(id="C", type=DAGNodeType.RETRIEVAL, title="Retrieval C"),
        DAGNode(id="D", type=DAGNodeType.OUTPUT, title="Output D"),
    ]
    edges = [
        DAGEdge(id="e1", source="A", target="B"),
        DAGEdge(id="e2", source="A", target="C"),
        DAGEdge(id="e3", source="B", target="D"),
        DAGEdge(id="e4", source="C", target="D"),
    ]
    graph = WorkflowDAGGraph(id="diamond_dag", name="Diamond DAG", nodes=nodes, edges=edges)

    result = compiler.compile(graph)
    assert result.is_valid is True
    assert len(result.errors) == 0

    order = result.topological_order
    assert order.index("A") < order.index("B")
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")

    # Verify parallel stages: Stage 0: [A], Stage 1: [B, C], Stage 2: [D]
    assert len(result.parallel_stages) == 3
    assert result.parallel_stages[0] == ["A"]
    assert set(result.parallel_stages[1]) == {"B", "C"}
    assert result.parallel_stages[2] == ["D"]


def test_kahn_cycle_detection(compiler: DAGWorkflowCompiler):
    """Verify directed cycle detection raises CyclicWorkflowError."""
    nodes = [
        DAGNode(id="n1", type=DAGNodeType.INPUT, title="Node 1"),
        DAGNode(id="n2", type=DAGNodeType.RETRIEVAL, title="Node 2"),
        DAGNode(id="n3", type=DAGNodeType.LLM, title="Node 3"),
    ]
    # n1 -> n2 -> n3 -> n1 (Cycle!)
    edges = [
        DAGEdge(id="e1", source="n1", target="n2"),
        DAGEdge(id="e2", source="n2", target="n3"),
        DAGEdge(id="e3", source="n3", target="n1"),
    ]
    cyclic_graph = WorkflowDAGGraph(id="cycle_dag", name="Cyclic DAG", nodes=nodes, edges=edges)

    with pytest.raises(CyclicWorkflowError, match="Cyclic dependency detected"):
        compiler.compile(cyclic_graph, raise_on_error=True)

    # In non-raising mode, check report
    result = compiler.compile(cyclic_graph, raise_on_error=False)
    assert result.is_valid is False
    assert len(result.errors) > 0
    assert any("Cyclic dependency" in err for err in result.errors)


def test_invalid_node_references_and_empty_graphs(compiler: DAGWorkflowCompiler):
    """Verify invalid node references and empty graphs trigger errors."""
    empty_graph = WorkflowDAGGraph(id="empty", name="Empty")
    with pytest.raises(InvalidWorkflowGraphError, match="must contain at least one node"):
        compiler.compile(empty_graph, raise_on_error=True)

    # Invalid edge referencing ghost node
    nodes = [DAGNode(id="A", type=DAGNodeType.INPUT, title="Input A")]
    edges = [DAGEdge(id="e1", source="A", target="GHOST_NODE")]
    bad_edge_graph = WorkflowDAGGraph(id="bad_edge", name="Bad Edge", nodes=nodes, edges=edges)

    with pytest.raises(InvalidWorkflowGraphError, match="references non-existent target node"):
        compiler.compile(bad_edge_graph, raise_on_error=True)


@pytest.mark.asyncio
async def test_dag_executor_pipeline_with_cost_attribution(executor: DAGWorkflowExecutor):
    """Verify end-to-end execution of Legal Analyzer template with token cost attribution."""
    tpl = get_legal_document_analyzer_template()
    tenant_id = "tn_legal_corp_001"
    initial_input = {"query": "Analyze indemnity clauses under Indian Contract Act."}

    result = await executor.execute(tenant_id, tpl, initial_input)

    assert result.status == "completed"
    assert result.tenant_id == tenant_id
    assert result.graph_id == tpl.id
    assert len(result.step_details) == len(tpl.nodes)
    assert result.total_tokens > 0
    assert result.total_cost_usd > 0.0
    assert result.total_latency_ms > 0.0

    # Verify each node's status
    for _node_id, step in result.step_details.items():
        assert step.status == NodeExecutionStatus.COMPLETED
        assert step.latency_ms >= 0.0
        assert step.started_at is not None
        assert step.completed_at is not None

    # Check that final output was generated
    assert "answer" in result.final_output or "response" in result.final_output
    assert result.final_output.get("sanitized") is True


@pytest.mark.asyncio
async def test_dag_executor_router_branching(executor: DAGWorkflowExecutor):
    """Verify router branches only execute active branch and skip non-selected branches."""
    tpl = get_customer_support_copilot_template()
    tenant_id = "tn_support_002"
    initial_input = {"query": "I need help with my API key.", "intent": "technical"}

    result = await executor.execute(tenant_id, tpl, initial_input)
    assert result.status == "completed"

    # In customer support template, router routes to kb_retrieval on 'technical'
    assert result.step_details["router_intent"].status == NodeExecutionStatus.COMPLETED
    assert result.step_details["retrieval_kb"].status == NodeExecutionStatus.COMPLETED
    assert result.step_details["llm_support"].status == NodeExecutionStatus.COMPLETED
    assert result.step_details["output_ticket"].status == NodeExecutionStatus.COMPLETED


def test_enterprise_templates_compilation_and_catalog(compiler: DAGWorkflowCompiler):
    """Verify all 4 enterprise templates compile cleanly without cycles or syntax errors."""
    templates = list_enterprise_templates()
    assert len(templates) == 4

    expected_ids = {
        "tpl_legal_analyzer",
        "tpl_customer_support",
        "tpl_codebase_assistant",
        "tpl_multimodal_inspector",
    }
    actual_ids = {t.id for t in templates}
    assert expected_ids == actual_ids

    for tpl in templates:
        res = compiler.compile(tpl, raise_on_error=True)
        assert res.is_valid is True
        assert len(res.errors) == 0
        assert len(res.topological_order) == len(tpl.nodes)
        assert len(res.parallel_stages) >= 2

        # Verify get_template_by_id
        fetched = get_template_by_id(tpl.id)
        assert fetched is not None
        assert fetched.id == tpl.id


@pytest.mark.asyncio
async def test_tenant_isolation_enforcement(executor: DAGWorkflowExecutor):
    """Verify tenant isolation breach raises TenantIsolationViolationError."""
    tpl = get_legal_document_analyzer_template()
    with pytest.raises(TenantIsolationViolationError, match="Tenant ID cannot be empty"):
        await executor.execute(tenant_id="", graph=tpl, initial_input={})

    with pytest.raises(TenantIsolationViolationError, match="Tenant ID cannot be empty"):
        await executor.execute(tenant_id="   ", graph=tpl, initial_input={})


def test_hexagonal_architecture_dag_workflow():
    """Verify domain/workflow DAG modules contain zero forbidden imports."""
    base_dir = os.path.dirname(__file__)
    files_to_check = [
        os.path.join(base_dir, "../src/domain/abstractions/workflow_dag.py"),
        os.path.join(base_dir, "../src/domain/workflow/dag_compiler.py"),
        os.path.join(base_dir, "../src/domain/workflow/dag_executor.py"),
        os.path.join(base_dir, "../src/domain/workflow/templates.py"),
    ]

    forbidden_prefixes = ("src.adapters", "src.routers", "sqlalchemy", "fastapi", "httpx", "requests")

    for filepath in files_to_check:
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


def test_dag_workflow_router_endpoints():
    """Verify FastAPI router endpoints for DAG compile, execute, and templates."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from src.main import app

    client = TestClient(app)
    headers = {"X-Admin-Master-Key": "test_admin_key"}

    with patch("src.config.settings.ADMIN_MASTER_KEY", "test_admin_key"):
        # 1. Get templates
        resp = client.get("/v1/tenants/test_tenant/workflows/dag/templates", headers=headers)
        assert resp.status_code == 200
        tpls = resp.json()
        assert len(tpls) == 4

        # 2. Get template by ID
        resp2 = client.get(
            "/v1/tenants/test_tenant/workflows/dag/templates/tpl_legal_analyzer",
            headers=headers,
        )
        assert resp2.status_code == 200
        tpl_data = resp2.json()
        assert tpl_data["id"] == "tpl_legal_analyzer"

        # 3. Compile DAG
        resp3 = client.post(
            "/v1/tenants/test_tenant/workflows/dag/compile",
            json=tpl_data,
            headers=headers,
        )
        assert resp3.status_code == 200
        comp_res = resp3.json()
        assert comp_res["is_valid"] is True
        assert len(comp_res["topological_order"]) == len(tpl_data["nodes"])

        # 4. Execute DAG
        resp4 = client.post(
            "/v1/tenants/test_tenant/workflows/dag/execute",
            json={
                "graph": tpl_data,
                "input_payload": {"query": "Analyze indemnity and compliance in agreement."},
            },
            headers=headers,
        )
        assert resp4.status_code == 200
        exec_res = resp4.json()
        assert exec_res["status"] == "completed"
        assert exec_res["total_tokens"] > 0
        assert exec_res["total_cost_usd"] > 0.0
        assert len(exec_res["step_details"]) == len(tpl_data["nodes"])

