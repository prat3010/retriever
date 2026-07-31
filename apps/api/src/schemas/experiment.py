from typing import Literal

from pydantic import BaseModel, Field

from src.domain.abstractions.experiment import VariantConfig


class CreateExperimentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the experiment.")
    description: str = Field(default="", max_length=1000, description="Optional experiment hypothesis/notes.")
    variants: list[VariantConfig] = Field(..., min_length=1, description="List of experiment variants.")


class UpdateExperimentRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    variants: list[VariantConfig] | None = None


class UpdateExperimentStatusRequest(BaseModel):
    status: Literal["draft", "active", "paused", "completed"] = Field(..., description="Target lifecycle status.")


class VariantMetricItem(BaseModel):
    variantId: str
    variantName: str
    trafficPct: float
    totalRequests: int
    totalTokens: int
    avgLatencyMs: float
    p95LatencyMs: float
    avgFeedbackRating: float
    errorRate: float


class ExperimentMetricsResponse(BaseModel):
    experimentId: str
    experimentName: str
    status: str
    totalExperimentRequests: int
    variants: list[VariantMetricItem]
