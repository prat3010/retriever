"""FastAPI Router for Agentic Workflow Execution endpoints (Milestone 91)."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    AgentExecutionResult,
    HITLApprovalDecision,
    ThreadCheckpoint,
    ThreadHistoryResponse,
    ThreadRollbackRequest,
    ToolDefinition,
)

router = APIRouter(prefix="/v1", tags=["Agentic Workflows"])


@router.post(
    "/tenants/{tenantId}/agentic/execute",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=AgentExecutionResult,
)
async def execute_agent_workflow(
    tenantId: str,
    request: AgentExecutionRequest,
) -> AgentExecutionResult:
    """Execute a stateful cyclic agentic workflow loop for a tenant."""
    request.tenant_id = tenantId
    try:
        return await container.agentic_engine.execute_workflow(request)
    except TenantIsolationViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(err)
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow error: {err!s}",
        ) from err


@router.post(
    "/tenants/{tenantId}/agentic/threads/{threadId}/resume",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=AgentExecutionResult,
)
async def resume_agent_workflow(
    tenantId: str,
    threadId: str,
    decision: HITLApprovalDecision,
) -> AgentExecutionResult:
    """Resume a paused agent thread with a human approval or rejection decision."""
    try:
        return await container.agentic_engine.resume_workflow(
            tenant_id=tenantId,
            thread_id=threadId,
            decision=decision,
        )
    except TenantIsolationViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(err)
        ) from err
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming agent thread: {err!s}",
        ) from err


@router.get(
    "/tenants/{tenantId}/agentic/threads/{threadId}/history",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=ThreadHistoryResponse,
)
async def get_agent_thread_history(
    tenantId: str,
    threadId: str,
) -> ThreadHistoryResponse:
    """Retrieve full chronological checkpoint history for time-travel debugging."""
    try:
        return await container.agentic_engine.get_thread_history(
            tenant_id=tenantId,
            thread_id=threadId,
        )
    except TenantIsolationViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(err)
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving thread history: {err!s}",
        ) from err


@router.post(
    "/tenants/{tenantId}/agentic/threads/{threadId}/rollback",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=ThreadCheckpoint,
)
async def rollback_agent_thread(
    tenantId: str,
    threadId: str,
    request: ThreadRollbackRequest,
) -> ThreadCheckpoint:
    """Roll back agent thread state to an earlier checkpoint."""
    try:
        return await container.agentic_engine.rollback_thread(
            tenant_id=tenantId,
            thread_id=threadId,
            checkpoint_id=request.target_checkpoint_id,
            fork=request.fork,
        )
    except TenantIsolationViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(err)
        ) from err
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(err)
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rolling back thread: {err!s}",
        ) from err


@router.get(
    "/tenants/{tenantId}/agentic/tools",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=list[ToolDefinition],
)
async def list_agent_tools(tenantId: str) -> list[ToolDefinition]:
    """List registered tools available in the agent toolbox."""
    return container.tool_registry.list_tools()
