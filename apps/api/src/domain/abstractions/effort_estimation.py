"""Domain abstractions for Scikit-Learn Project Effort & Sprint Delivery Timeline Regression (Milestone 84)."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ScopeFeatureVector(BaseModel):
    """Extracted numeric/categorical feature vector representing project architecture scope."""

    engine_id: str = Field(
        default="saas",
        description="Base architecture engine: 'landing' | 'multipage' | 'saas' | 'standalone_embed'",
    )
    total_features: int = Field(
        default=0, ge=0, description="Total count of active functional modules"
    )
    auth_security_count: int = Field(
        default=0, ge=0, description="Count of auth/security/RBAC modules"
    )
    database_storage_count: int = Field(
        default=0, ge=0, description="Count of database/storage/caching modules"
    )
    ai_vector_count: int = Field(
        default=0, ge=0, description="Count of AI/RAG/Vector search modules"
    )
    realtime_voice_count: int = Field(
        default=0, ge=0, description="Count of real-time WebRTC or Voice AI modules"
    )
    payment_billing_count: int = Field(
        default=0, ge=0, description="Count of payment gateway/escrow/subscription modules"
    )
    admin_rbac_count: int = Field(
        default=0, ge=0, description="Count of administration / CRM control decks"
    )
    dependency_depth: int = Field(
        default=1, ge=1, description="Longest topological dependency path in the DAG"
    )
    brand_complexity_weight: float = Field(
        default=1.0, ge=0.0, description="Weight of visual design, token systems, and motion"
    )
    maintenance_tier_weight: float = Field(
        default=0.0, ge=0.0, description="SLA operational maintenance tier weight"
    )


class TopEffortDriver(BaseModel):
    """Component driving significant variance or engineering hours."""

    feature_name: str = Field(..., description="Feature or subsystem identifier")
    category: str = Field(..., description="Subsystem category (e.g. 'AI/RAG', 'Real-Time Voice')")
    added_hours_estimate: float = Field(..., description="Estimated engineering hours contribution")
    risk_level: str = Field(default="low", description="'low' | 'medium' | 'high'")


class EffortPrediction(BaseModel):
    """Calibrated statistical prediction of sprint effort, calendar bounds, and complexity."""

    hours_p50: float = Field(
        ..., ge=0.0, description="Expected median engineering effort in hours (50th percentile)"
    )
    hours_p90: float = Field(
        ..., ge=0.0, description="Conservative risk-buffered effort in hours (90th percentile)"
    )
    calendar_days_min: int = Field(
        ..., ge=1, description="Optimistic delivery turnaround in calendar days"
    )
    calendar_days_max: int = Field(
        ..., ge=1, description="Conservative 95% confidence delivery turnaround in calendar days"
    )
    complexity_index: float = Field(
        ..., ge=1.0, le=5.0, description="Architectural complexity score from 1.0 to 5.0"
    )
    recommended_sprint_weeks: str = Field(
        ..., description="Human-readable sprint duration label (e.g. '1 to 2 Weeks Sprint')"
    )
    confidence_score: float = Field(
        default=0.92, ge=0.0, le=1.0, description="Regression certainty metric"
    )
    top_effort_drivers: list[TopEffortDriver] = Field(
        default_factory=list, description="Top individual subsystem effort contributors"
    )
    risk_factors: list[str] = Field(
        default_factory=list, description="Specific risk alerts (e.g. WebRTC concurrency, DAG depth)"
    )


class ProjectScopeInput(BaseModel):
    """Inbound request payload for estimating delivery timelines."""

    engine_id: str = Field(default="saas", description="Target engine ID")
    feature_ids: list[str] = Field(default_factory=list, description="List of selected feature IDs")
    brand_asset_id: str | None = Field(default=None, description="Selected brand asset package ID")
    maintenance_plan_id: str | None = Field(default=None, description="Selected monthly care plan ID")
    custom_notes: str | None = Field(default=None, description="Optional client RFP intent or notes")


class EffortEstimatorInterface(ABC):
    """Abstract interface for machine-learned effort & sprint delivery regression models."""

    @abstractmethod
    def predict_effort(self, vector: ScopeFeatureVector) -> EffortPrediction:
        """Calculate statistical effort bounds and complexity for a scope feature vector."""
        pass

    @abstractmethod
    def batch_predict(self, vectors: list[ScopeFeatureVector]) -> list[EffortPrediction]:
        """Perform batch inference across multiple scope vectors."""
        pass
