"""Unit tests for Milestone 53: Enterprise n8n & Workflow Automation Integration."""

import base64
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.workflow.n8n_dispatcher import N8nWebhookDispatcher
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: N8nWebhookDispatcher Event Dispatch ────────────────────────

@pytest.mark.asyncio
async def test_n8n_webhook_dispatcher_success():
    """Verify N8nWebhookDispatcher posts events to external webhook URLs."""
    dispatcher = N8nWebhookDispatcher()
    tenant_id = str(uuid.uuid4())

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        res = await dispatcher.dispatch_event(
            webhook_url="https://n8n.example.com/webhook/123",
            event_type="chat.feedback.negative",
            tenant_id=tenant_id,
            payload={"reason": "incorrect answer"},
        )

        assert res["success"] is True
        assert res["status_code"] == 200
        mock_post.assert_awaited_once()


# ── 2. Integration Test: Inbound n8n Auto-Ingest Webhook (Text) ───────────────

@patch("src.routers.workflow.document_repository.create_document", new_callable=AsyncMock)
def test_inbound_n8n_text_ingest(mock_create_doc):
    """Verify inbound text ingestion from n8n passes through PII anonymization and saves chunks."""
    tenant_id = str(uuid.uuid4())

    res = client.post(
        f"/v1/tenants/{tenant_id}/ingest/webhook",
        json={
            "title": "n8n Email Summary",
            "content": "User SSN is 123-45-6789 and email is info@test.com.",
            "source": "gmail_n8n",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ingested"
    assert body["tenant_id"] == tenant_id
    assert body["source"] == "gmail_n8n"
    assert body["chunks"] > 0
    mock_create_doc.assert_awaited_once()


# ── 3. Integration Test: Inbound n8n Base64 File Ingest Webhook ───────────────

@patch("src.routers.workflow.ingest_file_sync", new_callable=AsyncMock)
def test_inbound_n8n_base64_file_ingest(mock_ingest_sync):
    """Verify inbound base64 binary file ingestion from n8n/Google Drive."""
    tenant_id = str(uuid.uuid4())
    dummy_pdf_base64 = base64.b64encode(b"%PDF-1.4 Dummy File Content").decode("utf-8")
    mock_ingest_sync.return_value = 5

    res = client.post(
        f"/v1/tenants/{tenant_id}/ingest/webhook",
        json={
            "title": "Q3 Report.pdf",
            "file_base64": dummy_pdf_base64,
            "filename": "Q3_Report.pdf",
            "source": "gdrive_n8n",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ingested"
    assert body["chunks"] == 5
    mock_ingest_sync.assert_awaited_once()


# ── 4. Integration Test: n8n Webhook Config & OpenAPI Spec Endpoints ─────────

@patch("src.routers.workflow.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.routers.workflow.config_service.update_tenant_config", new_callable=AsyncMock)
@patch("src.routers.workflow.n8n_dispatcher.dispatch_event", new_callable=AsyncMock)
def test_workflow_admin_and_spec_endpoints(mock_dispatch, mock_save_cfg, mock_get_cfg):
    """Verify admin config of n8n webhook URL and retrieval of n8n OpenAPI spec."""
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())
        mock_cfg = AsyncMock()
        mock_cfg.metadata = {}
        mock_get_cfg.return_value = mock_cfg
        mock_dispatch.return_value = {"success": True}

        # 1. Admin Webhook Config Endpoint
        res_cfg = client.post(
            f"/v1/admin/tenants/{tenant_id}/workflow/webhooks",
            headers={"X-Admin-Master-Key": "test_key"},
            json={"n8n_webhook_url": "https://n8n.example.com/webhook/target"},
        )
        assert res_cfg.status_code == 200
        assert res_cfg.json()["status"] == "configured"
        mock_save_cfg.assert_awaited_once()

        # 2. n8n OpenAPI Spec Endpoint
        res_spec = client.get("/v1/workflow/n8n-spec")
        assert res_spec.status_code == 200
        body_spec = res_spec.json()
        assert body_spec["openapi"] == "3.0.3"
        assert "/v1/tenants/{tenantId}/ingest/webhook" in body_spec["paths"]
    finally:
        app.dependency_overrides.clear()
