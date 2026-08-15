"""Domain abstractions and models for the Recursive Language Model (RLM) Engine & REPL Sandbox."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ReplExecutionResult(BaseModel):
    """Execution output returned by the REPL Sandbox."""

    output: str = Field(default="", description="Captured stdout / console log output")
    return_value: Any = Field(default=None, description="Returned result value or evaluation expression")
    is_error: bool = Field(default=False, description="True if script execution raised an exception")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class ReplSandboxProvider(ABC):
    """Abstract port for executing Python code in an isolated tenant sandbox."""

    @abstractmethod
    async def execute_script(
        self,
        tenant_id: str,
        code: str,
        context_dict: dict[str, Any] | None = None,
        timeout_seconds: float = 15.0,
    ) -> ReplExecutionResult:
        """Execute a Python code string inside a restricted AST sandbox."""
        pass


class RlmAnalysisRequest(BaseModel):
    """Input payload to trigger a Recursive Language Model analytical synthesis."""

    tenant_id: str = Field(..., description="Target multi-tenant workspace ID")
    prompt: str = Field(..., description="High-level analytical query or synthesis task")
    document_ids: list[str] | None = Field(
        default=None, description="Optional filter list of target document UUIDs"
    )
    max_depth: int = Field(default=3, ge=1, le=5, description="Maximum recursive sub-call depth")


class RlmAnalysisResult(BaseModel):
    """Final output response returned by the RLM Engine."""

    tenant_id: str
    prompt: str
    analysis_summary: str
    code_executions: list[dict[str, Any]] = Field(default_factory=list)
    subcalls_count: int = Field(default=0)
    execution_time_ms: float
