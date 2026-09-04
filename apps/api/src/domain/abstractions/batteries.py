from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class BatteryCategory(StrEnum):
    RETRIEVAL = "retrieval"
    ML_INTELLIGENCE = "ml_intelligence"
    SAFETY_DEFENSE = "safety_defense"
    COMPUTATION_GRAPH = "computation_graph"
    BACKGROUND_WORKFLOWS = "background_workflows"



class BatteryStatus(StrEnum):
    ACTIVE = "active"
    STANDBY = "standby"
    DISABLED = "disabled"


class PlatformBatteryDTO(BaseModel):
    id: str = Field(..., description="Unique slug for the battery, e.g. 'colbert_maxsim'")
    name: str = Field(..., description="Human-readable battery name")
    category: BatteryCategory
    status: BatteryStatus
    algorithm_foundation: str = Field(..., description="Mathematical or algorithmic architecture")
    milestone: str = Field(..., description="Origin milestone and version")
    latency_profile: str = Field(..., description="Benchmark latency profile")
    description: str = Field(..., description="Operational capability explanation")
    active_parameters: dict[str, Any] = Field(default_factory=dict)
    health_check_endpoint: str | None = None


class PlatformBatteriesResponse(BaseModel):
    total_batteries: int
    active_count: int
    standby_count: int
    batteries: list[PlatformBatteryDTO]
