"""Schemas for Scoping Intent Classification (M85.11)."""

from pydantic import BaseModel, Field


class ClassifyIntentRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Natural language project description or scoping requirement",
    )
    model: str | None = Field(None, description="Optional LLM model override")


class ScopingIntentResult(BaseModel):
    archetype_id: str = Field(
        default="saas_app",
        description="Recommended archetype identifier",
    )
    base_engine_id: str = Field(
        default="saas",
        description="Base architecture engine ('landing' | 'multipage' | 'saas')",
    )
    feature_ids: list[str] = Field(
        default_factory=list,
        description="Recommended feature IDs from catalog",
    )
    brand_asset_id: str = Field(
        default="none",
        description="Recommended brand asset level ('none' | 'basic' | 'comprehensive')",
    )
    maintenance_plan_id: str = Field(
        default="essential",
        description="Recommended maintenance tier ('essential' | 'standard' | 'growth' | 'premium')",
    )
    suggested_timeline: str = Field(
        default="3 to 4 Weeks",
        description="Estimated delivery window",
    )
    confidence_score: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )
    summary_rationale: str = Field(
        default="",
        description="Technical rationale for the selected architecture",
    )
    retriever_engine_recommended: bool = Field(
        default=False,
        description="Whether Retriever RAG/vector engine is recommended",
    )
    unrecognized_requirements: list[str] = Field(
        default_factory=list,
        description="Any requirements outside standard catalog",
    )


class ClassifyIntentResponse(BaseModel):
    success: bool = True
    data: ScopingIntentResult
    model: str
    provider: str
    inputTokens: int = 0
    outputTokens: int = 0
    latencyMs: int = 0
