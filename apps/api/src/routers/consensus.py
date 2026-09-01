"""FastAPI Router for Multi-Agent Consensus & Reflection Loop endpoints."""

from fastapi import APIRouter, Depends, status

from src.adapters.api.security import verify_tenant_or_admin
from src.container import container
from src.domain.consensus.abstractions import ConsensusRequest, ConsensusResult

router = APIRouter(prefix="/v1", tags=["Multi-Agent Consensus"])


@router.post(
    "/tenants/{tenantId}/consensus/generate",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    response_model=ConsensusResult,
)

async def generate_consensus_response(
    tenantId: str,
    request: ConsensusRequest,
) -> ConsensusResult:
    """Execute a Multi-Agent Generator vs. Critic reflection loop."""
    request.tenant_id = tenantId
    return await container.consensus_engine.execute_consensus(request)
