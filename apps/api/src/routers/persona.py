"""API Router for Universal Visitor Persona Clustering & Lead Propensity Scoring (Milestone 85)."""

from fastapi import APIRouter

from src.container import persona_intelligence_service
from src.domain.abstractions.persona_classifier import (
    LeadFeatureVector,
    LeadPropensityScore,
    VisitorPersonaPrediction,
    VisitorTelemetryVector,
)

router = APIRouter(prefix="/v1", tags=["Visitor & Lead Intelligence"])


@router.post("/ml/classify-visitor", response_model=VisitorPersonaPrediction)
def classify_visitor(payload: VisitorTelemetryVector) -> VisitorPersonaPrediction:
    """Cluster anonymous visitor session telemetry into universal persona archetypes."""
    return persona_intelligence_service.classify_visitor(payload)


@router.post("/ml/score-lead", response_model=LeadPropensityScore)
def score_lead(payload: LeadFeatureVector) -> LeadPropensityScore:
    """Predict conversion probability and priority tier for prospective commercial leads."""
    return persona_intelligence_service.score_lead(payload)
