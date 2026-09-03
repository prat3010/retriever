"""Domain Service for Real-Time Telemetry Anomaly Sentinel & Abuse Guard.

Orchestrates behavioral feature extraction from streaming inference telemetry,
invokes unsupervised Isolation Forest scoring, enforces automated key quarantine,
and dispatches security incident alerts.
"""

import logging
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from src.domain.abstractions.anomaly import (
    AnomalyFeatureVector,
    AnomalyFilterParams,
    AnomalyScore,
    BaseAnomalyDetector,
    BaseAnomalyRepository,
)

logger = logging.getLogger(__name__)


def calculate_shannon_entropy(text: str) -> float:
    """Calculate character-level Shannon entropy H(X) in bits."""
    if not text:
        return 0.0
    freq = defaultdict(int)
    for char in text:
        freq[char] += 1
    length = len(text)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return float(entropy)


class AnomalySentinelService:
    """Domain service managing telemetry anomaly scanning, scoring, and credential quarantine."""

    def __init__(
        self,
        detector: BaseAnomalyDetector,
        repository: BaseAnomalyRepository | None = None,
        alert_service: Any = None,
        inference_repo: Any = None,
    ) -> None:
        self.detector = detector
        self.repository = repository
        self.alert_service = alert_service
        self.inference_repo = inference_repo

    def extract_features_from_logs(
        self,
        logs: list[Any],
        window_start: datetime,
        window_end: datetime,
    ) -> list[AnomalyFeatureVector]:
        """Aggregate raw inference log records into structured AnomalyFeatureVector objects."""
        duration_minutes = max(1.0, (window_end - window_start).total_seconds() / 60.0)
        grouped = defaultdict(list)

        for log in logs:
            key = getattr(log, "key_id", None) or getattr(log, "user_id", None) or getattr(log, "tenant_id", None)
            entity_id = str(key) if key else "anonymous"
            t_id = str(getattr(log, "tenant_id", "unknown"))
            grouped[(entity_id, t_id)].append(log)

        vectors: list[AnomalyFeatureVector] = []
        for (entity_id, tenant_id), entity_logs in grouped.items():
            req_count = len(entity_logs)
            velocity_rpm = req_count / duration_minutes

            inputs = [getattr(entry, "input_tokens", 0) or 0 for entry in entity_logs]
            outputs = [getattr(entry, "output_tokens", 0) or 0 for entry in entity_logs]
            latencies = [float(getattr(entry, "latency_ms", 0) or 0) for entry in entity_logs]
            costs = [float(getattr(entry, "cost_usd", 0.0) or 0.0) for entry in entity_logs]

            input_avg = sum(inputs) / req_count
            output_avg = sum(outputs) / req_count
            token_ratio = (sum(inputs) + 1.0) / (sum(outputs) + 1.0)

            # Latency P99 and variance
            sorted_lat = sorted(latencies)
            idx_p99 = min(len(sorted_lat) - 1, int(len(sorted_lat) * 0.99))
            p99_latency = sorted_lat[idx_p99] if sorted_lat else 0.0

            mean_lat = sum(latencies) / req_count
            lat_variance = sum((x - mean_lat) ** 2 for x in latencies) / req_count if req_count > 1 else 0.0

            # Shannon entropy on notes/prompts if available
            entropies: list[float] = []
            for entry in entity_logs:
                note = getattr(entry, "notes", None) or ""
                if note:
                    entropies.append(calculate_shannon_entropy(str(note)))
            prompt_entropy = (sum(entropies) / len(entropies)) if entropies else 3.5  # Natural language default

            # Error rate estimation from notes or status
            error_count = sum(
                1 for entry in entity_logs if "error" in str(getattr(entry, "notes", "")).lower()
            )

            error_rate = error_count / req_count

            # Cost velocity ($/hr)
            total_cost = sum(costs)
            cost_velocity_usd = total_cost * (60.0 / duration_minutes)

            vectors.append(
                AnomalyFeatureVector(
                    entity_id=entity_id,
                    entity_type="api_key" if entity_id != tenant_id else "tenant",
                    tenant_id=tenant_id,
                    window_start=window_start,
                    window_end=window_end,
                    request_count=req_count,
                    request_velocity_rpm=round(velocity_rpm, 2),
                    input_tokens_avg=round(input_avg, 2),
                    output_tokens_avg=round(output_avg, 2),
                    token_ratio=round(token_ratio, 2),
                    prompt_entropy=round(prompt_entropy, 3),
                    p99_latency_ms=round(p99_latency, 2),
                    latency_variance=round(lat_variance, 2),
                    error_rate=round(error_rate, 4),
                    cost_velocity_usd=round(cost_velocity_usd, 4),
                )
            )

        return vectors

    async def scan_telemetry(
        self,
        lookback_minutes: int = 60,
        tenant_id: str | None = None,
        auto_quarantine: bool = True,
    ) -> list[AnomalyScore]:
        """Scan inference logs within lookback window, detect anomalies, and enforce quarantine."""
        now = datetime.now(UTC)
        window_start = now - timedelta(minutes=lookback_minutes)

        logs: list[Any] = []
        if self.inference_repo is not None and hasattr(self.inference_repo, "get_recent_logs"):
            try:
                logs = await self.inference_repo.get_recent_logs(
                    window_start=window_start, tenant_id=tenant_id
                )
            except Exception as e:
                logger.warning(f"Failed to query inference logs: {e}")

        if not logs:
            return []

        vectors = self.extract_features_from_logs(logs, window_start, now)
        scores = self.detector.batch_detect(vectors)

        for score in scores:
            if score.is_anomaly:
                # 1. Persist anomaly event in repository
                if self.repository is not None:
                    try:
                        await self.repository.record_anomaly(score, score.features)
                    except Exception as e:
                        logger.error(f"Failed to record anomaly event: {e}")

                # 2. Automated Key Quarantine for CRITICAL threats
                if auto_quarantine and score.risk_level == "CRITICAL" and score.entity_type == "api_key":
                    if self.repository is not None:
                        try:
                            quarantine_reason = "; ".join(score.contributing_factors[:2])
                            await self.repository.quarantine_key(
                                key_id=score.entity_id,
                                tenant_id=score.tenant_id,
                                reason=f"Automated Sentinel Quarantine: {quarantine_reason}",
                                level="CRITICAL",
                            )
                            logger.warning(
                                f"API Key {score.entity_id} quarantined due to CRITICAL anomaly ({score.anomaly_score:.2f})"
                            )
                        except Exception as e:
                            logger.error(f"Failed to quarantine API key {score.entity_id}: {e}")

                # 3. Trigger Security Incident Alert via AlertService
                if self.alert_service is not None and hasattr(self.alert_service, "dispatch_anomaly_alert"):
                    try:
                        await self.alert_service.dispatch_anomaly_alert(score)
                    except Exception as e:
                        logger.warning(f"Failed to dispatch anomaly alert webhook: {e}")

        return scores

    async def list_anomalies(
        self,
        tenant_id: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query security anomaly events."""
        if self.repository is None:
            return [], 0
        return await self.repository.list_anomalies(
            AnomalyFilterParams(
                tenant_id=tenant_id,
                risk_level=risk_level,
                status=status,
                limit=limit,
                offset=offset,
            )
        )

    async def resolve_anomaly(
        self, anomaly_id: str, resolved_by: str, notes: str | None = None
    ) -> bool:
        """Resolve a flagged security anomaly."""
        if self.repository is None:
            return False
        return await self.repository.resolve_anomaly(anomaly_id, resolved_by, notes)

    async def quarantine_key(
        self, key_id: str, tenant_id: str, reason: str, level: str = "CRITICAL"
    ) -> bool:
        """Manually quarantine an API key."""
        if self.repository is None:
            return False
        return await self.repository.quarantine_key(key_id, tenant_id, reason, level)

    async def unquarantine_key(self, key_id: str, resolved_by: str) -> bool:
        """Manually restore a quarantined API key to active status."""
        if self.repository is None:
            return False
        return await self.repository.unquarantine_key(key_id, resolved_by)
