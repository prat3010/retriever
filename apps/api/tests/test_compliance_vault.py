"""Pytest suite for Milestone 88 (v0.73.0): Enterprise Compliance Vault.

Tests Presidio-grade PII entity recognition, Luhn checksum validation, synthetic masking,
cryptographic pseudonymization, HMAC-SHA256 GDPR erasure certificates, and public auditor verification.
"""

import ast
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.adapters.api.security import verify_admin_key
from src.domain.abstractions.compliance import (
    ErasureScope,
    MaskingMode,
    PiiCategory,
    PiiRedactionRequest,
)
from src.domain.compliance.certificate_service import ComplianceCertificateService
from src.domain.compliance.pii_anonymizer import PiiAnonymizer, luhn_checksum
from src.main import app

client = TestClient(app)


# ── 1. Luhn Checksum & Credit Card Entity Tests ──────────────────────────────

def test_luhn_checksum_validation():
    """Verify Luhn algorithm correctly distinguishes real card checksums from random numbers."""
    # Valid Visa test numbers
    assert luhn_checksum("4532015112830366") is True
    assert luhn_checksum("4532-0151-1283-0366") is True
    # Invalid checksum
    assert luhn_checksum("4532015112830367") is False
    assert luhn_checksum("1234567890123456") is False


def test_pii_anonymizer_credit_card_luhn():
    """Verify that only Luhn-valid cards are masked, avoiding false alarms on random 16-digit sequences."""
    anonymizer = PiiAnonymizer()
    text = (
        "Customer card is 4532-0151-1283-0366 (valid). "
        "Tracking number is 1234-5678-9012-3456 (invalid card)."
    )

    res = anonymizer.redact(PiiRedactionRequest(text=text, categories=[PiiCategory.FINANCIAL]))

    assert "4532-0151-1283-0366" not in res.redacted_text
    assert "[REDACTED_CREDIT_CARD]" in res.redacted_text
    # Invalid card number should remain intact
    assert "1234-5678-9012-3456" in res.redacted_text


# ── 2. Enterprise Secrets, Identifiers & Healthcare (HIPAA) ──────────────────

def test_pii_anonymizer_enterprise_entities():
    """Verify recognition of secrets (AWS, OpenAI, GitHub), HIPAA medical IDs, and network IPs."""
    anonymizer = PiiAnonymizer()
    text = (
        "Server config: AWS_KEY=AKIAIOSFODNN7EXAMPLE, OPENAI=sk-proj-123456789012345678901234567890. "
        "GitHub PAT: ghp_123456789012345678901234567890123456. "
        "Patient MRN: MRN-987654321. Server IP: 192.168.1.100. "
        "User SSN: 987-65-4321 and PAN: ABCDE1234F."
    )

    res = anonymizer.redact(PiiRedactionRequest(text=text))

    assert "AKIAIOSFODNN7EXAMPLE" not in res.redacted_text
    assert "sk-proj-123456789012345678901234567890" not in res.redacted_text
    assert "ghp_123456789012345678901234567890123456" not in res.redacted_text
    assert "MRN-987654321" not in res.redacted_text
    assert "192.168.1.100" not in res.redacted_text
    assert "987-65-4321" not in res.redacted_text
    assert "ABCDE1234F" not in res.redacted_text
    assert res.total_redacted >= 7


# ── 3. Masking Modes: Synthetic vs Cryptographic Pseudonymization ────────────

def test_pii_anonymizer_masking_modes():
    """Verify synthetic masking and deterministic cryptographic pseudonymization."""
    anonymizer = PiiAnonymizer()
    text = "Contact Alice at alice@example.com with SSN 123-45-6789."

    # Test Synthetic
    syn_res = anonymizer.redact(
        PiiRedactionRequest(text=text, masking_mode=MaskingMode.SYNTHETIC)
    )
    assert "***-**-6789" in syn_res.redacted_text
    assert "al***@example.com" in syn_res.redacted_text

    # Test Pseudonymize
    pseudo_res1 = anonymizer.redact(
        PiiRedactionRequest(text=text, masking_mode=MaskingMode.PSEUDONYMIZE)
    )
    pseudo_res2 = anonymizer.redact(
        PiiRedactionRequest(text=text, masking_mode=MaskingMode.PSEUDONYMIZE)
    )

    # Determinism: the same raw token generates the exact same pseudonym hash
    assert "[PSEUDONYM:" in pseudo_res1.redacted_text
    assert pseudo_res1.redacted_text == pseudo_res2.redacted_text


# ── 4. Cryptographic GDPR Erasure Certificate Issuance & Verification ─────────

def test_cryptographic_compliance_certificate():
    """Verify HMAC-SHA256 signature issuance, valid verification, and tamper detection."""
    service = ComplianceCertificateService(signing_key="enterprise-secret-key-12345")
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    records = {"documents_purged": 1, "chunks_purged": 15, "vectors_purged": 45}

    cert = service.issue_certificate(
        tenant_id=tenant_id,
        requester="dpo@enterprise-client.com",
        reason="GDPR Article 17 Right to Erasure",
        erasure_scope=ErasureScope.DOCUMENT,
        records_purged=records,
        target_id=doc_id,
    )

    assert cert.certificate_id.startswith("cert_gdpr_")
    assert len(cert.sha256_audit_signature) == 64
    assert cert.verification_status == "VALID"

    # 1. Verify authentic certificate
    assert service.verify_certificate(cert) is True

    # 2. Tamper with certificate records count
    tampered_cert = cert.model_copy(deep=True)
    tampered_cert.records_purged["vectors_purged"] = 999
    assert service.verify_certificate(tampered_cert) is False

    # 3. Tamper with tenant ID
    tampered_tenant_cert = cert.model_copy(deep=True)
    tampered_tenant_cert.tenant_id = str(uuid.uuid4())
    assert service.verify_certificate(tampered_tenant_cert) is False


# ── 5. Admin API Endpoints for Compliance Vault ─────────────────────────────

@patch("src.routers.admin.hard_purge_service.purge_document_with_certificate", new_callable=AsyncMock)
@patch("src.routers.admin.hard_purge_service.purge_tenant_with_certificate", new_callable=AsyncMock)
def test_admin_compliance_vault_endpoints(mock_purge_tenant, mock_purge_doc):
    """Verify admin endpoints return signed compliance certificates upon hard-purges."""
    app.dependency_overrides[verify_admin_key] = lambda: True

    service = ComplianceCertificateService(signing_key="test-key")
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_cert = service.issue_certificate(
        tenant_id=tenant_id,
        requester="admin_system",
        reason="Admin Hard Purge Document",
        erasure_scope=ErasureScope.DOCUMENT,
        records_purged={"chunks_purged": 5, "vectors_purged": 5},
        target_id=doc_id,
    )
    mock_purge_doc.return_value = mock_cert
    mock_purge_tenant.return_value = mock_cert

    # 1. Document purge with certificate
    res = client.delete(
        f"/v1/admin/tenants/{tenant_id}/compliance/documents/{doc_id}",
        headers={"X-Admin-Key": "test"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "purged"
    assert "certificate" in data
    assert data["certificate"]["certificate_id"].startswith("cert_gdpr_")

    # 2. Anonymize endpoint with full entity detection
    anon_res = client.post(
        f"/v1/admin/tenants/{tenant_id}/compliance/anonymize",
        json={"text": "Contact john@example.com with SSN 123-45-6789.", "masking_mode": "redact"},
        headers={"X-Admin-Key": "test"},
    )
    assert anon_res.status_code == 200
    anon_data = anon_res.json()
    assert anon_data["total_redacted"] >= 2
    assert len(anon_data["entities_detected"]) >= 2

    app.dependency_overrides.pop(verify_admin_key, None)


# ── 6. Hexagonal Architecture Boundaries ────────────────────────────────────

def test_hexagonal_architecture_compliance():
    """Ensure compliance domain layer imports zero infrastructure or web frameworks."""
    forbidden = ["fastapi", "sqlalchemy", "requests", "httpx", "aiohttp", "boto3"]
    domain_files = [
        Path(f"src/domain/{rel}")
        if Path(f"src/domain/{rel}").exists()
        else Path(f"apps/api/src/domain/{rel}")
        for rel in [
            "abstractions/compliance.py",
            "compliance/pii_anonymizer.py",
            "compliance/certificate_service.py",
            "compliance/purge_service.py",
        ]
    ]

    for p in domain_files:
        assert p.exists(), f"File {p} must exist"
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    for f in forbidden:
                        assert not name.name.startswith(f), f"Illegal import '{name.name}' in {p}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                for f in forbidden:
                    assert not node.module.startswith(f), f"Illegal import from '{node.module}' in {p}"
