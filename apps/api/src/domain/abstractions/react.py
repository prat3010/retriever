"""Domain Abstractions for Autonomous Multi-Turn ReAct Tool Loop (M104).

Pure domain layer with zero infrastructure or framework imports.
Defines contracts for:
- Cyclic ReAct state machine lifecycle (Reasoning -> Selecting Tool -> Executing Battery -> Observing -> Evaluating)
- Granular streaming Server-Sent Events (SSE) protocol frames
- Anti-loop circuit breaker configurations and event tracking
- Autonomous self-healing exception advisories
- Comprehensive execution trace records
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ReActState(StrEnum):
    """Discrete states of the cyclic ReAct agentic execution machine."""

    IDLE = "idle"
    REASONING = "reasoning"
    SELECTING_TOOL = "selecting_tool"
    EXECUTING_BATTERY = "executing_battery"
    OBSERVING_RESULT = "observing_result"
    SELF_HEALING = "self_healing"
    EVALUATING_COMPLETION = "evaluating_completion"
    COMPLETED = "completed"
    ERROR = "error"


class ReActEventType(StrEnum):
    """Event types emitted over the streaming SSE channel."""

    THOUGHT = "thought"
    TOOL_START = "tool_start"
    TOOL_DONE = "tool_done"
    SELF_HEALING = "self_healing"
    CIRCUIT_BREAKER = "circuit_breaker"
    MODEL_ESCALATION = "model_escalation"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"


class ReActEvent(BaseModel):
    """Real-time streaming event frame emitted during cyclic ReAct execution."""

    event_id: str = Field(..., description="Unique event UUID")
    event_type: ReActEventType
    step_index: int = Field(default=0, ge=0, description="Zero-based reasoning iteration counter")
    state: ReActState
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class ReActLoopConfig(BaseModel):
    """Configuration hyperparameters governing the autonomous ReAct loop."""

    max_turns: int = Field(default=8, ge=1, le=20, description="Strict maximum reasoning loop turns")
    timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0, description="Wall-clock loop execution timeout")
    anti_loop_threshold: int = Field(
        default=2, ge=2, le=5, description="Max allowed identical tool call signatures before tripping circuit breaker"
    )
    self_healing_enabled: bool = Field(default=True, description="Whether tool execution errors trigger self-healing prompt recovery")
    allowed_tools: list[str] | None = Field(default=None, description="Optional tool whitelist; None allows all registered batteries")


class ReActExecutionTrace(BaseModel):
    """Immutable audit record of a completed ReAct agentic thread execution."""

    thread_id: str
    tenant_id: str
    query: str
    final_answer: str
    total_steps: int
    self_healing_interventions: int = 0
    circuit_breaker_triggered: bool = False
    execution_time_ms: float
    events: list[ReActEvent] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=_utc_now)


@runtime_checkable
class ReActLoopProtocol(Protocol):
    """Abstract protocol for executing multi-turn autonomous ReAct reasoning loops."""

    def run_loop_stream(
        self,
        tenant_id: str,
        query: str,
        config: ReActLoopConfig | None = None,
        thread_id: str | None = None,
    ) -> AsyncGenerator[ReActEvent, None]:
        """Execute cyclic ReAct loop yielding streaming real-time events."""
        ...

    async def run_loop(
        self,
        tenant_id: str,
        query: str,
        config: ReActLoopConfig | None = None,
        thread_id: str | None = None,
    ) -> ReActExecutionTrace:
        """Execute cyclic ReAct loop and return full compiled execution trace."""
        ...
