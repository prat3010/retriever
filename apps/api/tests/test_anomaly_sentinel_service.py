"""Unit tests for AnomalySentinelService domain orchestration (Milestone 83)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cognitive.anomaly_detector_adapter import AnomalyDetectorAdapter
from src.domain.abstractions.anomaly import (
    AnomalyScore,
)
from src.domain.telemetry.anomaly_sentinel_service import (
    AnomalySentinelService,
    calculate_shannon_entropy,
)


def test_shannon_entropy_calculation():
    """Verify Shannon entropy mathematical properties."""
    # Empty string
    assert calculate_shannon_entropy("") == 0.0

    # Single repeating character (zero uncertainty)
    assert calculate_shannon_entropy("aaaaaaa") == 0.0

    # High variety / natural English text
    entropy_en = calculate_shannon_entropy("The quick brown fox jumps over the lazy dog.")
    assert 3.5 <= entropy_en <= 5.0

    # Two equally probable characters (1 bit)
    assert round(calculate_shannon_entropy("abababab"), 4) == 1.0


class DummyLog:
    def __init__(
        self,
        key_id: str,
        tenant_id: str,
        input_tokens: int = 500,
        output_tokens: int = 250,
        latency_ms: int = 200,
        cost_usd: float = 0.01,
        notes: str = "normal query",
    ):
        self.key_id = key_id
        self.tenant_id = tenant_id
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms
        self.cost_usd = cost_usd
        self.notes = notes


@pytest.mark.asyncio
async def test_feature_extraction_from_logs():
    """Verify inference logs are aggregated correctly into AnomalyFeatureVectors."""
    service = AnomalySentinelService(detector=AnomalyDetectorAdapter())
    now = datetime.now(UTC)
    start = now - timedelta(minutes=30)

    logs = [
        DummyLog("key_1", "tn_1", input_tokens=1000, output_tokens=100, latency_ms=300),
        DummyLog("key_1", "tn_1", input_tokens=800, output_tokens=100, latency_ms=200),
        DummyLog("key_2", "tn_2", input_tokens=200, output_tokens=400, latency_ms=150),
    ]

    vectors = service.extract_features_from_logs(logs, start, now)
    assert len(vectors) == 2

    v1 = next(v for v in vectors if v.entity_id == "key_1")
    assert v1.request_count == 2
    assert v1.tenant_id == "tn_1"
    assert v1.input_tokens_avg == 900.0
    assert v1.output_tokens_avg == 100.0
    assert v1.token_ratio > 8.0


@pytest.mark.asyncio
async def test_scan_telemetry_triggers_quarantine_and_alert():
    """Verify scan_telemetry triggers repository quarantine and alert dispatch for critical anomalies."""
    mock_detector = MagicMock()
    mock_repo = AsyncMock()
    mock_alert_svc = AsyncMock()
    mock_inference_repo = AsyncMock()

    # Synthetic critical anomaly return from detector
    critical_score = AnomalyScore(
        entity_id="key_compromised_1",
        entity_type="api_key",
        tenant_id="tn_target",
        anomaly_score=0.92,
        is_anomaly=True,
        risk_level="CRITICAL",
        contributing_factors=["Abnormal request velocity (600 rpm)", "High token ratio (90x)"],
        algorithm_used="isolation_forest",
        features={"request_velocity_rpm": 600.0},
    )
    mock_detector.batch_detect.return_value = [critical_score]
    mock_inference_repo.get_recent_logs.return_value = [
        DummyLog("key_compromised_1", "tn_target", latency_ms=5000)
    ]

    service = AnomalySentinelService(
        detector=mock_detector,
        repository=mock_repo,
        alert_service=mock_alert_svc,
        inference_repo=mock_inference_repo,
    )

    scores = await service.scan_telemetry(lookback_minutes=15, auto_quarantine=True)

    assert len(scores) == 1
    assert scores[0].anomaly_score == 0.92

    # 1. Anomaly was recorded in repository
    mock_repo.record_anomaly.assert_awaited_once()

    # 2. Key was automatically quarantined due to CRITICAL level
    mock_repo.quarantine_key.assert_awaited_once_with(
        key_id="key_compromised_1",
        tenant_id="tn_target",
        reason="Automated Sentinel Quarantine: Abnormal request velocity (600 rpm); High token ratio (90x)",
        level="CRITICAL",
    )

    # 3. Security alert was dispatched
    mock_alert_svc.dispatch_anomaly_alert.assert_awaited_once_with(critical_score)


@pytest.mark.asyncio
async def test_service_unquarantine_delegation():
    """Verify unquarantine_key delegates cleanly to the repository."""
    mock_repo = AsyncMock()
    mock_repo.unquarantine_key.return_value = True

    service = AnomalySentinelService(detector=AnomalyDetectorAdapter(), repository=mock_repo)
    success = await service.unquarantine_key("key_123", resolved_by="admin_prateek")

    assert success is True
    mock_repo.unquarantine_key.assert_awaited_once_with("key_123", "admin_prateek")
