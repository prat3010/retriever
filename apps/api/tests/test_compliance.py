"""Unit tests for Milestone 51: Compliance & Data Sovereignty Lifecycle (GDPR/SOC2)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.compliance.pii_anonymizer import PiiAnonymizer
from src.domain.compliance.purge_service import HardPurgeService
from src.domain.compliance.retention_worker import RetentionWorker
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: PiiAnonymizer Token Redaction ───────────────────────────────

def test_pii_anonymizer_redacts_tokens():
    """Verify SSNs, credit cards, emails, phone numbers, and custom regex are masked."""
    anonymizer = PiiAnonymizer()
    raw_text = (
        "User SSN is 123-45-6789 and email is john@example.com. "
        "Call +1-555-123-4567. Card: 4111-1111-1111-1111. Secret Code: CONFIDENTIAL-99."
    )

    redacted = anonymizer.anonymize_text(
        raw_text,
        custom_patterns=[r"CONFIDENTIAL-\d+"],
    )

    assert "123-45-6789" not in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "john@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_CREDIT_CARD]" in redacted
    assert "[REDACTED_CUSTOM_1]" in redacted


# ── 2. Unit Test: HardPurgeService Document & Tenant Purge ───────────────────

@pytest.mark.asyncio
async def test_hard_purge_service():
    """Verify hard purge service calls cascade deletion logic."""
    mock_storage = AsyncMock()
    mock_storage.delete_file.return_value = True
    mock_graph = AsyncMock()
    mock_graph.delete_document_triples.return_value = 5
    mock_repo = AsyncMock()
    mock_repo.purge_document_db_records.return_value = (3, 10, 1, "test/path.pdf")

    service = HardPurgeService(
        compliance_repo=mock_repo,
        graph_repository=mock_graph,
        storage_provider=mock_storage,
    )

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    stats = await service.hard_purge_document(tenant_id, doc_id)

    assert stats["document_purged"] == 1
    assert stats["chunks_purged"] == 3
    assert stats["vectors_purged"] == 10
    assert stats["graph_triples_purged"] == 5
    mock_storage.delete_file.assert_awaited_once_with("test/path.pdf")


# ── 3. Unit Test: RetentionWorker Expired Document Purge ─────────────────────

@pytest.mark.asyncio
async def test_retention_worker_scans_expired():
    """Verify retention worker identifies expired documents and triggers purge."""
    mock_purge_service = AsyncMock()
    mock_purge_service.hard_purge_document.return_value = {"document_purged": 1}
    mock_repo = AsyncMock()
    mock_repo.get_expired_document_ids.return_value = [str(uuid.uuid4()), str(uuid.uuid4())]

    worker = RetentionWorker(purge_service=mock_purge_service, compliance_repo=mock_repo)
    tenant_id = str(uuid.uuid4())

    res = await worker.scan_and_purge_expired_documents(tenant_id, retention_days=30)

    assert res["scanned"] == 2
    assert res["purged"] == 2
    assert mock_purge_service.hard_purge_document.await_count == 2


# ── 4. Integration Test: Compliance Admin API Endpoints ─────────────────────

@patch("src.routers.admin.hard_purge_service.hard_purge_document", new_callable=AsyncMock)
@patch("src.routers.admin.hard_purge_service.hard_purge_tenant_data", new_callable=AsyncMock)
@patch("src.routers.admin.retention_worker.scan_and_purge_expired_documents", new_callable=AsyncMock)
def test_admin_compliance_endpoints(mock_retention, mock_forget, mock_purge_doc):
    """Verify admin endpoints for hard purge, tenant forget, anonymization, and retention purge."""
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())

        mock_purge_doc.return_value = {"chunks_purged": 3, "document_purged": 1}
        mock_forget.return_value = {"documents_purged": 10, "vectors_purged": 50}
        mock_retention.return_value = {"scanned": 5, "purged": 5}

        headers = {"X-Admin-Master-Key": "test_key"}

        # 1. Hard Purge Document Endpoint
        res_purge = client.delete(
            f"/v1/admin/tenants/{tenant_id}/compliance/documents/{doc_id}",
            headers=headers,
        )
        assert res_purge.status_code == 200
        assert res_purge.json()["status"] == "purged"

        # 2. Forget Tenant Endpoint
        res_forget = client.post(
            f"/v1/admin/tenants/{tenant_id}/compliance/forget",
            headers=headers,
        )
        assert res_forget.status_code == 200
        assert res_forget.json()["status"] == "tenant_purged"

        # 3. Anonymize Text Endpoint
        res_anon = client.post(
            f"/v1/admin/tenants/{tenant_id}/compliance/anonymize",
            headers=headers,
            json={"text": "Contact info@company.com or 123-45-6789."},
        )
        assert res_anon.status_code == 200
        redacted = res_anon.json()["redacted_text"]
        assert "[REDACTED_EMAIL]" in redacted
        assert "[REDACTED_SSN]" in redacted

        # 4. Retention Purge Endpoint
        res_ret = client.post(
            f"/v1/admin/tenants/{tenant_id}/compliance/run-retention-purge?retention_days=60",
            headers=headers,
        )
        assert res_ret.status_code == 200
        assert res_ret.json()["status"] == "completed"
    finally:
        app.dependency_overrides.clear()
