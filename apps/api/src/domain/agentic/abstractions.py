"""Domain models and abstractions for the Agentic Workflow Execution Engine.

Conforms strictly to Hexagonal Architecture boundaries (0 framework imports).
"""

import time
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Schema definition for an executable tool registered in the Agent Toolbox."""

    name: str = Field(..., description="Unique tool identifier name")
    description: str = Field(..., description="Human-readable description of tool capability")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for required and optional tool arguments"
    )
    category: str = Field(default="utility", description="Tool functional category")
    requires_approval: bool = Field(
        default=False, description="Whether execution halts at HITL gate for human confirmation"
    )
    risk_level: str = Field(
        default="low", description="Risk tier: low | medium | high | critical"
    )


class ToolCall(BaseModel):
    """An invocation request produced by the LLM during an agentic step."""

    call_id: str = Field(..., description="Unique identifier for matching tool call with result")
    tool_name: str = Field(..., description="Target tool name to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments passed to tool")


class ToolResult(BaseModel):
    """The execution result returned by a tool call."""

    call_id: str = Field(..., description="Identifier matching the originating ToolCall")
    tool_name: str = Field(..., description="Name of executed tool")
    output: Any = Field(..., description="Returned execution result data or string response")
    is_error: bool = Field(default=False, description="True if tool execution raised an exception")


class AgentStep(BaseModel):
    """A single reasoning and tool execution iteration in an agentic workflow."""

    step_index: int = Field(..., description="Zero-based iteration step counter")
    thought: str = Field(..., description="Agent reasoning or internal plan before action")
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)


class HITLApprovalRequest(BaseModel):
    """Structured human approval request emitted when a sensitive action is triggered."""

    action_id: str = Field(..., description="Unique action approval request identifier")
    thread_id: str = Field(..., description="Orchestration thread session identifier")
    tenant_id: str = Field(..., description="Target tenant workspace ID")
    tool_name: str = Field(..., description="Name of the sensitive tool awaiting approval")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Proposed tool arguments")
    risk_level: str = Field(default="high", description="Risk tier: high | critical")
    description: str = Field(..., description="Human-readable description of what will execute")
    status: str = Field(default="pending", description="pending | approved | rejected")
    created_at: float = Field(default_factory=time.time, description="Creation epoch timestamp")


class HITLApprovalDecision(BaseModel):
    """Human operator response submitted to resume an interrupted agent thread."""

    action_id: str = Field(..., description="Target action ID being resolved")
    decision: str = Field(..., description="Approval decision: approve | reject")
    modified_arguments: dict[str, Any] | None = Field(
        default=None, description="Optional override or sanitized arguments to run instead"
    )
    comment: str | None = Field(
        default=None, description="Optional human rationale or instructions to guide the agent"
    )


class ThreadCheckpoint(BaseModel):
    """Persisted snapshot of agent state at a specific node/step in the graph."""

    checkpoint_id: str = Field(..., description="Unique checkpoint identifier")
    thread_id: str = Field(..., description="Orchestration thread session identifier")
    tenant_id: str = Field(..., description="Tenant workspace ID")
    node_name: str = Field(..., description="Name of active graph node when saved")
    step_index: int = Field(..., description="Step counter at checkpoint time")
    state_snapshot: dict[str, Any] = Field(..., description="Serialized thread state payload")
    created_at: float = Field(default_factory=time.time, description="Epoch timestamp of snapshot")


class ThreadRollbackRequest(BaseModel):
    """Request payload to rewind a thread to an earlier state checkpoint."""

    target_checkpoint_id: str = Field(..., description="Checkpoint ID to rewind state to")
    fork: bool = Field(
        default=False, description="If True, creates a new branched thread instead of pruning forward steps"
    )


class ThreadHistoryResponse(BaseModel):
    """Complete chronological audit history of state checkpoints for a thread."""

    thread_id: str
    tenant_id: str
    total_checkpoints: int
    checkpoints: list[ThreadCheckpoint] = Field(default_factory=list)


class AgentExecutionRequest(BaseModel):
    """Input payload to trigger an agentic multi-step execution workflow."""

    tenant_id: str = Field(..., description="Target multi-tenant workspace ID")
    prompt: str = Field(..., description="User task goal or multi-step prompt")
    thread_id: str | None = Field(
        default=None, description="Optional thread session ID. If None, a new thread is generated."
    )
    max_steps: int = Field(
        default=10, ge=1, le=20, description="Maximum reasoning iterations allowed"
    )
    allowed_tools: list[str] | None = Field(
        default=None, description="Optional whitelist of tool names permitted for this run"
    )


class AgentExecutionResult(BaseModel):
    """Output response returned by the Agentic Workflow Engine."""

    tenant_id: str
    thread_id: str = Field(
        default_factory=lambda: f"thr_{uuid4().hex[:12]}",
        description="Thread session identifier",
    )
    prompt: str
    final_answer: str
    status: str = Field(
        default="completed", description="completed | waiting_approval | rejected | error"
    )
    steps: list[AgentStep] = Field(default_factory=list)
    pending_approval: HITLApprovalRequest | None = Field(
        default=None, description="Populated when status is waiting_approval"
    )
    checkpoint_id: str | None = Field(
        default=None, description="Latest state checkpoint identifier"
    )
    total_steps: int
    execution_time_ms: float


@runtime_checkable
class StateCheckpointerProtocol(Protocol):
    """Abstract protocol for persisting, retrieving, and rewinding agent graph checkpoints."""

    async def save_checkpoint(self, checkpoint: ThreadCheckpoint) -> None:
        """Persist a state checkpoint snapshot."""
        ...

    async def get_checkpoint(
        self, tenant_id: str, thread_id: str, checkpoint_id: str
    ) -> ThreadCheckpoint | None:
        """Fetch a specific checkpoint scoped strictly by tenant_id."""
        ...

    async def get_latest_checkpoint(
        self, tenant_id: str, thread_id: str
    ) -> ThreadCheckpoint | None:
        """Retrieve the most recent checkpoint for an active thread."""
        ...

    async def list_thread_checkpoints(
        self, tenant_id: str, thread_id: str
    ) -> list[ThreadCheckpoint]:
        """List all chronological checkpoints recorded for a thread."""
        ...

    async def rollback_to_checkpoint(
        self, tenant_id: str, thread_id: str, checkpoint_id: str, fork: bool = False
    ) -> ThreadCheckpoint:
        """Rewind thread to a prior checkpoint, pruning future steps or branching."""
        ...


@runtime_checkable
class AgentGraphEngineProtocol(Protocol):
    """Abstract protocol for executing and resuming cyclic state graph workflows."""

    async def execute_workflow(
        self, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Execute a stateful cyclic agent graph."""
        ...

    async def resume_workflow(
        self,
        tenant_id: str,
        thread_id: str,
        decision: HITLApprovalDecision,
    ) -> AgentExecutionResult:
        """Resume an interrupted thread with human approval or rejection."""
        ...
