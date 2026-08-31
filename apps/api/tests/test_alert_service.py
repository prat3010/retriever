"""Unit and API tests for Milestone 76: SLA Multi-Channel Webhook Alerting Service."""

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.domain.abstractions.telemetry import (
    AlertPayload,
    TenantAlertConfig,
    TenantLiveTelemetry,
)
from src.domain.telemetry.alert_service import AlertService
from src.main import app

client = TestClient(app)


# ── 1. Unit Tests: Payload Formatters ────────────────────────────────────────

def test_alert_format_slack_payload():
    """Verify Slack Block Kit format includes severity emoji and mrkdwn blocks."""
    alert_svc = AlertService()
    alert = AlertPayload(
        alert_id="alt_123",
        tenant_id="tn_test",
        rule_name="hallucination_spike",
        severity="CRITICAL",
        title="Hallucination Spike Detected",
        description="Index exceeded 30%",
        metrics={"hallucination_index": 0.35},
        timestamp="2026-08-31T09:00:00Z",
    )

    slack_data = alert_svc.format_slack_payload(alert)
    assert "blocks" in slack_data
    assert len(slack_data["blocks"]) == 3
    assert slack_data["blocks"][0]["type"] == "header"
    assert "CRITICAL" in slack_data["blocks"][0]["text"]["text"]
    assert "tn_test" in slack_data["blocks"][1]["text"]["text"]


def test_alert_format_discord_payload():
    """Verify Discord Embed format contains proper color codes and fields."""
    alert_svc = AlertService()
    alert = AlertPayload(
        alert_id="alt_456",
        tenant_id="tn_test",
        rule_name="token_quota_threshold",
        severity="WARNING",
        title="Quota 90% Reached",
        description="Token capacity near limit",
        metrics={"usage_percentage": 92.5},
        timestamp="2026-08-31T09:00:00Z",
    )

    discord_data = alert_svc.format_discord_payload(alert)
    assert "embeds" in discord_data
    embed = discord_data["embeds"][0]
    assert embed["title"] == "🚨 [WARNING] Quota 90% Reached"
    assert embed["color"] == 16753920
    assert any(f["name"] == "Tenant ID" for f in embed["fields"])


def test_alert_format_custom_webhook():
    """Verify standard normalized JSON webhook structure."""
    alert_svc = AlertService()
    alert = AlertPayload(
        alert_id="alt_789",
        tenant_id="tn_test",
        rule_name="latency_spike",
        severity="WARNING",
        title="P99 Latency Breach",
        description="P99 latency > 5000ms",
        metrics={"p99_latency_ms": 6200.0},
        timestamp="2026-08-31T09:00:00Z",
    )

    payload = alert_svc.format_custom_webhook_payload(alert)
    assert payload["event_type"] == "sla_incident_alert"
    assert payload["rule_name"] == "latency_spike"
    assert payload["metrics"]["p99_latency_ms"] == 6200.0


# ── 2. Unit Tests: SLA Rule Triggers & Debounce ───────────────────────────────

def test_alert_evaluation_hallucination_trigger():
    """Verify hallucination spike rule fires when index > 30%."""
    alert_svc = AlertService()
    telemetry = TenantLiveTelemetry(
        tenant_id="tn_test",
        hallucination_index=0.34,
        avg_faithfulness=0.66,
    )

    alerts = alert_svc.evaluate_rules("tn_test", telemetry, token_quota_max=100_000)
    assert len(alerts) == 1
    assert alerts[0].rule_name == "hallucination_spike"
    assert alerts[0].severity == "CRITICAL"


def test_alert_evaluation_quota_trigger():
    """Verify quota rule fires at 90% (WARNING) and 100% (CRITICAL)."""
    alert_svc = AlertService()

    # 90% Warning
    telemetry_warn = TenantLiveTelemetry(
        tenant_id="tn_test",
        monthly_tokens_used=92_000,
        hallucination_index=0.05,
    )
    alerts_warn = alert_svc.evaluate_rules("tn_test", telemetry_warn, token_quota_max=100_000)
    assert len(alerts_warn) == 1
    assert alerts_warn[0].rule_name == "token_quota_threshold"
    assert alerts_warn[0].severity == "WARNING"

    # 100% Critical
    telemetry_crit = TenantLiveTelemetry(
        tenant_id="tn_test",
        monthly_tokens_used=105_000,
        hallucination_index=0.05,
    )
    alerts_crit = alert_svc.evaluate_rules("tn_test", telemetry_crit, token_quota_max=100_000)
    assert len(alerts_crit) == 1
    assert alerts_crit[0].rule_name == "token_quota_threshold"
    assert alerts_crit[0].severity == "CRITICAL"


def test_alert_evaluation_latency_trigger():
    """Verify latency rule fires when P99 > 5000ms."""
    alert_svc = AlertService()
    telemetry = TenantLiveTelemetry(
        tenant_id="tn_test",
        p99_latency_ms=5400.0,
        hallucination_index=0.02,
    )

    alerts = alert_svc.evaluate_rules("tn_test", telemetry, token_quota_max=100_000)
    assert len(alerts) == 1
    assert alerts[0].rule_name == "latency_spike"
    assert alerts[0].severity == "WARNING"


@pytest.mark.asyncio
async def test_alert_debouncing():
    """Verify rapid repetitive triggers are suppressed within debounce window."""
    alert_svc = AlertService()
    telemetry = TenantLiveTelemetry(
        tenant_id="tn_debounced",
        hallucination_index=0.40,
    )
    config = TenantAlertConfig(tenant_id="tn_debounced", min_interval_minutes=10)

    # First trigger -> dispatched
    alerts_first = await alert_svc.evaluate_and_dispatch(
        "tn_debounced", telemetry, token_quota_max=100_000, config=config
    )
    assert len(alerts_first) == 1

    # Immediate second trigger -> suppressed by debounce
    alerts_second = await alert_svc.evaluate_and_dispatch(
        "tn_debounced", telemetry, token_quota_max=100_000, config=config
    )
    assert len(alerts_second) == 0


# ── 3. API Tests: Admin Alert Endpoints ───────────────────────────────────────

def test_admin_test_alert_endpoint():
    """Verify POST /v1/admin/tenants/{tenantId}/alerts/test endpoint."""
    response = client.post(
        "/v1/admin/tenants/00000000-0000-0000-0000-000000000000/alerts/test",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={
            "channel": "slack",
            "webhook_url": "https://hooks.slack.com/services/T000/B000/XXXX",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["dispatched", "failed"]
    assert data["channel"] == "slack"
    assert "formatted_payload" in data
    assert "blocks" in data["formatted_payload"]


def test_admin_alert_history_endpoint():
    """Verify GET /v1/admin/tenants/{tenantId}/alerts/history endpoint."""
    response = client.get(
        "/v1/admin/tenants/00000000-0000-0000-0000-000000000000/alerts/history",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
