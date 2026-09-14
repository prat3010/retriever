"""FastAPI Router for Multi-Agent Swarm Quorum & Dynamic Debate Consensus (M109)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.adapters.api.security import verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.agent_swarm import (
    QuorumConsensusResult,
    SwarmAgentProfile,
    SwarmDebateRequest,
    SwarmStats,
)

router = APIRouter(prefix="/v1", tags=["Agent Swarm Quorum"])


@router.post(
    "/tenants/{tenantId}/agentic/swarm/debate",
    response_model=QuorumConsensusResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def execute_swarm_debate(
    tenantId: str,
    request: SwarmDebateRequest,
) -> QuorumConsensusResult:
    """Execute a multi-agent dialectic debate with weighted quorum voting."""
    engine = getattr(container, "swarm_quorum_engine", None)
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Multi-Agent Swarm Quorum engine is not initialized.",
        )
    request.tenant_id = tenantId
    try:
        return await engine.execute_debate(request)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Swarm debate execution error: {err!s}",
        ) from err


@router.post(
    "/tenants/{tenantId}/agentic/swarm/debate/stream",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def stream_swarm_debate(
    tenantId: str,
    request: SwarmDebateRequest,
) -> StreamingResponse:
    """Stream real-time dialectic debate turns and quorum voting event frames."""
    engine = getattr(container, "swarm_quorum_engine", None)
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Multi-Agent Swarm Quorum engine is not initialized.",
        )
    request.tenant_id = tenantId

    async def sse_event_generator():
        try:
            async for event in engine.stream_debate(request):
                yield f"data: {event.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as err:
            yield f"event: error\ndata: {{\"error\": \"{err!s}\"}}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/tenants/{tenantId}/agentic/swarm/roles",
    response_model=list[SwarmAgentProfile],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def get_swarm_roles(tenantId: str) -> list[SwarmAgentProfile]:
    """List registered specialized swarm agent profiles and voting weights."""
    engine = getattr(container, "swarm_quorum_engine", None)
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Multi-Agent Swarm Quorum engine is not initialized.",
        )
    return await engine.get_roles()


@router.get(
    "/tenants/{tenantId}/agentic/swarm/stats",
    response_model=SwarmStats,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def get_swarm_stats(tenantId: str) -> SwarmStats:
    """Retrieve operational telemetry and debate statistics for a tenant."""
    engine = getattr(container, "swarm_quorum_engine", None)
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Multi-Agent Swarm Quorum engine is not initialized.",
        )
    return await engine.get_stats(tenantId)
