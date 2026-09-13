"""FastAPI Router for Agentic Workflow Execution endpoints (Milestones 91 & 104)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.economic_orchestrator import (
    EconomicLedgerSummary,
    TaskComplexity,
)
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.abstractions.react import ReActLoopConfig
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


class ReActStreamRequest(BaseModel):
    """Payload to trigger a streaming ReAct agentic reasoning loop."""

    prompt: str = Field(..., min_length=1, description="Goal or multi-step query for the agent")
    max_turns: int = Field(default=8, ge=1, le=20, description="Max reasoning turns")
    timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0, description="Max execution timeout in seconds")
    allowed_tools: list[str] | None = Field(default=None, description="Optional whitelist of allowed tool names")


@router.post(
    "/tenants/{tenantId}/agentic/stream",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def stream_agent_workflow(
    tenantId: str,
    request: ReActStreamRequest,
) -> StreamingResponse:
    """Execute autonomous cyclic ReAct reasoning loop with real-time SSE streaming event frames."""
    config = ReActLoopConfig(
        max_turns=request.max_turns,
        timeout_seconds=request.timeout_seconds,
        allowed_tools=request.allowed_tools,
    )

    async def sse_event_generator():
        async for event in container.react_engine.run_loop_stream(
            tenant_id=tenantId,
            query=request.prompt,
            config=config,
        ):
            yield f"data: {event.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/tenants/{tenantId}/agentic/execute",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
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


class ClassifyComplexityRequest(BaseModel):
    """Payload to classify task complexity and determine starting model tier."""

    query: str = Field(..., min_length=1, description="User prompt or task to evaluate")
    allowed_tools: list[str] | None = Field(default=None, description="Optional list of tools available for the task")


@router.get(
    "/tenants/{tenantId}/agentic/tools",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    response_model=list[ToolDefinition],
)
async def list_agent_tools(tenantId: str) -> list[ToolDefinition]:
    """List registered tools available in the agent toolbox."""
    return container.tool_registry.list_tools()


@router.get(
    "/tenants/{tenantId}/agentic/gateway/ledger",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    response_model=EconomicLedgerSummary,
)
async def get_agentic_economic_ledger(tenantId: str) -> EconomicLedgerSummary:
    """Retrieve multi-model economic orchestration ledger and cumulative cost savings."""
    return container.smart_tool_router.get_ledger_summary(tenantId)


@router.post(
    "/tenants/{tenantId}/agentic/gateway/classify",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    response_model=TaskComplexity,
)
async def classify_task_complexity(
    tenantId: str,
    request: ClassifyComplexityRequest,
) -> TaskComplexity:
    """Classify prompt difficulty and assign optimal starting model tier."""
    return container.smart_tool_router.classify_complexity(
        query=request.query,
        allowed_tools=request.allowed_tools,
    )
