from datetime import UTC, datetime

from src.domain.abstractions.edge_router import (
    EdgeRouterInterface,
    EdgeRoutingDecision,
    MultiRegionClusterStatus,
    RegionCode,
    RegionNodeConfig,
    ReplicaHealthStatus,
)

# Continents & ISO-3166-1 Country Code mappings
AMERICAS_COUNTRIES: frozenset[str] = frozenset({
    "US", "CA", "MX", "BR", "AR", "CL", "CO", "PE", "VE", "UY", "PY", "BO", "EC", "CR", "PA", "JM", "DO",
})

EUROPE_ME_AFRICA_COUNTRIES: frozenset[str] = frozenset({
    "GB", "DE", "FR", "IT", "ES", "NL", "SE", "CH", "PL", "NO", "DK", "FI", "IE", "BE", "AT", "PT",
    "GR", "CZ", "RO", "HU", "AE", "SA", "IL", "ZA", "EG", "TR", "UA", "RU", "NG", "KE", "MA", "QA",
})

APAC_COUNTRIES: frozenset[str] = frozenset({
    "IN", "SG", "JP", "AU", "NZ", "KR", "ID", "MY", "TH", "VN", "PH", "TW", "HK", "CN", "PK", "BD", "LK", "NP",
})

# Typical empirical optical round-trip latencies (ms)
LATENCY_PROFILES: dict[RegionCode, dict[str, float]] = {
    RegionCode.US_EAST: {
        "primary_rtt": 215.0,  # US to AP-South Master
        "replica_rtt": 18.0,   # US to US-East Replica
    },
    RegionCode.EU_CENTRAL: {
        "primary_rtt": 158.0,  # Europe to AP-South Master
        "replica_rtt": 22.0,   # Europe to EU-Central Replica
    },
    RegionCode.AP_SOUTH: {
        "primary_rtt": 15.0,   # APAC to AP-South Master
        "replica_rtt": 15.0,   # APAC local
    },
}


class EdgeRouterService(EdgeRouterInterface):
    """Pure domain service for determining topologically optimal regional read-replicas."""

    def __init__(
        self,
        configured_regions: set[RegionCode] | None = None,
        primary_region: RegionCode = RegionCode.AP_SOUTH,
    ) -> None:
        self._primary_region = primary_region
        self._configured_regions: set[RegionCode] = configured_regions or {primary_region}
        self._node_health: dict[RegionCode, ReplicaHealthStatus] = {
            RegionCode.AP_SOUTH: ReplicaHealthStatus.HEALTHY,
            RegionCode.US_EAST: ReplicaHealthStatus.HEALTHY if RegionCode.US_EAST in self._configured_regions else ReplicaHealthStatus.FALLBACK_PRIMARY,
            RegionCode.EU_CENTRAL: ReplicaHealthStatus.HEALTHY if RegionCode.EU_CENTRAL in self._configured_regions else ReplicaHealthStatus.FALLBACK_PRIMARY,
        }
        self._node_latencies: dict[RegionCode, float] = {
            RegionCode.AP_SOUTH: 14.5,
            RegionCode.US_EAST: 18.2 if RegionCode.US_EAST in self._configured_regions else 215.0,
            RegionCode.EU_CENTRAL: 21.8 if RegionCode.EU_CENTRAL in self._configured_regions else 158.0,
        }

    def set_node_status(
        self,
        region: RegionCode,
        status: ReplicaHealthStatus,
        latency_ms: float | None = None,
    ) -> None:
        """Update live status and ping latency for a regional node."""
        self._node_health[region] = status
        if latency_ms is not None:
            self._node_latencies[region] = latency_ms

    def resolve_region(self, country_code: str | None) -> EdgeRoutingDecision:
        """Map ISO country code to optimal target regional node with fallback assurance."""
        norm_country = (country_code or "DEFAULT").strip().upper()

        if norm_country in AMERICAS_COUNTRIES:
            continent = "Americas"
            preferred_region = RegionCode.US_EAST
        elif norm_country in EUROPE_ME_AFRICA_COUNTRIES:
            continent = "Europe / Middle East"
            preferred_region = RegionCode.EU_CENTRAL
        elif norm_country in APAC_COUNTRIES:
            continent = "Asia-Pacific & Oceania"
            preferred_region = RegionCode.AP_SOUTH
        else:
            continent = "Global (Default)"
            preferred_region = self._primary_region

        profile = LATENCY_PROFILES.get(preferred_region, LATENCY_PROFILES[RegionCode.AP_SOUTH])
        primary_rtt = profile["primary_rtt"]
        replica_rtt = profile["replica_rtt"]

        # Check if the preferred region is configured and healthy
        is_configured = preferred_region in self._configured_regions
        health = self._node_health.get(preferred_region, ReplicaHealthStatus.FALLBACK_PRIMARY)

        if preferred_region != self._primary_region and (not is_configured or health != ReplicaHealthStatus.HEALTHY):
            # Fallback to Primary Master
            selected_region = self._primary_region
            is_fallback = True
            est_reduction = 0.0
            endpoint = "https://rag.prateeq.in"
            reason = f"Preferred region '{preferred_region.value}' unconfigured or degraded; routed to Primary Master."
        else:
            selected_region = preferred_region
            is_fallback = False
            if primary_rtt > replica_rtt:
                est_reduction = round(((primary_rtt - replica_rtt) / primary_rtt) * 100.0, 1)
            else:
                est_reduction = 0.0
            endpoint = f"https://{preferred_region.value}.rag.prateeq.in" if preferred_region != self._primary_region else "https://rag.prateeq.in"
            reason = f"Optimally routed to local {continent} edge replica ({selected_region.value})."

        return EdgeRoutingDecision(
            client_country=norm_country,
            detected_continent=continent,
            selected_region=selected_region,
            target_endpoint=endpoint,
            is_fallback=is_fallback,
            estimated_primary_latency_ms=primary_rtt,
            estimated_replica_latency_ms=replica_rtt if not is_fallback else primary_rtt,
            estimated_reduction_pct=est_reduction,
            routing_reason=reason,
        )

    def get_cluster_status(self) -> MultiRegionClusterStatus:
        """Return the multi-region topology, configured status, and current latency."""
        regions_list = [
            RegionNodeConfig(
                region_code=RegionCode.AP_SOUTH,
                region_name="Asia-Pacific Hub",
                city="Mumbai / Singapore",
                is_primary=True,
                is_configured=True,
                endpoint_display="rag.prateeq.in (Primary Master)",
                status=self._node_health.get(RegionCode.AP_SOUTH, ReplicaHealthStatus.HEALTHY),
                latency_ms=self._node_latencies.get(RegionCode.AP_SOUTH, 14.5),
                last_probe_at=datetime.now(UTC),
            ),
            RegionNodeConfig(
                region_code=RegionCode.US_EAST,
                region_name="Americas Edge",
                city="N. Virginia / New York",
                is_primary=False,
                is_configured=RegionCode.US_EAST in self._configured_regions,
                endpoint_display="us-east.rag.prateeq.in" if RegionCode.US_EAST in self._configured_regions else "Fallback to Primary Master",
                status=self._node_health.get(RegionCode.US_EAST, ReplicaHealthStatus.FALLBACK_PRIMARY),
                latency_ms=self._node_latencies.get(RegionCode.US_EAST, 215.0),
                last_probe_at=datetime.now(UTC),
            ),
            RegionNodeConfig(
                region_code=RegionCode.EU_CENTRAL,
                region_name="Europe & ME Edge",
                city="Frankfurt / London",
                is_primary=False,
                is_configured=RegionCode.EU_CENTRAL in self._configured_regions,
                endpoint_display="eu-central.rag.prateeq.in" if RegionCode.EU_CENTRAL in self._configured_regions else "Fallback to Primary Master",
                status=self._node_health.get(RegionCode.EU_CENTRAL, ReplicaHealthStatus.FALLBACK_PRIMARY),
                latency_ms=self._node_latencies.get(RegionCode.EU_CENTRAL, 158.0),
                last_probe_at=datetime.now(UTC),
            ),
        ]

        configured_count = sum(1 for r in regions_list if r.is_configured and not r.is_primary)

        return MultiRegionClusterStatus(
            primary_region=self._primary_region,
            total_regions=len(regions_list),
            configured_replicas=configured_count,
            active_routing_mode="Geo-IP Adaptive Dynamic Routing",
            regions=regions_list,
            timestamp=datetime.now(UTC),
        )
