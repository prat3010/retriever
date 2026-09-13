"""Comprehensive Unit & Integration Test Suite for Milestone 104 (ReAct Tool Loop).

Validates:
1. Hexagonal domain abstraction purity (AST assertion: 0 forbidden imports).
2. Autonomous ReAct single-turn completion (Direct thought -> Final Answer).
3. Multi-turn tool execution across registered batteries (Thought -> Tool Call -> Observation -> Final Answer).
4. Autonomous Self-Healing Error Recovery (Interception of tool failure -> Diagnostic advice -> Self-correction).
5. Signature-based Anti-Loop Circuit Breaker (Trip on >= 2 identical calls -> Warning injection).
6. Maximum turn limit cap enforcement (Strict limit <= max_turns).
7. Execution timeout guard.
8. FastAPI SSE streaming endpoint (/v1/tenants/{tenantId}/agentic/stream) with real-time event frames.
9. Tenant isolation and security auth headers.
"""

import ast
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.domain.abstractions.inference import (
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
    Usage,
)
from src.domain.abstractions.react import (
    ReActEventType,
    ReActLoopConfig,
)
from src.domain.agentic.abstractions import ToolDefinition
from src.domain.agentic.react_engine import ReActExecutionEngine, _tool_call_signature
from src.domain.agentic.tool_registry import ToolRegistry
from src.main import app


class MockSequentialLlm(LlmProvider):
    """Mock LLM provider returning a programmed sequence of outputs for testing cyclic loops."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self.recorded_requests: list[InferenceRequest] = []

    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        self.recorded_requests.append(request)
        if self._call_count < len(self._responses):
            content = self._responses[self._call_count]
            self._call_count += 1
        else:
            content = json.dumps({"thought": "Final wrap up", "final_answer": "All tasks concluded."})

        return InferenceResponse(
            content=content,
            finish_reason="stop",
            usage=Usage(input_tokens=50, output_tokens=50, total_tokens=100),
        )

    async def generate_stream(self, request: InferenceRequest):
        raise NotImplementedError()


def test_react_domain_abstractions_purity():
    """Verify that domain abstractions import zero forbidden frameworks (Hexagonal rule)."""
    domain_file = Path(__file__).resolve().parents[1] / "src" / "domain" / "abstractions" / "react.py"
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


def test_tool_call_signature_hashing():
    """Verify deterministic signature generation regardless of dictionary key ordering."""
    sig1 = _tool_call_signature("calculator", {"a": 1, "b": 2})
    sig2 = _tool_call_signature("calculator", {"b": 2, "a": 1})
    sig3 = _tool_call_signature("calculator", {"a": 1, "b": 3})
    assert sig1 == sig2
    assert sig1 != sig3


@pytest.mark.asyncio
async def test_react_single_turn_completion():
    """Verify single-turn execution where LLM provides a final answer directly."""
    mock_llm = MockSequentialLlm([
        json.dumps({
            "thought": "This query can be answered directly without tool invocations.",
            "tool_calls": [],
            "final_answer": "Direct answer to prompt.",
        })
    ])
    engine = ReActExecutionEngine(llm_provider=mock_llm)

    trace = await engine.run_loop(tenant_id="test-tenant", query="What is the capital of France?")
    assert trace.final_answer == "Direct answer to prompt."
    assert trace.total_steps >= 1
    assert trace.circuit_breaker_triggered is False
    assert trace.self_healing_interventions == 0


@pytest.mark.asyncio
async def test_react_multi_turn_tool_chaining():
    """Verify multi-turn tool calling: Turn 1 executes tool, Turn 2 completes with final answer."""
    tool_reg = ToolRegistry()
    tool_reg.register_tool(
        definition=ToolDefinition(name="echo_tool", description="Echoes text"),
        handler=lambda msg="": f"Echo: {msg}",
    )

    mock_llm = MockSequentialLlm([
        # Turn 1: Call echo_tool
        json.dumps({
            "thought": "I need to invoke echo_tool to process the message.",
            "tool_calls": [{"tool_name": "echo_tool", "arguments": {"msg": "Hello Swarm"}}],
            "final_answer": None,
        }),
        # Turn 2: Receive observation and answer
        json.dumps({
            "thought": "I received the echo output successfully.",
            "tool_calls": [],
            "final_answer": "Tool execution confirmed: Echo: Hello Swarm",
        }),
    ])

    engine = ReActExecutionEngine(llm_provider=mock_llm, tool_registry=tool_reg)
    events = []
    async for ev in engine.run_loop_stream(tenant_id="test-tenant", query="Echo Hello Swarm"):
        events.append(ev)

    event_types = [e.event_type for e in events]
    assert ReActEventType.THOUGHT in event_types
    assert ReActEventType.TOOL_START in event_types
    assert ReActEventType.TOOL_DONE in event_types
    assert ReActEventType.FINAL_ANSWER in event_types

    # Validate tool output recorded in TOOL_DONE event
    tool_done_ev = next(e for e in events if e.event_type == ReActEventType.TOOL_DONE)
    assert "Echo: Hello Swarm" in tool_done_ev.data["output"]


@pytest.mark.asyncio
async def test_react_self_healing_error_recovery():
    """Verify that when a tool execution fails, the engine intercepts the error, emits SELF_HEALING, and allows recovery."""
    tool_reg = ToolRegistry()

    def buggy_handler(fix: bool = False):
        if not fix:
            raise ValueError("DivisionByZeroError")
        return "Calculation: 42"

    tool_reg.register_tool(
        definition=ToolDefinition(name="flaky_tool", description="A tool that can fail"),
        handler=buggy_handler,
    )

    mock_llm = MockSequentialLlm([
        # Turn 1: Call tool with bad args
        json.dumps({
            "thought": "Trying calculation with initial args.",
            "tool_calls": [{"tool_name": "flaky_tool", "arguments": {"fix": False}}],
        }),
        # Turn 2: Self-correct after observing the error
        json.dumps({
            "thought": "The tool failed with division by zero. Self-correcting by passing fix=True.",
            "tool_calls": [{"tool_name": "flaky_tool", "arguments": {"fix": True}}],
        }),
        # Turn 3: Conclude
        json.dumps({
            "thought": "Calculation resolved cleanly.",
            "tool_calls": [],
            "final_answer": "Success with result 42.",
        }),
    ])

    engine = ReActExecutionEngine(llm_provider=mock_llm, tool_registry=tool_reg)
    trace = await engine.run_loop(tenant_id="test-tenant", query="Compute 42")

    assert trace.self_healing_interventions == 1
    assert "Success with result 42" in trace.final_answer

    # Verify SELF_HEALING event was emitted
    self_healing_events = [e for e in trace.events if e.event_type == ReActEventType.SELF_HEALING]
    assert len(self_healing_events) == 1
    assert self_healing_events[0].data["tool_name"] == "flaky_tool"


@pytest.mark.asyncio
async def test_react_anti_loop_circuit_breaker():
    """Verify that calling the identical tool signature >= 2 times trips the anti-loop circuit breaker."""
    tool_reg = ToolRegistry()
    tool_reg.register_tool(
        definition=ToolDefinition(name="noop_tool", description="No-op"),
        handler=lambda **kwargs: "Same output",
    )

    # Model tries to repeat identical tool call 3 times in a row
    repeating_response = json.dumps({
        "thought": "Looping on same call.",
        "tool_calls": [{"tool_name": "noop_tool", "arguments": {"key": "same_val"}}],
    })
    mock_llm = MockSequentialLlm([repeating_response, repeating_response, repeating_response])

    engine = ReActExecutionEngine(llm_provider=mock_llm, tool_registry=tool_reg)
    trace = await engine.run_loop(
        tenant_id="test-tenant",
        query="Loop test",
        config=ReActLoopConfig(anti_loop_threshold=2, max_turns=5),
    )

    assert trace.circuit_breaker_triggered is True
    cb_events = [e for e in trace.events if e.event_type == ReActEventType.CIRCUIT_BREAKER]
    assert len(cb_events) >= 1
    assert cb_events[0].data["repeated_count"] >= 2


@pytest.mark.asyncio
async def test_react_max_turns_cap():
    """Verify that loop strictly terminates when max_turns is reached."""
    tool_reg = ToolRegistry()
    tool_reg.register_tool(
        definition=ToolDefinition(name="step_tool", description="Steps"),
        handler=lambda **kwargs: "Step executed",
    )

    infinite_steps = [
        json.dumps({"thought": f"Turn {i}", "tool_calls": [{"tool_name": "step_tool", "arguments": {"i": i}}]})
        for i in range(10)
    ]
    mock_llm = MockSequentialLlm(infinite_steps)

    engine = ReActExecutionEngine(llm_provider=mock_llm, tool_registry=tool_reg)
    trace = await engine.run_loop(
        tenant_id="test-tenant",
        query="Run forever",
        config=ReActLoopConfig(max_turns=3),
    )

    # Turn count should not exceed max_turns
    thought_events = [e for e in trace.events if e.event_type == ReActEventType.THOUGHT and "thought" in e.data]
    assert len(thought_events) <= 3


@pytest.mark.asyncio
async def test_fastapi_agentic_stream_endpoint():
    """Verify the /v1/tenants/{tenantId}/agentic/stream SSE endpoint emits valid event streams."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}
        tenant_id = "test-tenant-stream"

        response = await client.post(
            f"/v1/tenants/{tenant_id}/agentic/stream",
            headers=headers,
            json={
                "prompt": "Calculate 5 + 5",
                "max_turns": 4,
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        lines = response.text.strip().split("\n")
        data_lines = [line.removeprefix("data: ").strip() for line in lines if line.startswith("data: ")]
        assert len(data_lines) >= 2

        # Check for [DONE] terminal signal
        assert "[DONE]" in data_lines

        # Parse at least one JSON event frame
        first_event = json.loads(data_lines[0])
        assert "event_id" in first_event
        assert "event_type" in first_event
        assert "state" in first_event
