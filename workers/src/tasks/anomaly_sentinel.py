"""Asynchronous Celery Task for Real-Time Telemetry Anomaly Sentinel (Milestone 83).

Periodically evaluates streaming inference telemetry logs across tenants,
flags automated scraping and credential abuse via Isolation Forest,
enforces API key quarantine, and triggers SLA alerts.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from celery import Task

from workers.src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=Task,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def run_telemetry_anomaly_sentinel(
    self,
    lookback_minutes: int = 60,
    tenant_id: str | None = None,
    auto_quarantine: bool = True,
) -> dict[str, Any]:
    """Execute asynchronous telemetry anomaly scan and abuse quarantine enforcement."""
    logger.info(
        f"Starting Telemetry Anomaly Sentinel scan (lookback: {lookback_minutes}m, tenant: {tenant_id or 'all'})."
    )

    async def _execute_scan():
        from src.container import anomaly_sentinel_service

        scores = await anomaly_sentinel_service.scan_telemetry(
            lookback_minutes=lookback_minutes,
            tenant_id=tenant_id,
            auto_quarantine=auto_quarantine,
        )

        anomalies = [s for s in scores if s.is_anomaly]
        quarantined = [s for s in anomalies if s.risk_level == "CRITICAL" and s.entity_type == "api_key"]

        return {
            "status": "completed",
            "total_evaluated": len(scores),
            "anomalies_detected": len(anomalies),
            "quarantined_count": len(quarantined),
            "anomalous_entities": [
                {
                    "entity_id": a.entity_id,
                    "tenant_id": a.tenant_id,
                    "score": a.anomaly_score,
                    "risk": a.risk_level,
                    "factors": a.contributing_factors[:2],
                }
                for a in anomalies
            ],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If in an existing loop, use an executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _execute_scan()).result()
        else:
            result = loop.run_until_complete(_execute_scan())
        return result
    except Exception as exc:
        logger.error(f"Anomaly Sentinel scan failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
