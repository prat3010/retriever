"""FastAPI Router for Recursive Language Model (RLM) Engine endpoints."""

from fastapi import APIRouter, Depends, status

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.rlm.abstractions import RlmAnalysisRequest, RlmAnalysisResult

router = APIRouter(prefix="/v1", tags=["RLM Analytical Engine"])


@router.post(
    "/tenants/{tenantId}/rlm/analyze",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=RlmAnalysisResult,
)
async def analyze_rlm_workflow(
    tenantId: str,
    request: RlmAnalysisRequest,
) -> RlmAnalysisResult:
    """Trigger recursive analytical RLM synthesis across tenant document trees."""
    request.tenant_id = tenantId
    return await container.rlm_engine.analyze(request)
