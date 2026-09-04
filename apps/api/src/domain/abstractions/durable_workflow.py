"""Domain Abstractions for Durable Asynchronous Workflow Execution (Milestone 95).

Defines pure domain models, workflow definitions, step checkpoints, and
abstract repository & adapter interfaces for event-driven durable execution.
Contains ZERO external framework, adapter, or database imports.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(StrEnum):
    """Lifecycle state of a durable workflow execution."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    """Lifecycle state of an individual durable workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStepRecord(BaseModel):
    """Execution checkpoint and memoized outcome of a single workflow step."""

    step_id: str
    execution_id: str
    step_name: str
    step_index: int = 0
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    memoized_output: dict[str, Any] = Field(default_factory=dict)
    error_details: str | None = None
    execution_time_ms: float = 0.0
    started_at: str | None = None
    completed_at: str | None = None


class WorkflowExecutionRecord(BaseModel):
    """Full execution state, parameters, and step history for a durable workflow."""

    execution_id: str
    tenant_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.QUEUED
    trigger_event: str | None = None
    idempotency_key: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    total_steps: int = 0
    completed_steps: int = 0
    current_step_name: str | None = None
    error_message: str | None = None
    step_history: list[WorkflowStepRecord] = Field(default_factory=list)
    webhook_url: str | None = None
    started_at: str = ""
    completed_at: str | None = None


class WorkflowStepDefinition(BaseModel):
    """Declarative specification of a single step within a workflow pipeline."""

    name: str
    description: str = ""
    max_attempts: int = 3
    timeout_seconds: int = 60


class WorkflowDefinition(BaseModel):
    """Specification of a multi-step durable workflow pipeline."""

    name: str
    title: str
    description: str = ""
    trigger_event: str | None = None
    concurrency_limit: int = 3
    max_step_retries: int = 3
    backoff_factor: float = 2.0
    initial_interval_seconds: float = 1.0
    steps: list[WorkflowStepDefinition] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    """Payload to trigger an asynchronous durable workflow execution."""

    workflow_name: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    webhook_url: str | None = None


class WorkflowEventDispatch(BaseModel):
    """Event emitted to trigger matching event-driven workflows."""

    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


# ── Abstract Repository Port ──────────────────────────────────────────────────


class IDurableWorkflowRepository(ABC):
    """Persistence port for workflow executions and step-level checkpoints."""

    @abstractmethod
    async def create_execution(self, execution: WorkflowExecutionRecord) -> None:
        """Create a new workflow execution record."""
        pass

    @abstractmethod
    async def get_execution(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecutionRecord | None:
        """Fetch execution record by tenant and execution ID."""
        pass

    @abstractmethod
    async def find_by_idempotency_key(
        self, tenant_id: str, idempotency_key: str
    ) -> WorkflowExecutionRecord | None:
        """Retrieve existing execution by unique idempotency key if previously submitted."""
        pass

    @abstractmethod
    async def update_execution(self, execution: WorkflowExecutionRecord) -> None:
        """Update workflow execution state and outputs."""
        pass

    @abstractmethod
    async def list_executions(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        status: WorkflowStatus | None = None,
        workflow_name: str | None = None,
    ) -> tuple[list[WorkflowExecutionRecord], int]:
        """List workflow executions for a tenant with pagination and filters."""
        pass

    @abstractmethod
    async def save_step_checkpoint(self, step: WorkflowStepRecord) -> None:
        """Persist or update a step checkpoint."""
        pass

    @abstractmethod
    async def get_step_checkpoint(
        self, execution_id: str, step_name: str
    ) -> WorkflowStepRecord | None:
        """Retrieve a specific step checkpoint by execution ID and step name."""
        pass

    @abstractmethod
    async def list_step_checkpoints(
        self, execution_id: str
    ) -> list[WorkflowStepRecord]:
        """Fetch all step checkpoints for an execution in chronological sequence."""
        pass

    @abstractmethod
    async def count_active_tenant_executions(self, tenant_id: str) -> int:
        """Count currently running/queued executions for concurrency throttling."""
        pass


# ── Abstract Workflow Adapter Port ─────────────────────────────────────────────


class IDurableWorkflowAdapter(ABC):
    """Adapter port for executing resilient multi-step workflows with step memoization."""

    @abstractmethod
    async def dispatch_event(
        self, tenant_id: str, event: WorkflowEventDispatch
    ) -> list[WorkflowExecutionRecord]:
        """Dispatch event and trigger any matching subscribed workflow pipelines."""
        pass

    @abstractmethod
    async def start_workflow(
        self, tenant_id: str, request: WorkflowRunRequest
    ) -> WorkflowExecutionRecord:
        """Start a named workflow execution immediately with step memoization."""
        pass

    @abstractmethod
    async def get_execution(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecutionRecord | None:
        """Get live status and step progress of an execution."""
        pass

    @abstractmethod
    async def retry_execution(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecutionRecord:
        """Replay failed workflow execution from the failed step checkpoint."""
        pass

    @abstractmethod
    async def cancel_execution(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecutionRecord:
        """Cancel a queued or active workflow execution."""
        pass

    @abstractmethod
    async def list_executions(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        status: WorkflowStatus | None = None,
    ) -> tuple[list[WorkflowExecutionRecord], int]:
        """List past executions for a tenant."""
        pass

    @abstractmethod
    def list_registered_workflows(self) -> list[WorkflowDefinition]:
        """List all available workflow blueprints registered in the engine."""
        pass
