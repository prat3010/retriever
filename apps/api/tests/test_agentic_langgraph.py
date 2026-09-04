"""Comprehensive unit and integration tests for Milestone 91:
LangGraph Cyclic Agentic Orchestration & Human-in-the-Loop (HITL) State Engine (v0.76.0).
"""

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.adapters.cognitive.langgraph_orchestrator import LangGraphOrchestrator
from src.adapters.database.agent_checkpoint_repository import (
    SqlAgentCheckpointRepository,
)
from src.config import settings
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.abstractions.inference import InferenceResponse, LlmProvider
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    HITLApprovalDecision,
    ThreadCheckpoint,
)
from src.domain.agentic.execution_engine import AgenticExecutionEngine
from src.domain.agentic.tool_registry import ToolRegistry
from src.main import app

# ── 1. ToolRegistry Sensitivity & Risk Tests ────────────────────────────────


def test_tool_registry_risk_and_sensitivity():
    """Verify built-in tool classification into safe and sensitive tiers."""
    registry = ToolRegistry()

    # Safe tools
    assert registry.is_tool_sensitive("calculator") is False
    assert registry.get_tool_risk("calculator") == "low"
    assert registry.is_tool_sensitive("hybrid_search") is False
    assert registry.is_tool_sensitive("document_reader") is False
    assert registry.is_tool_sensitive("system_metrics") is False

    # Sensitive HITL tools
    assert registry.is_tool_sensitive("document_delete") is True
    assert registry.get_tool_risk("document_delete") == "high"

    assert registry.is_tool_sensitive("tenant_prompt_update") is True
    assert registry.get_tool_risk("tenant_prompt_update") == "high"

    assert registry.is_tool_sensitive("api_key_revoke") is True
    assert registry.get_tool_risk("api_key_revoke") == "critical"


# ── 2. Checkpointer Persistence & Time-Travel Rollback Tests ─────────────────


@pytest.mark.asyncio
async def test_checkpointer_persistence_and_rollback():
    """Verify storing, retrieving, listing, and rolling back state checkpoints."""
    checkpointer = SqlAgentCheckpointRepository()
    tenant_id = str(uuid.uuid4())
    thread_id = f"thr_test_{uuid.uuid4().hex[:8]}"

    # Save Step 0
    chk_0 = ThreadCheckpoint(
        checkpoint_id=f"chk_{thread_id}_step0",
        thread_id=thread_id,
        tenant_id=tenant_id,
        node_name="reasoner",
        step_index=0,
        state_snapshot={"step": 0, "thought": "initial plan"},
    )
    await checkpointer.save_checkpoint(chk_0)

    # Save Step 1
    chk_1 = ThreadCheckpoint(
        checkpoint_id=f"chk_{thread_id}_step1",
        thread_id=thread_id,
        tenant_id=tenant_id,
        node_name="tool_executor",
        step_index=1,
        state_snapshot={"step": 1, "thought": "executed calc"},
    )
    await checkpointer.save_checkpoint(chk_1)

    # Save Step 2
    chk_2 = ThreadCheckpoint(
        checkpoint_id=f"chk_{thread_id}_step2",
        thread_id=thread_id,
        tenant_id=tenant_id,
        node_name="synthesizer",
        step_index=2,
        state_snapshot={"step": 2, "thought": "done"},
    )
    await checkpointer.save_checkpoint(chk_2)

    # Retrieve history
    history = await checkpointer.list_thread_checkpoints(tenant_id, thread_id)
    assert len(history) == 3
    assert history[0].step_index == 0
    assert history[2].step_index == 2

    # Latest checkpoint
    latest = await checkpointer.get_latest_checkpoint(tenant_id, thread_id)
    assert latest is not None
    assert latest.checkpoint_id == chk_2.checkpoint_id

    # Rollback to Step 1 (prunes Step 2)
    rolled_back = await checkpointer.rollback_to_checkpoint(
        tenant_id=tenant_id,
        thread_id=thread_id,
        checkpoint_id=chk_1.checkpoint_id,
        fork=False,
    )
    assert rolled_back.checkpoint_id == chk_1.checkpoint_id

    # Verify Step 2 is pruned from active timeline
    updated_history = await checkpointer.list_thread_checkpoints(tenant_id, thread_id)
    assert len(updated_history) == 2
    assert all(c.step_index <= 1 for c in updated_history)


@pytest.mark.asyncio
async def test_checkpointer_tenant_isolation():
    """Verify cross-tenant security and invalid UUID rejection."""
    checkpointer = SqlAgentCheckpointRepository()
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    thread_id = f"thr_{uuid.uuid4().hex[:8]}"

    chk = ThreadCheckpoint(
        checkpoint_id=f"chk_{thread_id}_0",
        thread_id=thread_id,
        tenant_id=tenant_a,
        node_name="reasoner",
        step_index=0,
        state_snapshot={"secret": "confidential_tenant_a_data"},
    )
    await checkpointer.save_checkpoint(chk)

    # Tenant B cannot retrieve Tenant A's checkpoint
    isolated_res = await checkpointer.get_checkpoint(
        tenant_id=tenant_b, thread_id=thread_id, checkpoint_id=chk.checkpoint_id
    )
    assert isolated_res is None

    # Invalid UUID raises TenantIsolationViolationError
    with pytest.raises(TenantIsolationViolationError):
        await checkpointer.get_checkpoint(
            tenant_id="invalid-uuid-format", thread_id=thread_id, checkpoint_id=chk.checkpoint_id
        )


# ── 3. LangGraph Cyclic Execution & HITL State Tests ─────────────────────────


@pytest.mark.asyncio
async def test_langgraph_safe_cyclic_execution():
    """Verify autonomous cyclic loop for safe tools up to final synthesis."""
    mock_llm = MagicMock(spec=LlmProvider)
    # Turn 1: Calls safe calculator
    resp_1 = InferenceResponse(
        content='{"thought": "Compute total cost", "tool_calls": [{"tool_name": "calculator", "arguments": {"expression": "250 * 4"}}], "final_answer": null}'
    )
    # Turn 2: Cycles back to Reasoner, completes
    resp_2 = InferenceResponse(
        content='{"thought": "Computation complete.", "tool_calls": [], "final_answer": "Total cost is 1000 USD."}'
    )
    mock_llm.generate = AsyncMock(side_effect=[resp_1, resp_2])

    registry = ToolRegistry()
    checkpointer = SqlAgentCheckpointRepository()
    orchestrator = LangGraphOrchestrator(
        llm_provider=mock_llm,
        tool_registry=registry,
        checkpointer=checkpointer,
    )
    engine = AgenticExecutionEngine(
        graph_orchestrator=orchestrator,
        checkpointer=checkpointer,
        tool_registry=registry,
    )

    tenant_id = str(uuid.uuid4())
    req = AgentExecutionRequest(
        tenant_id=tenant_id,
        prompt="Calculate 250 * 4",
        max_steps=5,
    )

    result = await engine.execute_workflow(req)

    assert result.status == "completed"
    assert result.final_answer == "Total cost is 1000 USD."
    assert result.total_steps == 2
    assert result.pending_approval is None

    # Checkpoint history verified
    history = await engine.get_thread_history(tenant_id, result.thread_id)
    assert history.total_checkpoints >= 2


@pytest.mark.asyncio
async def test_langgraph_hitl_gateway_pause_and_approve():
    """Verify execution halts at HITL gate on sensitive tool, then resumes upon approval."""
    mock_llm = MagicMock(spec=LlmProvider)

    # Step 0: Agent decides to call sensitive document_delete
    resp_step0 = InferenceResponse(
        content='{"thought": "User requested document deletion.", "tool_calls": [{"tool_name": "document_delete", "arguments": {"document_id": "doc_999"}}], "final_answer": null}'
    )
    # Step 1 (after resume): Agent sees tool observation and synthesizes final answer
    resp_step1 = InferenceResponse(
        content='{"thought": "Document was approved and deleted.", "tool_calls": [], "final_answer": "Document doc_999 was successfully removed from the knowledge base."}'
    )
    mock_llm.generate = AsyncMock(side_effect=[resp_step0, resp_step1])

    registry = ToolRegistry()
    checkpointer = SqlAgentCheckpointRepository()
    orchestrator = LangGraphOrchestrator(
        llm_provider=mock_llm,
        tool_registry=registry,
        checkpointer=checkpointer,
    )
    engine = AgenticExecutionEngine(
        graph_orchestrator=orchestrator,
        checkpointer=checkpointer,
        tool_registry=registry,
    )

    tenant_id = str(uuid.uuid4())
    req = AgentExecutionRequest(
        tenant_id=tenant_id,
        prompt="Delete document doc_999",
        max_steps=5,
    )

    # 1. Trigger workflow -> Must halt at HITL Gate
    halted_res = await engine.execute_workflow(req)

    assert halted_res.status == "waiting_approval"
    assert halted_res.pending_approval is not None
    assert halted_res.pending_approval.tool_name == "document_delete"
    assert halted_res.pending_approval.risk_level == "high"
    action_id = halted_res.pending_approval.action_id
    thread_id = halted_res.thread_id

    # 2. Submit Approval Decision
    decision = HITLApprovalDecision(
        action_id=action_id,
        decision="approve",
        comment="Authorized by system administrator.",
    )
    resumed_res = await engine.resume_workflow(
        tenant_id=tenant_id,
        thread_id=thread_id,
        decision=decision,
    )

    assert resumed_res.status == "completed"
    assert "doc_999 was successfully removed" in resumed_res.final_answer
    assert resumed_res.pending_approval is None


@pytest.mark.asyncio
async def test_langgraph_hitl_gateway_rejection():
    """Verify execution halts at HITL gate, then safely handles human rejection."""
    mock_llm = MagicMock(spec=LlmProvider)

    # Step 0: Agent plans API key revocation
    resp_step0 = InferenceResponse(
        content='{"thought": "Revoking key.", "tool_calls": [{"tool_name": "api_key_revoke", "arguments": {"key_id": "key_abc"}}], "final_answer": null}'
    )
    # Step 1: Agent receives rejection feedback and informs user
    resp_step1 = InferenceResponse(
        content='{"thought": "Key revocation was rejected by admin.", "tool_calls": [], "final_answer": "API key revocation was declined by the operator. Key remains active."}'
    )
    mock_llm.generate = AsyncMock(side_effect=[resp_step0, resp_step1])

    registry = ToolRegistry()
    checkpointer = SqlAgentCheckpointRepository()
    orchestrator = LangGraphOrchestrator(
        llm_provider=mock_llm,
        tool_registry=registry,
        checkpointer=checkpointer,
    )
    engine = AgenticExecutionEngine(
        graph_orchestrator=orchestrator,
        checkpointer=checkpointer,
        tool_registry=registry,
    )

    tenant_id = str(uuid.uuid4())
    req = AgentExecutionRequest(
        tenant_id=tenant_id,
        prompt="Revoke key key_abc",
        max_steps=5,
    )

    halted_res = await engine.execute_workflow(req)
    assert halted_res.status == "waiting_approval"
    action_id = halted_res.pending_approval.action_id

    # Reject
    decision = HITLApprovalDecision(
        action_id=action_id,
        decision="reject",
        comment="This key is actively used in production billing.",
    )
    rejected_res = await engine.resume_workflow(
        tenant_id=tenant_id,
        thread_id=halted_res.thread_id,
        decision=decision,
    )

    assert rejected_res.status == "completed"
    assert "declined by the operator" in rejected_res.final_answer


# ── 4. FastAPI Router Endpoint Tests ─────────────────────────────────────────


def test_agentic_tools_endpoint():
    """Verify GET /v1/tenants/{tenantId}/agentic/tools lists tools with approval metadata."""
    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    response = client.get(f"/v1/tenants/{tenant_id}/agentic/tools", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    tool_map = {t["name"]: t for t in data}
    assert "calculator" in tool_map
    assert tool_map["calculator"]["requires_approval"] is False

    assert "document_delete" in tool_map
    assert tool_map["document_delete"]["requires_approval"] is True
    assert tool_map["document_delete"]["risk_level"] == "high"


def test_agentic_history_and_rollback_endpoints():
    """Verify GET /history and POST /rollback endpoints."""
    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    thread_id = f"thr_api_{uuid.uuid4().hex[:8]}"
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    # Query history (initially empty)
    res = client.get(
        f"/v1/tenants/{tenant_id}/agentic/threads/{thread_id}/history",
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["total_checkpoints"] == 0


# ── 5. Hexagonal Architecture Boundary Enforcement ──────────────────────────


def test_hexagonal_architecture_boundaries():
    """Verify domain files never import FastAPI, SQLAlchemy, or LangGraph."""
    import src.domain.agentic.abstractions as abs_mod
    import src.domain.agentic.execution_engine as exec_mod
    import src.domain.agentic.tool_registry as tool_mod

    for mod in (abs_mod, exec_mod, tool_mod):
        source = inspect.getsource(mod)
        assert "from fastapi" not in source, f"{mod.__name__} violates Hexagonal boundary by importing FastAPI"
        assert "from sqlalchemy" not in source, f"{mod.__name__} violates Hexagonal boundary by importing SQLAlchemy"
        assert "from langgraph" not in source, f"{mod.__name__} violates Hexagonal boundary by importing LangGraph"
