"""API Router for Scikit-Learn Project Effort & Sprint Delivery Timeline Regression (Milestone 84)."""

from fastapi import APIRouter

from src.container import effort_estimation_service
from src.domain.abstractions.effort_estimation import (
    EffortPrediction,
    ProjectScopeInput,
)

router = APIRouter(prefix="/v1", tags=["Scoping & Estimation"])


@router.post("/scoping/estimate-timeline", response_model=EffortPrediction)
def estimate_scoping_timeline(payload: ProjectScopeInput) -> EffortPrediction:
    """Predict realistic engineering hours (P50/P90), calendar delivery bounds, and complexity index."""
    return effort_estimation_service.estimate(payload)
