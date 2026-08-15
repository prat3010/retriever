"""Domain models and abstractions for the Agentic Workflow Execution Engine."""

from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Schema definition for an executable tool registered in the Agent Toolbox."""

    name: str = Field(..., description="Unique tool identifier name")
    description: str = Field(..., description="Human-readable description of tool capability")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for required and optional tool arguments"
    )
    category: str = Field(default="utility", description="Tool functional category")


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


class AgentExecutionRequest(BaseModel):
    """Input payload to trigger an agentic multi-step execution workflow."""

    tenant_id: str = Field(..., description="Target multi-tenant workspace ID")
    prompt: str = Field(..., description="User task goal or multi-step prompt")
    max_steps: int = Field(default=5, ge=1, le=15, description="Maximum reasoning iterations allowed")
    allowed_tools: list[str] | None = Field(
        default=None, description="Optional whitelist of tool names permitted for this run"
    )


class AgentExecutionResult(BaseModel):
    """Final output response returned by the Agentic Workflow Engine."""

    tenant_id: str
    prompt: str
    final_answer: str
    steps: list[AgentStep] = Field(default_factory=list)
    total_steps: int
    execution_time_ms: float
