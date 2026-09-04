"""FastAPI Router for Durable Asynchronous Workflow Execution (Milestone 95).

Provides tenant-scoped and platform-wide REST APIs to trigger event-driven workflows,
inspect execution step DAGs, replay failed checkpoints, and monitor background tasks.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.abstractions.durable_workflow import (
    WorkflowDefinition,
    WorkflowEventDispatch,
    WorkflowExecutionRecord,
    WorkflowRunRequest,
    WorkflowStatus,
)
from src.domain.abstractions.exceptions import TenantIsolationViolationError

logger = logging.getLogger("api")

# Tenant-scoped workflow router
router = APIRouter(
    prefix="/v1/tenants/{tenantId}/workflows",
    tags=["Durable Workflows"],
)

# Admin platform-wide router
admin_router = APIRouter(
    prefix="/v1/admin/workflows",
    tags=["Durable Workflows Admin"],
)


class TriggerWorkflowBody(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    webhook_url: str | None = None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowExecutionRecord]
    total: int
    limit: int
    offset: int


class WorkflowOverviewResponse(BaseModel):
    total_blueprints: int
    blueprints: list[WorkflowDefinition]
    engine_status: str = "healthy"
    checkpoint_backend: str = "PostgreSQL+Redis"


# ── Tenant-Scoped Workflow Endpoints ──────────────────────────────────────────


@router.get("/blueprints", response_model=list[WorkflowDefinition])
async def list_tenant_blueprints(
    tenantId: str,
    _=Depends(verify_admin_key),
) -> list[WorkflowDefinition]:
    """List all available durable workflow blueprints."""
    return container.durable_workflow_adapter.list_registered_workflows()


@router.post("/events", response_model=list[WorkflowExecutionRecord], status_code=status.HTTP_202_ACCEPTED)
async def dispatch_workflow_event(
    tenantId: str,
    event: WorkflowEventDispatch,
    _=Depends(verify_admin_key),
) -> list[WorkflowExecutionRecord]:
    """Dispatch an event to trigger subscribed durable workflows."""
    try:
        return await container.durable_workflow_adapter.dispatch_event(tenantId, event)
    except TenantIsolationViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
    except Exception as err:
        logger.error("Failed to dispatch workflow event: %s", err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from err


@router.post("/{workflowName}/run", response_model=WorkflowExecutionRecord, status_code=status.HTTP_202_ACCEPTED)
async def run_named_workflow(
    tenantId: str,
    workflowName: str,
    body: TriggerWorkflowBody,
    _=Depends(verify_admin_key),
) -> WorkflowExecutionRecord:
    """Trigger a named workflow execution immediately."""
    req = WorkflowRunRequest(
        workflow_name=workflowName,
        input_payload=body.input_payload,
        idempotency_key=body.idempotency_key,
        webhook_url=body.webhook_url,
    )
    try:
        return await container.durable_workflow_adapter.start_workflow(tenantId, req)
    except TenantIsolationViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    except Exception as err:
        logger.error("Failed to start workflow '%s': %s", workflowName, err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from err


@router.get("/executions", response_model=WorkflowListResponse)
async def list_tenant_executions(
    tenantId: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: WorkflowStatus | None = Query(default=None, alias="status"),
    _=Depends(verify_admin_key),
) -> WorkflowListResponse:
    """List execution history and current progress for a tenant."""
    try:
        items, total = await container.durable_workflow_adapter.list_executions(
            tenantId, limit=limit, offset=offset, status=status_filter
        )
        return WorkflowListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
    except TenantIsolationViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


@router.get("/executions/{executionId}", response_model=WorkflowExecutionRecord)
async def get_execution_detail(
    tenantId: str,
    executionId: str,
    _=Depends(verify_admin_key),
) -> WorkflowExecutionRecord:
    """Get full state and step-level checkpoints of an execution."""
    try:
        rec = await container.durable_workflow_adapter.get_execution(tenantId, executionId)
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{executionId}' not found for tenant.",
            )
        return rec
    except TenantIsolationViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


@router.post("/executions/{executionId}/retry", response_model=WorkflowExecutionRecord)
async def retry_failed_execution(
    tenantId: str,
    executionId: str,
    _=Depends(verify_admin_key),
) -> WorkflowExecutionRecord:
    """Replay execution starting from the failed step checkpoint."""
    try:
        return await container.durable_workflow_adapter.retry_execution(tenantId, executionId)
    except TenantIsolationViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    except Exception as err:
        logger.error("Failed to retry execution '%s': %s", executionId, err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)) from err


@router.post("/executions/{executionId}/cancel", response_model=WorkflowExecutionRecord)
async def cancel_workflow_execution(
    tenantId: str,
    executionId: str,
    _=Depends(verify_admin_key),
) -> WorkflowExecutionRecord:
    """Cancel an active or queued workflow execution."""
    try:
        return await container.durable_workflow_adapter.cancel_execution(tenantId, executionId)
    except TenantIsolationViolationError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


# ── Platform Admin Endpoints ───────────────────────────────────────────────────


@admin_router.get("/overview", response_model=WorkflowOverviewResponse)
async def get_admin_workflow_overview(
    _=Depends(verify_admin_key),
) -> WorkflowOverviewResponse:
    """Get platform-wide workflow blueprints and engine status."""
    blueprints = container.durable_workflow_adapter.list_registered_workflows()
    return WorkflowOverviewResponse(
        total_blueprints=len(blueprints),
        blueprints=blueprints,
        engine_status="healthy",
        checkpoint_backend="PostgreSQL+Redis",
    )
