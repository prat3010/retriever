"""Unit tests for 2026 Agentic Query Planning and Multi-Step Execution Loops."""

import pytest

from src.domain.abstractions.react import ReActEventType, ReActLoopConfig
from src.domain.agentic.query_planner import (
    AgenticPlanOrchestrator,
    AgenticQueryPlanner,
    PlanStepType,
)
from src.domain.agentic.react_engine import ReActExecutionEngine
from src.domain.agentic.tool_registry import ToolRegistry


def test_query_planner_comparative_decomposition():
    planner = AgenticQueryPlanner()
    query = "Compare PostgreSQL Row-Level Security vs Redis in-memory caching"
    plan = planner.decompose_query(query, tenant_id="test_tenant")

    assert plan.complexity == "comparative"
    assert plan.is_multi_step is True
    assert len(plan.steps) == 3

    step_1, step_2, step_3 = plan.steps
    assert step_1.step_type == PlanStepType.RETRIEVAL
    assert "PostgreSQL Row-Level Security" in step_1.query
    assert step_2.step_type == PlanStepType.RETRIEVAL
    assert "Redis in-memory caching" in step_2.query
    assert step_3.step_type == PlanStepType.SYNTHESIS
    assert step_3.depends_on == ["step_1", "step_2"]


def test_query_planner_analytical_decomposition():
    planner = AgenticQueryPlanner()
    query = "Calculate total revenue and invoice amounts in Q3"
    plan = planner.decompose_query(query, tenant_id="test_tenant")

    assert plan.complexity == "analytical"
    assert plan.is_multi_step is True
    assert len(plan.steps) == 3

    step_1, step_2, step_3 = plan.steps
    assert step_1.step_type == PlanStepType.RETRIEVAL
    assert step_2.step_type == PlanStepType.TOOL_CALL
    assert step_2.tool_name in {"table_query", "calculator"}
    assert step_3.step_type == PlanStepType.SYNTHESIS


def test_query_planner_multi_hop_decomposition():
    planner = AgenticQueryPlanner()
    query = "Find the primary admin email for tenant alpha and then check their active API quota"
    plan = planner.decompose_query(query, tenant_id="test_tenant")

    assert plan.complexity == "multi_hop"
    assert plan.is_multi_step is True
    assert len(plan.steps) == 3

    step_1, step_2, step_3 = plan.steps
    assert step_1.step_type == PlanStepType.RETRIEVAL
    assert step_2.step_type == PlanStepType.RETRIEVAL
    assert "step_1" in step_2.depends_on
    assert step_3.step_type == PlanStepType.SYNTHESIS


def test_query_planner_simple_single_hop():
    planner = AgenticQueryPlanner()
    query = "What is the p95 latency SLA for search queries?"
    plan = planner.decompose_query(query, tenant_id="test_tenant")

    assert plan.complexity == "simple"
    assert plan.is_multi_step is False
    assert len(plan.steps) == 2
    assert plan.steps[0].step_type == PlanStepType.RETRIEVAL
    assert plan.steps[1].step_type == PlanStepType.SYNTHESIS


@pytest.mark.asyncio
async def test_agentic_plan_orchestrator_execution():
    planner = AgenticQueryPlanner()
    orchestrator = AgenticPlanOrchestrator()

    query = "Compare HNSW vector search and BM25 keyword search"
    plan = planner.decompose_query(query, tenant_id="tenant_123")

    mock_db = {
        "HNSW vector search": ["HNSW provides sub-linear dense vector search over embeddings."],
        "BM25 keyword search": ["BM25 provides inverted index lexical keyword matching."],
    }

    def mock_search(sub_q: str, tenant_id: str, top_k: int = 5):
        for k, v in mock_db.items():
            if k in sub_q:
                return v
        return ["Default contextual document."]

    res = await orchestrator.execute_plan(plan, search_fn=mock_search)

    assert res.success is True
    assert res.tenant_id == "tenant_123"
    assert len(res.step_records) == 3
    assert len(res.aggregated_contexts) == 2
    assert "HNSW provides sub-linear" in res.final_answer or "Based on retrieved documentation" in res.final_answer


@pytest.mark.asyncio
async def test_table_query_tool_operations():
    registry = ToolRegistry()
    table_md = """| Plan | Monthly Fee | Max Tenants | Support |
| --- | --- | --- | --- |
| Starter | $49 | 5 | Community |
| Growth | $199 | 25 | Priority |
| Enterprise | $999 | 100 | 24/7 Dedicated |
"""

    # 1. Filter rows
    r_filter = await registry.execute_tool(
        call_id="c1",
        tool_name="table_query",
        arguments={"table_markdown": table_md, "column": "Plan", "filter_value": "Growth"},
    )
    assert r_filter.is_error is False
    assert "Growth" in str(r_filter.output)
    assert "$199" in str(r_filter.output)

    # 2. Sum operation
    r_sum = await registry.execute_tool(
        call_id="c2",
        tool_name="table_query",
        arguments={"table_markdown": table_md, "column": "Monthly Fee", "operation": "sum"},
    )
    assert r_sum.is_error is False
    # 49 + 199 + 999 = 1247.00
    assert "1247.00" in str(r_sum.output)

    # 3. Columns inspection
    r_cols = await registry.execute_tool(
        call_id="c3",
        tool_name="table_query",
        arguments={"table_markdown": table_md, "operation": "columns"},
    )
    assert r_cols.is_error is False
    assert "Plan, Monthly Fee, Max Tenants, Support" in str(r_cols.output)


@pytest.mark.asyncio
async def test_react_engine_query_planning_event_emission():
    # Mock LLM provider that halts after 1 turn
    class MockLlm:
        async def generate(self, req, *args, **kwargs):
            from types import SimpleNamespace

            return SimpleNamespace(
                content='{"thought": "Plan completed", "tool_calls": [], "final_answer": "Done"}'
            )

    engine = ReActExecutionEngine(llm_provider=MockLlm())
    config = ReActLoopConfig(enable_query_planning=True, max_turns=2)

    events = []
    async for event in engine.run_loop_stream(
        tenant_id="tenant_abc",
        query="Compare Azure and AWS multi-cloud deployments",
        config=config,
    ):
        events.append(event)

    # Verify that QUERY_PLAN event was emitted
    event_types = [e.event_type for e in events]
    assert ReActEventType.QUERY_PLAN in event_types
    plan_event = next(e for e in events if e.event_type == ReActEventType.QUERY_PLAN)
    assert plan_event.data["complexity"] == "comparative"
    assert len(plan_event.data["steps"]) == 3


@pytest.mark.asyncio
async def test_agentic_plan_orchestrator_analytical_execution():
    planner = AgenticQueryPlanner()
    orchestrator = AgenticPlanOrchestrator()
    plan = planner.decompose_query("Calculate total invoice amount", tenant_id="tenant_123")

    def mock_search(*args, **kwargs):
        return [
            "| Invoice | Amount |\n| --- | --- |\n| INV-01 | $500 |\n| INV-02 | $750 |"
        ]

    res = await orchestrator.execute_plan(plan, search_fn=mock_search)
    assert res.success is True
    assert len(res.step_records) == 3
    # Step 2 must be completed and computed sum
    s2 = res.step_records[1]
    assert s2.status == "completed"
    assert "1250.00" in str(s2.output)
    assert "1250.00" in res.final_answer


@pytest.mark.asyncio
async def test_table_query_multi_table_isolation():
    registry = ToolRegistry()
    multi_table_doc = """
# Summary
| Dept | Headcount |
| --- | --- |
| Eng | 40 |

# Invoices
| ID | Amount |
| --- | --- |
| A | 100 |
| B | 200 |
"""
    res = await registry.execute_tool(
        call_id="c_multi",
        tool_name="table_query",
        arguments={"table_markdown": multi_table_doc, "column": "Amount", "operation": "sum"},
    )
    assert res.is_error is False
    assert "300.00" in str(res.output)


@pytest.mark.asyncio
async def test_agentic_plan_orchestrator_search_result_objects():
    from src.domain.abstractions.retrieval import SearchResult

    planner = AgenticQueryPlanner()
    orchestrator = AgenticPlanOrchestrator()
    plan = planner.decompose_query("What is our disaster recovery RTO?", tenant_id="t_dr")

    def mock_search_objects(*args, **kwargs):
        return [
            SearchResult(
                chunk_id="chunk_dr_1",
                document_id="doc_dr_1",
                content="Our disaster recovery RTO is 15 minutes.",
                score=0.98,
            )
        ]

    res = await orchestrator.execute_plan(plan, search_fn=mock_search_objects)
    assert res.success is True
    assert "15 minutes" in res.final_answer


@pytest.mark.asyncio
async def test_multi_step_retrieval_deduplication():
    registry = ToolRegistry()
    res = await registry.execute_tool(
        call_id="c_dedup",
        tool_name="multi_step_retrieval",
        arguments={"sub_queries": ["query A", "query A"], "top_k": 3},
    )
    assert res.is_error is False
    # Deduplication ensures identical result isn't repeated twice
    assert "Sub-query 'query A'" in str(res.output)

