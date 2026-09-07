"""Infrastructure Adapter for Multi-Cloud Health Probing (M99).

Implements MultiCloudHealthProbeProtocol:
- Performs asynchronous non-blocking HTTP health checks with timeout guards.
- Computes round-trip latency and validates status codes.
- Reports genuine health metrics and records network failures with status 503.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime

import httpx

from src.domain.abstractions.multicloud import (
    CloudRegionNode,
    MultiCloudHealthProbeProtocol,
    RegionHealthProbe,
)

logger = logging.getLogger(__name__)


class HttpMultiCloudHealthProbeAdapter(MultiCloudHealthProbeProtocol):
    """Adapter executing real HTTP probes across multi-cloud regions."""

    def __init__(
        self,
        probe_timeout_seconds: float = 1.5,
    ) -> None:
        self.probe_timeout_seconds = probe_timeout_seconds

    async def probe_node(self, node: CloudRegionNode) -> RegionHealthProbe:
        """Probes a single cloud region node."""
        probe_url = f"{node.endpoint_url.rstrip('/')}/health/liveness"
        start_time = time.perf_counter()
        now_str = datetime.now(UTC).isoformat()

        try:
            async with httpx.AsyncClient(timeout=self.probe_timeout_seconds) as client:
                resp = await client.get(probe_url)
                latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                is_healthy = resp.status_code == 200

                return RegionHealthProbe(
                    node_id=node.node_id,
                    region=node.region,
                    probe_url=probe_url,
                    latency_ms=latency_ms,
                    status_code=resp.status_code,
                    is_healthy=is_healthy,
                    failure_reason=None if is_healthy else f"HTTP {resp.status_code}",
                    probed_at=now_str,
                    is_simulated=False,
                )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.warning("Probe failed for region %s (%s): %s", node.region, probe_url, exc)
            return RegionHealthProbe(
                node_id=node.node_id,
                region=node.region,
                probe_url=probe_url,
                latency_ms=latency_ms,
                status_code=503,
                is_healthy=False,
                failure_reason=str(exc),
                probed_at=now_str,
                is_simulated=False,
            )

    async def probe_all_regions(self, nodes: list[CloudRegionNode]) -> list[RegionHealthProbe]:
        """Concurrently executes health probes across all cloud region nodes."""
        tasks = [self.probe_node(node) for node in nodes]
        return await asyncio.gather(*tasks)
