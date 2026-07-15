from pydantic import BaseModel, Field
from typing import Any


class VariantConfig(BaseModel):
    id: str
    traffic_pct: float = 50.0
    overrides: dict[str, Any] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    id: str
    variants: list[VariantConfig] = Field(default_factory=list)
