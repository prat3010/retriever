"""Unit and API tests for Milestone 76: Live Database Telemetry Aggregations."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.domain.abstractions.telemetry import TenantLiveTelemetry
from src.domain.telemetry.telemetry_service import LiveTelemetryService
from src.main import app

client = TestClient(app)


# ── 1. Unit Tests: Live Telemetry Service ────────────────────────────────────

@pytest.mark.asyncio
async def test_live_telemetry_service_fallback():
    """Verify LiveTelemetryService returns valid fallback defaults when unconfigured."""
    service = LiveTelemetryService(repository=None)
    telemetry = await service.get_live_telemetry("tn_test_fallback")

    assert telemetry.tenant_id == "tn_test_fallback"
    assert telemetry.monthly_tokens_used == 0
    assert telemetry.documents_count == 0
    assert telemetry.storage_bytes_used == 0
    assert telemetry.satisfaction_rate == 100
    assert telemetry.avg_faithfulness == 1.0


@pytest.mark.asyncio
async def test_live_telemetry_service_with_mock_repo():
    """Verify LiveTelemetryService delegates cleanly to underlying SQL repository."""
    mock_repo = AsyncMock()
    mock_repo.get_tenant_live_telemetry.return_value = TenantLiveTelemetry(
        tenant_id="tn_test_live",
        monthly_tokens_used=45000,
        documents_count=12,
        storage_bytes_used=5242880,
        cache_hits=80,
        latency_saved_ms=68000,
        cost_saved_usd=2.40,
        thumbs_up=38,
        thumbs_down=2,
        satisfaction_rate=95,
        avg_faithfulness=0.96,
        avg_precision=0.92,
        hallucination_index=0.04,
        p99_latency_ms=450.0,
    )

    service = LiveTelemetryService(repository=mock_repo)
    telemetry = await service.get_live_telemetry("tn_test_live")

    assert telemetry.tenant_id == "tn_test_live"
    assert telemetry.monthly_tokens_used == 45000
    assert telemetry.cache_hits == 80
    assert telemetry.cost_saved_usd == 2.40
    assert telemetry.satisfaction_rate == 95
    assert telemetry.hallucination_index == 0.04


# ── 2. API Tests: Admin Live Telemetry Endpoint ───────────────────────────────

def test_admin_live_telemetry_endpoint():
    """Verify GET /v1/admin/tenants/{tenantId}/telemetry/live endpoint."""
    response = client.get(
        "/v1/admin/tenants/00000000-0000-0000-0000-000000000000/telemetry/live",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "00000000-0000-0000-0000-000000000000"
    assert "monthly_tokens_used" in data
    assert "documents_count" in data
    assert "cache_hits" in data
    assert "satisfaction_rate" in data
    assert "avg_faithfulness" in data
    assert "hallucination_index" in data
