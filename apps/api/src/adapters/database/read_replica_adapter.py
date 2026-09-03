import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.adapters.database.connection import engine as primary_engine
from src.config import settings
from src.domain.abstractions.edge_router import (
    RegionCode,
    RegionProbeResponse,
    RegionProbeResult,
    ReplicaHealthStatus,
)
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.routing.edge_router_service import EdgeRouterService

logger = logging.getLogger(__name__)


class ReadReplicaAdapter:
    """Infrastructure adapter managing multi-region read-replica connection pools and health probes."""

    def __init__(
        self,
        router_service: EdgeRouterService,
        primary_eng: AsyncEngine | None = None,
    ) -> None:
        self.router_service = router_service
        self.primary_engine: AsyncEngine = primary_eng or primary_engine
        self.primary_region = RegionCode(settings.PRIMARY_REGION)

        self._engines: dict[RegionCode, AsyncEngine] = {
            self.primary_region: self.primary_engine,
        }
        self._session_makers: dict[RegionCode, async_sessionmaker[AsyncSession]] = {
            self.primary_region: async_sessionmaker(
                bind=self.primary_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            ),
        }

        # Initialize optional regional read-replicas
        self._init_replica(RegionCode.US_EAST, settings.REPLICA_US_EAST_DATABASE_URL)
        self._init_replica(RegionCode.EU_CENTRAL, settings.REPLICA_EU_CENTRAL_DATABASE_URL)
        if settings.REPLICA_AP_SOUTH_DATABASE_URL and self.primary_region != RegionCode.AP_SOUTH:
            self._init_replica(RegionCode.AP_SOUTH, settings.REPLICA_AP_SOUTH_DATABASE_URL)

    def _init_replica(self, region: RegionCode, url: str | None) -> None:
        if not url:
            return
        try:
            eng = create_async_engine(
                url,
                pool_size=5,
                max_overflow=5,
                pool_timeout=10,
                pool_recycle=1800,
                pool_pre_ping=True,
            )
            self._engines[region] = eng
            self._session_makers[region] = async_sessionmaker(
                bind=eng,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            self.router_service.set_node_status(region, ReplicaHealthStatus.HEALTHY)
            logger.info("Initialized read-replica engine for region: %s", region.value)
        except Exception as e:
            logger.warning("Failed to initialize read-replica for %s: %s", region.value, e)
            self.router_service.set_node_status(region, ReplicaHealthStatus.UNREACHABLE)

    async def probe_regional_health(self) -> RegionProbeResponse:
        """Ping all registered regional endpoints to measure live latency and verify connectivity."""
        probe_results: list[RegionProbeResult] = []

        all_regions = [RegionCode.AP_SOUTH, RegionCode.US_EAST, RegionCode.EU_CENTRAL]

        for region in all_regions:
            eng = self._engines.get(region)
            if not eng:
                # Replica not configured; report fallback
                probe_results.append(
                    RegionProbeResult(
                        region_code=region,
                        status=ReplicaHealthStatus.FALLBACK_PRIMARY,
                        latency_ms=0.0,
                    )
                )
                self.router_service.set_node_status(region, ReplicaHealthStatus.FALLBACK_PRIMARY)
                continue

            start_t = time.perf_counter()
            try:
                async with eng.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
                status = ReplicaHealthStatus.HEALTHY
            except Exception as e:
                logger.debug("Probe failed for region %s: %s", region.value, e)
                elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
                # Primary should not be marked unreachable lightly; replicas fallback
                status = ReplicaHealthStatus.UNREACHABLE if region == self.primary_region else ReplicaHealthStatus.FALLBACK_PRIMARY

            self.router_service.set_node_status(region, status, elapsed_ms)
            probe_results.append(
                RegionProbeResult(
                    region_code=region,
                    status=status,
                    latency_ms=elapsed_ms,
                )
            )

        overall = "HEALTHY" if all(r.status in (ReplicaHealthStatus.HEALTHY, ReplicaHealthStatus.FALLBACK_PRIMARY) for r in probe_results) else "DEGRADED"

        return RegionProbeResponse(
            results=probe_results,
            overall_health=overall,
        )

    @asynccontextmanager
    async def get_read_session(
        self,
        region: RegionCode | None = None,
        tenant_id: str | None = None,
    ) -> AsyncGenerator[AsyncSession, None]:
        """Provide a read-only transactional session targeting the optimal regional replica or master."""
        target_region = region or self.primary_region
        maker = self._session_makers.get(target_region) or self._session_makers[self.primary_region]

        async with maker() as session:
            async with session.begin():
                if tenant_id:
                    try:
                        valid_uuid = uuid.UUID(str(tenant_id))
                    except ValueError as e:
                        raise TenantIsolationViolationError(f"Invalid tenant ID format: {e}") from e
                    await session.execute(
                        text(f"SET LOCAL app.current_tenant_id = '{valid_uuid}'"),
                    )
                else:
                    await session.execute(text("SET LOCAL app.current_tenant_id = ''"))
                yield session
