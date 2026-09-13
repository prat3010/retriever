"""Test suite for Smart Tool Gateway & Multi-Model Economic Orchestrator (Milestone 105).

Validates:
1. Hexagonal boundary purity of economic_orchestrator abstractions.
2. Complexity classification accuracy across simple, multi-hop, and code prompts.
3. Mid-flight escalation triggers (step threshold, circuit breaker, self-healing failure).
4. Counterfactual economic ledger accounting, savings math, and tenant isolation.
5. FastAPI gateway endpoints for classification and ledger metrics.
"""

import ast
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.domain.abstractions.economic_orchestrator import (
    EscalationReason,
    ModelTier,
)
from src.domain.agentic.smart_tool_router import SmartToolRouter
from src.main import app


def test_economic_orchestrator_hexagonal_purity():
    """Verify economic_orchestrator has ZERO framework, database, or adapter imports."""
    domain_file = (
        Path(__file__).parent.parent
        / "src"
        / "domain"
        / "abstractions"
        / "economic_orchestrator.py"
    )
    assert domain_file.exists(), f"Domain abstraction file not found: {domain_file}"

    tree = ast.parse(domain_file.read_text())
    forbidden_prefixes = (
        "src.adapters",
        "src.routers",
        "src.infrastructure",
        "fastapi",
        "sqlalchemy",
        "redis",
        "httpx",
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert not name.name.startswith(forbidden_prefixes), (
                    f"Forbidden import in domain abstraction: {name.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not node.module.startswith(forbidden_prefixes), (
                    f"Forbidden import in domain abstraction: {node.module}"
                )


def test_complexity_classification_simple_lookup():
    """Verify routine lookup prompt receives low complexity score and MID_TIER assignment."""
    router = SmartToolRouter()
    result = router.classify_complexity("What is the capital of France?")

    assert result.tier_assigned == ModelTier.MID_TIER
    assert result.score <= 0.65
    assert not result.requires_code_execution
    assert not result.requires_multi_hop
    assert "MID_TIER" in result.rationale


def test_complexity_classification_code_and_debugging():
    """Verify prompt requiring programming/debugging is escalated to FRONTIER tier."""
    router = SmartToolRouter()
    prompt = "Write a python script with def process_chunks(data): to debug a memory leak in the repl"
    result = router.classify_complexity(prompt, allowed_tools=["python_sandbox"])

    assert result.tier_assigned == ModelTier.FRONTIER
    assert result.score > 0.65
    assert result.requires_code_execution
    assert result.estimated_steps >= 2
    assert "FRONTIER" in result.rationale


def test_complexity_classification_multi_hop_forensic():
    """Verify multi-hop comparison prompt is escalated to FRONTIER tier."""
    router = SmartToolRouter()
    prompt = "Compare and contrast Q1 vs Q2 earnings across all departments, reconcile discrepancies, and calculate compound growth"
    result = router.classify_complexity(prompt)

    assert result.tier_assigned == ModelTier.FRONTIER
    assert result.score > 0.65
    assert result.requires_multi_hop
    assert result.requires_mathematical_synthesis


def test_escalation_rules():
    """Verify mid-flight escalation detection conditions."""
    router = SmartToolRouter()

    # Case 1: Frontier tier never escalates further
    should_esc, reason, _ = router.should_escalate(
        current_tier=ModelTier.FRONTIER,
        step_index=5,
        circuit_breaker_tripped=True,
    )
    assert not should_esc
    assert reason is None

    # Case 2: Circuit breaker tripped triggers escalation
    should_esc, reason, details = router.should_escalate(
        current_tier=ModelTier.MID_TIER,
        step_index=1,
        circuit_breaker_tripped=True,
    )
    assert should_esc
    assert reason == EscalationReason.CIRCUIT_BREAKER_WARNING
    assert "Circuit breaker" in details

    # Case 3: Self-healing failed after tool exception
    should_esc, reason, details = router.should_escalate(
        current_tier=ModelTier.MID_TIER,
        step_index=1,
        last_tool_error=True,
        self_healing_attempted=True,
    )
    assert should_esc
    assert reason == EscalationReason.SELF_HEALING_FAILED

    # Case 4: Step count threshold >= 3
    should_esc, reason, details = router.should_escalate(
        current_tier=ModelTier.MID_TIER,
        step_index=3,
    )
    assert should_esc
    assert reason == EscalationReason.STEP_COUNT_THRESHOLD

    # Case 5: Routine step 1 without errors
    should_esc, reason, _ = router.should_escalate(
        current_tier=ModelTier.MID_TIER,
        step_index=0,
    )
    assert not should_esc
    assert reason is None


def test_economic_ledger_accounting():
    """Verify counterfactual costs and net savings math."""
    router = SmartToolRouter()
    tenant_id = "tenant_test_econ"

    # Transaction 1: 100% Mid-tier query (2,000 tokens)
    # Actual: 2000 * 0.00015 = $0.30
    # Counterfactual: 2000 * 0.005 = $10.00
    # Net savings: $9.70 (97%)
    rec1 = router.record_transaction(
        tenant_id=tenant_id,
        thread_id="th_1",
        query="Explain pgvector HNSW indexing",
        mid_tier_tokens=2000,
        frontier_tokens=0,
        mid_tier_model="gemini-2.5-flash",
        frontier_model="claude-3-5-sonnet",
    )
    assert rec1.actual_cost_usd == 0.30
    assert rec1.counterfactual_frontier_cost_usd == 10.00
    assert rec1.net_savings_usd == 9.70
    assert rec1.savings_percentage == 97.0
    assert not rec1.escalated

    # Transaction 2: Escalated query (1,000 mid-tier + 1,000 frontier tokens)
    # Actual: (1000 * 0.00015) + (1000 * 0.005) = 0.15 + 5.00 = $5.15
    # Counterfactual: 2000 * 0.005 = $10.00
    # Net savings: $4.85 (48.5%)
    rec2 = router.record_transaction(
        tenant_id=tenant_id,
        thread_id="th_2",
        query="Complex forensic debugging",
        mid_tier_tokens=1000,
        frontier_tokens=1000,
        mid_tier_model="gemini-2.5-flash",
        frontier_model="claude-3-5-sonnet",
        escalated=True,
        escalation_reason=EscalationReason.STEP_COUNT_THRESHOLD,
    )
    assert rec2.actual_cost_usd == 5.15
    assert rec2.counterfactual_frontier_cost_usd == 10.00
    assert rec2.net_savings_usd == 4.85
    assert rec2.savings_percentage == 48.5
    assert rec2.escalated

    # Aggregated Ledger Summary
    summary = router.get_ledger_summary(tenant_id)
    assert summary.total_queries == 2
    assert summary.total_tokens == 4000
    assert summary.mid_tier_share_percentage == 100.0  # Both started on mid-tier
    assert summary.escalation_rate_percentage == 50.0  # 1 out of 2 escalated
    assert summary.total_actual_cost_usd == 5.45
    assert summary.total_counterfactual_cost_usd == 20.00
    assert summary.total_savings_usd == 14.55
    assert summary.average_savings_percentage == 72.8
    assert len(summary.records) == 2


def test_economic_ledger_tenant_isolation():
    """Verify tenant records remain strictly isolated."""
    router = SmartToolRouter()
    router.record_transaction(
        tenant_id="tenant_alpha",
        thread_id="th_a",
        query="Alpha query",
        mid_tier_tokens=1000,
        frontier_tokens=0,
        mid_tier_model="gemini",
        frontier_model="claude",
    )

    alpha_summary = router.get_ledger_summary("tenant_alpha")
    beta_summary = router.get_ledger_summary("tenant_beta")

    assert alpha_summary.total_queries == 1
    assert beta_summary.total_queries == 0
    assert len(beta_summary.records) == 0


@pytest.mark.asyncio
async def test_fastapi_gateway_endpoints():
    """Verify FastAPI gateway classification and ledger REST endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

        # 1. Test POST /v1/tenants/{tenantId}/agentic/gateway/classify
        classify_resp = await client.post(
            "/v1/tenants/tenant_e2e/agentic/gateway/classify",
            json={"query": "Debug python memory profiling script", "allowed_tools": ["python_sandbox"]},
            headers=headers,
        )
        assert classify_resp.status_code == 200
        data = classify_resp.json()
        assert "score" in data
        assert "tier_assigned" in data
        assert data["tier_assigned"] == "frontier"

        # 2. Test GET /v1/tenants/{tenantId}/agentic/gateway/ledger
        ledger_resp = await client.get(
            "/v1/tenants/tenant_e2e/agentic/gateway/ledger",
            headers=headers,
        )
        assert ledger_resp.status_code == 200
        ledger_data = ledger_resp.json()
        assert "total_savings_usd" in ledger_data
        assert "mid_tier_share_percentage" in ledger_data
