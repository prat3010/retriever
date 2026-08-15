"""FastAPI Router for Agentic Workflow Execution endpoints."""

from fastapi import APIRouter, Depends, status

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    AgentExecutionResult,
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
    """Execute a multi-step agentic workflow loop for a tenant."""
    request.tenant_id = tenantId
    return await container.agentic_engine.execute_workflow(request)


@router.get(
    "/tenants/{tenantId}/agentic/tools",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=list[ToolDefinition],
)
async def list_agent_tools(tenantId: str) -> list[ToolDefinition]:
    """List registered tools available in the agent toolbox."""
    return container.tool_registry.list_tools()
