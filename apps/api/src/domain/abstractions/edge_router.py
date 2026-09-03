from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RegionCode(StrEnum):
    AP_SOUTH = "ap-south"  # Mumbai / Singapore / Asia-Pacific Hub (Primary Master)
    US_EAST = "us-east"  # N. Virginia / New York / Americas
    EU_CENTRAL = "eu-central"  # Frankfurt / London / Europe & Middle East
    AUTO = "auto"  # Automatic Geo-IP resolution


class ReplicaHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    FALLBACK_PRIMARY = "fallback_primary"  # Active when replica is unconfigured, using Master


class RegionNodeConfig(BaseModel):
    region_code: RegionCode
    region_name: str
    city: str
    is_primary: bool = False
    is_configured: bool = False
    endpoint_display: str
    status: ReplicaHealthStatus = ReplicaHealthStatus.FALLBACK_PRIMARY
    latency_ms: float | None = None
    last_probe_at: datetime | None = None


class EdgeRoutingDecision(BaseModel):
    client_country: str
    detected_continent: str
    selected_region: RegionCode
    target_endpoint: str
    is_fallback: bool
    estimated_primary_latency_ms: float
    estimated_replica_latency_ms: float
    estimated_reduction_pct: float
    routing_reason: str


class MultiRegionClusterStatus(BaseModel):
    primary_region: RegionCode = RegionCode.AP_SOUTH
    total_regions: int = 3
    configured_replicas: int = 0
    active_routing_mode: str = "Geo-IP Adaptive Routing"
    regions: list[RegionNodeConfig]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RegionProbeResult(BaseModel):
    region_code: RegionCode
    status: ReplicaHealthStatus
    latency_ms: float
    probed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RegionProbeResponse(BaseModel):
    probed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    results: list[RegionProbeResult]
    overall_health: str


class EdgeRouterInterface(ABC):
    """Abstract interface for Geo-IP edge routing and read-replica selection."""

    @abstractmethod
    def resolve_region(self, country_code: str | None) -> EdgeRoutingDecision:
        """Resolve client country code to optimal target regional node."""
        pass

    @abstractmethod
    def get_cluster_status(self) -> MultiRegionClusterStatus:
        """Retrieve multi-region cluster topology and active replica health states."""
        pass
