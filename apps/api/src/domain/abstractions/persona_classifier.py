"""Domain abstractions for Universal Multi-Tenant Visitor Persona Clustering & Lead Propensity Scoring (Milestone 85)."""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field


class VisitorTelemetryVector(BaseModel):
    """Universal normalized visitor session telemetry vector (tenant-agnostic)."""

    commercial_intent_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Proportion of dwell/events on commercial/pricing/checkout pages"
    )
    credibility_intent_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Proportion of dwell/events on credentials/case studies/team/resume"
    )
    product_intent_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Proportion of dwell/events on interactive sandbox/terminal/docs"
    )
    content_intent_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Proportion of dwell/events on blog/articles/general discovery"
    )
    dwell_time_seconds: float = Field(
        default=0.0, ge=0.0, description="Total active session duration in seconds"
    )
    interaction_depth_score: float = Field(
        default=0.0, ge=0.0, description="Normalized interaction density (clicks, commands, toggles)"
    )


class VisitorPersonaPrediction(BaseModel):
    """Calibrated persona prediction derived from unsupervised KMeans clustering."""

    persona_category: Literal[
        "commercial_buyer", "technical_evaluator", "talent_recruiter", "community_peer"
    ] = Field(..., description="Classified universal persona category")
    confidence_score: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Cluster centroid proximity confidence score"
    )
    intent_affinity: dict[str, float] = Field(
        default_factory=dict, description="Normalized affinity breakdown across intent dimensions"
    )
    recommended_action: str = Field(
        ..., description="Recommended conversion or engagement action for this persona"
    )
    cluster_id: int = Field(default=0, ge=0, description="Zero-indexed cluster identifier")


class LeadFeatureVector(BaseModel):
    """Normalized structured attributes of a prospective B2B commercial lead."""

    company_size_tier: int = Field(
        default=2, ge=1, le=5, description="1 (1-10), 2 (11-50), 3 (51-200), 4 (201-1000), 5 (1000+)"
    )
    domain_vertical: Literal[
        "ai_ml", "fintech", "enterprise_saas", "health_tech", "e_commerce", "agency_consulting", "other"
    ] = Field(default="ai_ml", description="Business industry vertical")
    role_seniority: Literal[
        "founder_cxo", "engineering_leadership", "technical_staff", "talent_acquisition", "other"
    ] = Field(default="engineering_leadership", description="Seniority of decision maker or hiring contact")
    tech_stack_affinity: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Overlap with tenant engineering competencies (0.0 to 1.0)"
    )
    budget_tier_usd: float = Field(
        default=50000.0, ge=0.0, description="Estimated deal value or annualized compensation budget in USD"
    )
    is_remote: bool = Field(default=True, description="Whether position or engagement is remote-friendly")


class LeadPropensityScore(BaseModel):
    """Calibrated conversion probability and priority tier for autonomous outreach ranking."""

    conversion_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Model-predicted conversion or response probability (0.0 to 1.0)"
    )
    priority_tier: Literal["A+ High Value", "B Qualified", "C Low Priority"] = Field(
        ..., description="Standardized outreach queue priority band"
    )
    recommended_engagement_strategy: str = Field(
        ..., description="Tailored engagement or pitch recommendation based on lead profile"
    )
    key_scoring_drivers: list[str] = Field(
        default_factory=list, description="Primary positive or negative factors influencing the score"
    )


class PersonaClassifierInterface(ABC):
    """Abstract interface for unsupervised visitor persona clustering."""

    @abstractmethod
    def classify_visitor(self, vector: VisitorTelemetryVector) -> VisitorPersonaPrediction:
        """Assign an anonymous session telemetry vector to a persona cluster."""
        pass


class LeadScorerInterface(ABC):
    """Abstract interface for supervised lead conversion propensity scoring."""

    @abstractmethod
    def score_lead(self, vector: LeadFeatureVector) -> LeadPropensityScore:
        """Predict conversion probability and priority band for a B2B lead vector."""
        pass
