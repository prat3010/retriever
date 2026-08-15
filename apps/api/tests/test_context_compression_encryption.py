"""Unit tests for Milestone 49: Context Compression & Zero-Trust Field Encryption."""

import uuid

import pytest
from fastapi.testclient import TestClient

from src.adapters.cognitive.context_compressor_adapter import (
    IntelligentContextCompressor,
)
from src.adapters.security.encryption_adapter import Aes256FieldEncryptor
from src.config import settings
from src.domain.security_compression.abstractions import (
    CompressionRequest,
    DecryptionRequest,
    EncryptionRequest,
)
from src.main import app

# ── 1. Context Compression Tests ──────────────────────────────────────────

def test_context_compressor_trims_fluff_and_preserves_facts():
    """Verify IntelligentContextCompressor removes filler and keeps factual numbers."""
    compressor = IntelligentContextCompressor()
    text = (
        "It is important to note that for the purpose of analyzing revenue, "
        "the Q3 net profit reached $4.2 million in 2026. "
        "Furthermore, as a matter of fact, customer retention was 94.5% across all regions. "
        "Basically, we are very happy with the results."
    )
    req = CompressionRequest(text=text, compression_rate=0.5)
    res = compressor.compress(req)

    assert res.compressed_tokens < res.original_tokens
    assert "$4.2 million" in res.compressed_text or "94.5%" in res.compressed_text
    assert "It is important to note that" not in res.compressed_text


# ── 2. AES-256 Field Encryption Tests ──────────────────────────────────────

def test_aes256_field_encryption_roundtrip():
    """Verify AES-256 field encryption and decryption roundtrip."""
    encryptor = Aes256FieldEncryptor(master_key="test_master_secret")
    tenant_id = str(uuid.uuid4())
    secret_text = "CONFIDENTIAL: Client SSN #123-45-6789 and Medical Record #9982"

    enc_req = EncryptionRequest(tenant_id=tenant_id, plaintext=secret_text)
    enc_res = encryptor.encrypt(enc_req)

    assert enc_res.ciphertext != secret_text
    assert "CONFIDENTIAL" not in enc_res.ciphertext

    dec_req = DecryptionRequest(tenant_id=tenant_id, ciphertext=enc_res.ciphertext)
    dec_res = encryptor.decrypt(dec_req)

    assert dec_res.plaintext == secret_text


def test_encryption_tenant_isolation():
    """Verify tenant A cannot decrypt tenant B's ciphertext."""
    encryptor = Aes256FieldEncryptor(master_key="test_master_secret")
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    secret_text = "Highly Confidential Data"

    enc_res = encryptor.encrypt(EncryptionRequest(tenant_id=tenant_a, plaintext=secret_text))

    dec_req_wrong_tenant = DecryptionRequest(tenant_id=tenant_b, ciphertext=enc_res.ciphertext)
    try:
        encryptor.decrypt(dec_req_wrong_tenant)
        pytest.fail("Should have failed decryption with wrong tenant key")
    except Exception:
        pass  # Expected Fernet InvalidToken exception


# ── 3. Router Endpoints Tests ──────────────────────────────────────────────

def test_security_compression_endpoints():
    """Verify API endpoints for context compression, encryption, and decryption."""
    client = TestClient(app)
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    # 1. Compress
    comp_resp = client.post(
        f"/v1/tenants/{tenant_id}/context/compress",
        headers=headers,
        json={
            "text": "Furthermore, it should be noted that profit was $1000 in 2026. Basically, it was great.",
            "compression_rate": 0.5,
        },
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["compressed_tokens"] <= comp_data["original_tokens"]

    # 2. Encrypt
    enc_resp = client.post(
        f"/v1/tenants/{tenant_id}/security/encrypt",
        headers=headers,
        json={"tenant_id": tenant_id, "plaintext": "Top Secret Data"},
    )
    assert enc_resp.status_code == 200
    ciphertext = enc_resp.json()["ciphertext"]

    # 3. Decrypt
    dec_resp = client.post(
        f"/v1/tenants/{tenant_id}/security/decrypt",
        headers=headers,
        json={"tenant_id": tenant_id, "ciphertext": ciphertext},
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["plaintext"] == "Top Secret Data"
