"""Unit tests for Milestone 46: Agentic Workflow Execution Engine."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.domain.abstractions.inference import InferenceResponse, LlmProvider
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    ToolDefinition,
)
from src.domain.agentic.execution_engine import AgenticExecutionEngine
from src.domain.agentic.tool_registry import ToolRegistry
from src.main import app

# ── 1. ToolRegistry Tests ───────────────────────────────────────────────────

def test_tool_registry_management():
    """Verify registering, retrieving, and unregistering tools."""
    registry = ToolRegistry()

    custom_tool = ToolDefinition(
        name="echo_tool",
        description="Echoes input string",
        parameters_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
    )

    def _echo_handler(msg: str) -> str:
        return f"Echo: {msg}"

    registry.register_tool(custom_tool, _echo_handler)
    assert registry.get_tool_definition("echo_tool") is not None
    assert len(registry.list_tools()) >= 2  # default calculator + echo_tool

    # Filtered whitelist
    filtered = registry.list_tools(allowed_tools=["calculator"])
    assert len(filtered) == 1
    assert filtered[0].name == "calculator"

    # Unregister
    registry.unregister_tool("echo_tool")
    assert registry.get_tool_definition("echo_tool") is None


@pytest.mark.asyncio
async def test_tool_execution_calculator():
    """Verify built-in safe calculator tool execution."""
    registry = ToolRegistry()

    res = await registry.execute_tool(
        call_id="call_1",
        tool_name="calculator",
        arguments={"expression": "12000 + 15000 + 8000"},
    )
    assert res.is_error is False
    assert res.output == "35000"


# ── 2. AgenticExecutionEngine ReAct Loop Test ────────────────────────────────

@pytest.mark.asyncio
async def test_agentic_execution_loop():
    """Verify AgenticExecutionEngine executes multi-step ReAct tool calling loop."""
    mock_llm = MagicMock(spec=LlmProvider)

    # Step 0: LLM decides to call calculator tool
    llm_resp_1 = InferenceResponse(
        content='{"thought": "I need to calculate the sum.", "tool_calls": [{"tool_name": "calculator", "arguments": {"expression": "50 + 50"}}], "final_answer": null}'
    )
    # Step 1: LLM sees tool result and synthesizes final answer
    llm_resp_2 = InferenceResponse(
        content='{"thought": "I have the sum result.", "tool_calls": [], "final_answer": "The calculated total is 100."}'
    )

    mock_llm.generate = AsyncMock(side_effect=[llm_resp_1, llm_resp_2])

    registry = ToolRegistry()
    engine = AgenticExecutionEngine(llm_provider=mock_llm, tool_registry=registry)

    req = AgentExecutionRequest(
        tenant_id=str(uuid.uuid4()),
        prompt="Calculate 50 + 50",
        max_steps=5,
    )

    result = await engine.execute_workflow(req)

    assert result.final_answer == "The calculated total is 100."
    assert result.total_steps == 2
    assert len(result.steps[0].tool_calls) == 1
    assert result.steps[0].tool_calls[0].tool_name == "calculator"
    assert result.steps[0].tool_results[0].output == "100"


# ── 3. Router Endpoint Tests ─────────────────────────────────────────────────

def test_agentic_tools_endpoint():
    """Verify GET /v1/tenants/{tenantId}/agentic/tools endpoint."""
    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    response = client.get(f"/v1/tenants/{tenant_id}/agentic/tools", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(t["name"] == "calculator" for t in data)


@patch("src.container.container.agentic_engine.execute_workflow")
def test_agentic_execute_endpoint(mock_execute):
    """Verify POST /v1/tenants/{tenantId}/agentic/execute endpoint."""
    mock_execute.return_value = AsyncMock()
    mock_execute.return_value = {
        "tenant_id": "t1",
        "prompt": "Test prompt",
        "final_answer": "Final test answer",
        "steps": [],
        "total_steps": 1,
        "execution_time_ms": 12.5,
    }

    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    payload = {
        "tenant_id": tenant_id,
        "prompt": "Calculate 10 + 20",
        "max_steps": 3,
    }

    response = client.post(
        f"/v1/tenants/{tenant_id}/agentic/execute",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["final_answer"] == "Final test answer"
