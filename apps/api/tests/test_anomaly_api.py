"""API integration tests for Telemetry Anomaly Sentinel & Abuse Guard (Milestone 83)."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.config import settings
from src.container import anomaly_sentinel_service
from src.domain.abstractions.anomaly import AnomalyScore
from src.main import app

client = TestClient(app)


def test_admin_list_anomalies_endpoint(monkeypatch):
    """Verify GET /v1/admin/telemetry/anomalies endpoint returns paginated anomalies."""
    mock_list = AsyncMock(
        return_value=(
            [
                {
                    "anomaly_id": "anom_123",
                    "tenant_id": "tn_test",
                    "entity_id": "key_456",
                    "entity_type": "api_key",
                    "risk_level": "HIGH",
                    "anomaly_score": 0.78,
                    "algorithm_used": "isolation_forest",
                    "features": {"request_velocity_rpm": 250.0},
                    "contributing_factors": ["High velocity"],
                    "is_quarantined": False,
                    "status": "active",
                }
            ],
            1,
        )
    )
    monkeypatch.setattr(anomaly_sentinel_service, "list_anomalies", mock_list)

    response = client.get(
        "/v1/admin/telemetry/anomalies?limit=10",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["anomaly_id"] == "anom_123"
    assert data["items"][0]["risk_level"] == "HIGH"


def test_admin_trigger_scan_endpoint(monkeypatch):
    """Verify POST /v1/admin/telemetry/anomalies/scan triggers on-demand evaluation."""
    mock_scan = AsyncMock(
        return_value=[
            AnomalyScore(
                entity_id="key_flood_999",
                entity_type="api_key",
                tenant_id="tn_test",
                anomaly_score=0.91,
                is_anomaly=True,
                risk_level="CRITICAL",
                contributing_factors=["Velocity 400 rpm"],
                algorithm_used="isolation_forest",
            )
        ]
    )
    monkeypatch.setattr(anomaly_sentinel_service, "scan_telemetry", mock_scan)

    response = client.post(
        "/v1/admin/telemetry/anomalies/scan",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={"lookback_minutes": 30, "auto_quarantine": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_evaluated"] == 1
    assert data["anomalies_detected"] == 1
    assert data["quarantined_count"] == 1
    assert data["scores"][0]["entity_id"] == "key_flood_999"


def test_admin_resolve_anomaly_endpoint(monkeypatch):
    """Verify POST /v1/admin/telemetry/anomalies/{id}/resolve marks event resolved."""
    mock_resolve = AsyncMock(return_value=True)
    monkeypatch.setattr(anomaly_sentinel_service, "resolve_anomaly", mock_resolve)

    response = client.post(
        "/v1/admin/telemetry/anomalies/anom_test_99/resolve",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={"notes": "Investigated and verified benign customer load test."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["anomaly_id"] == "anom_test_99"


def test_admin_quarantine_and_unquarantine_api_key(monkeypatch):
    """Verify POST /v1/admin/api-keys/{id}/quarantine and /unquarantine."""
    mock_quarantine = AsyncMock(return_value=True)
    mock_unquarantine = AsyncMock(return_value=True)
    monkeypatch.setattr(anomaly_sentinel_service, "quarantine_key", mock_quarantine)
    monkeypatch.setattr(anomaly_sentinel_service, "unquarantine_key", mock_unquarantine)

    # 1. Quarantine
    res_q = client.post(
        "/v1/admin/api-keys/key_bad_actor/quarantine",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={"tenant_id": "tn_test", "reason": "Compromised credential detected"},
    )
    assert res_q.status_code == 200
    assert res_q.json()["quarantined"] is True

    # 2. Unquarantine
    res_uq = client.post(
        "/v1/admin/api-keys/key_bad_actor/unquarantine",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
    )
    assert res_uq.status_code == 200
    assert res_uq.json()["active"] is True
