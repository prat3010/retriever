from typing import Any, Literal

from pydantic import BaseModel, Field


class VariantConfig(BaseModel):
    id: str
    name: str = ""
    traffic_pct: float = 50.0
    overrides: dict[str, Any] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    status: Literal["draft", "active", "paused", "completed"] = "draft"
    variants: list[VariantConfig] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
