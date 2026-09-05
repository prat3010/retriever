"""Comprehensive Unit & REST Integration Test Suite for Milestone 101.

Validates:
- Hexagonal boundary purity of domain abstractions
- Cryptographic nonce challenge lifecycle & anti-replay gates
- Hardware remote attestation generation and signature verification
- Forged signature and tampered PCR evidence rejection
- Authenticated AES-256-GCM memory sealing and unsealing roundtrip
- Strict tenant isolation and AAD binding enforcement
- EphemeralMemorySanitizer zeroing and memory scrubbing
- Platform Battery #21 registration in BatteryService
- FastAPI admin & tenant REST endpoints
"""

import ast
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.security.enclave_adapter import HardwareEnclaveAdapter
from src.adapters.security.memory_sanitizer import EphemeralMemorySanitizer
from src.config import settings
from src.container import battery_service, container
from src.domain.abstractions.enclave import (
    AttestationTrustLevel,
    CipherSuite,
)
from src.main import app


def test_enclave_domain_abstractions_purity():
    """Verify that domain abstractions import zero forbidden frameworks."""
    domain_file = Path(__file__).resolve().parents[1] / "src" / "domain" / "abstractions" / "enclave.py"
    assert domain_file.exists()

    tree = ast.parse(domain_file.read_text(), filename=str(domain_file))
    forbidden = {"fastapi", "sqlalchemy", "cryptography", "redis", "pika", "celery", "adapters"}

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    violating = forbidden & imported_modules
    assert not violating, f"Domain abstraction contains forbidden imports: {violating}"


def test_attestation_nonce_lifecycle():
    """Test nonce generation, expiry detection, and replay prevention."""
    sanitizer = EphemeralMemorySanitizer(register_signals=False)
    adapter = HardwareEnclaveAdapter(memory_sanitizer=sanitizer)

    # 1. Fresh nonce
    nonce_obj = adapter.generate_nonce(ttl_seconds=300)
    assert len(nonce_obj.nonce) == 64
    assert not nonce_obj.consumed

    evidence = adapter.generate_evidence(nonce_obj.nonce)
    report1 = adapter.verify_evidence(evidence, expected_nonce=nonce_obj.nonce)
    assert report1.is_valid is True

    # 2. Replay attack: reusing the same nonce must be rejected
    report_replay = adapter.verify_evidence(evidence, expected_nonce=nonce_obj.nonce)
    assert report_replay.is_valid is False
    assert "replay" in report_replay.details.get("error", "").lower()

    # 3. Expired nonce
    expired_nonce = adapter.generate_nonce(ttl_seconds=1)
    expired_nonce.expires_at = datetime.now(UTC) - timedelta(seconds=10)
    adapter._nonces[expired_nonce.nonce] = expired_nonce

    evidence_exp = adapter.generate_evidence(expired_nonce.nonce)
    report_exp = adapter.verify_evidence(evidence_exp, expected_nonce=expired_nonce.nonce)
    assert report_exp.is_valid is False
    assert "expired" in report_exp.details.get("error", "").lower()


def test_hardware_attestation_verification_and_rejection():
    """Test remote attestation verification and rejection of forged signatures/measurements."""
    sanitizer = EphemeralMemorySanitizer(register_signals=False)
    adapter = HardwareEnclaveAdapter(memory_sanitizer=sanitizer)

    nonce_obj = adapter.generate_nonce(ttl_seconds=300)
    evidence = adapter.generate_evidence(nonce_obj.nonce)

    # Valid verification
    report = adapter.verify_evidence(evidence, expected_nonce=nonce_obj.nonce)
    assert report.is_valid is True
    assert report.trust_level in {AttestationTrustLevel.HARDWARE_ROOTED, AttestationTrustLevel.SIMULATED}
    assert report.pcr_measurement == adapter.pcr0_measurement

    # Forged signature rejection
    nonce_obj2 = adapter.generate_nonce(ttl_seconds=300)
    bad_evidence = adapter.generate_evidence(nonce_obj2.nonce)
    # Tamper with signature bytes
    sig_raw = bytearray(base64.b64decode(bad_evidence.signature))
    sig_raw[0] ^= 0xFF
    bad_evidence.signature = base64.b64encode(sig_raw).decode("utf-8")

    report_bad = adapter.verify_evidence(bad_evidence, expected_nonce=nonce_obj2.nonce)
    assert report_bad.is_valid is False
    assert report_bad.trust_level == AttestationTrustLevel.UNTRUSTED

    # Tampered PCR measurement rejection
    nonce_obj3 = adapter.generate_nonce(ttl_seconds=300)
    tampered_pcr_ev = adapter.generate_evidence(nonce_obj3.nonce)
    tampered_pcr_ev.pcr_measurement = "0" * 64
    report_tampered = adapter.verify_evidence(tampered_pcr_ev, expected_nonce=nonce_obj3.nonce)
    assert report_tampered.is_valid is False


def test_tenant_sealing_unsealing_roundtrip():
    """Test AES-256-GCM memory sealing and unsealing for a tenant."""
    sanitizer = EphemeralMemorySanitizer(register_signals=False)
    adapter = HardwareEnclaveAdapter(memory_sanitizer=sanitizer)

    tenant_id = "tn_confidential_alpha"
    secret_text = "Highly confidential trade secret vector embedding BLOB #4096"
    custom_aad = "doc_id:doc_999:version:2"

    sealed = adapter.seal(tenant_id=tenant_id, plaintext=secret_text, aad=custom_aad)
    assert sealed.tenant_id == tenant_id
    assert sealed.cipher_suite == CipherSuite.AES_256_GCM
    assert sealed.pcr_binding == adapter.pcr0_measurement
    assert sealed.aad == custom_aad
    assert len(base64.b64decode(sealed.nonce_iv)) == 12  # 96-bit GCM IV
    assert len(base64.b64decode(sealed.auth_tag)) == 16  # 128-bit tag

    # Unseal
    unsealed_bytes = adapter.unseal(sealed)
    assert unsealed_bytes.decode("utf-8") == secret_text


def test_tenant_isolation_and_aad_tampering():
    """Verify that a sealed payload cannot be unsealed by another tenant or with tampered AAD."""
    sanitizer = EphemeralMemorySanitizer(register_signals=False)
    adapter = HardwareEnclaveAdapter(memory_sanitizer=sanitizer)

    tenant_alpha = "tn_alpha_111"
    tenant_beta = "tn_beta_222"

    sealed_alpha = adapter.seal(tenant_id=tenant_alpha, plaintext="Alpha confidential data")

    # Attempt cross-tenant unseal: tenant_beta attempts to unseal alpha's ciphertext
    fraudulent_payload = sealed_alpha.model_copy(update={"tenant_id": tenant_beta})
    with pytest.raises(ValueError, match="authentication tag verification failed"):
        adapter.unseal(fraudulent_payload)

    # Attempt AAD tampering
    tampered_aad_payload = sealed_alpha.model_copy(update={"aad": "tampered_context"})
    with pytest.raises(ValueError, match="authentication tag verification failed"):
        adapter.unseal(tampered_aad_payload)

    # Attempt Ciphertext tampering
    ct_raw = bytearray(base64.b64decode(sealed_alpha.ciphertext))
    ct_raw[0] ^= 0x01
    tampered_ct_payload = sealed_alpha.model_copy(update={"ciphertext": base64.b64encode(ct_raw).decode()})
    with pytest.raises(ValueError, match="authentication tag verification failed"):
        adapter.unseal(tampered_ct_payload)


def test_memory_sanitizer_zeroing():
    """Verify in-place memory wiping of volatile keys."""
    sanitizer = EphemeralMemorySanitizer(register_signals=False)

    key_id = "test_key_001"
    raw_key = b"super_secret_master_key_bytes_32"

    sanitizer.allocate_ephemeral_key(key_id, raw_key)
    assert sanitizer.get_ephemeral_key(key_id) == raw_key
    assert sanitizer.active_key_count == 1

    # In-place wipe
    wiped = sanitizer.wipe_key(key_id)
    assert wiped is True
    assert sanitizer.get_ephemeral_key(key_id) is None
    assert sanitizer.active_key_count == 0

    # Scoped context manager
    with sanitizer.scoped_key("scoped_key_1", b"volatile_data") as k:
        assert k == b"volatile_data"
        assert sanitizer.active_key_count == 1
    assert sanitizer.active_key_count == 0

    # Wipe all
    sanitizer.allocate_ephemeral_key("k1", b"1111")
    sanitizer.allocate_ephemeral_key("k2", b"2222")
    sanitizer.allocate_ephemeral_key("k3", b"3333")
    assert sanitizer.active_key_count == 3
    count = sanitizer.wipe_all()
    assert count == 3
    assert sanitizer.active_key_count == 0


def test_platform_battery_21_registration():
    """Verify that Battery #21 (zero_trust_micro_enclave) is registered in BatteryService."""
    resp = battery_service.get_platform_batteries()
    battery = battery_service.get_battery("zero_trust_micro_enclave")

    assert battery is not None
    assert battery.id == "zero_trust_micro_enclave"
    assert battery.milestone == "M101 (v0.86.0)"
    assert battery.category.value == "safety_defense"
    assert battery.status.value == "active"
    assert "AES-256-GCM" in battery.active_parameters.get("cipher_suite", "")
    assert resp.total_batteries >= 21


@pytest.mark.asyncio
async def test_fastapi_enclave_endpoints():
    """Verify all admin and tenant FastAPI endpoints for enclave attestation and sealing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

        # 1. GET /v1/admin/edge/attestation/nonce
        nonce_res = await client.get("/v1/admin/edge/attestation/nonce", headers=admin_headers)
        assert nonce_res.status_code == 200
        nonce_data = nonce_res.json()
        assert "nonce" in nonce_data
        challenge_nonce = nonce_data["nonce"]

        # 2. POST /v1/admin/edge/attestation/verify
        enclave = container.enclave_adapter
        evidence = enclave.generate_evidence(nonce=challenge_nonce)
        verify_res = await client.post(
            "/v1/admin/edge/attestation/verify",
            json=evidence.model_dump(),
            headers=admin_headers,
        )
        assert verify_res.status_code == 200
        assert verify_res.json()["is_valid"] is True

        # 3. GET /v1/admin/edge/attestation/report
        report_res = await client.get("/v1/admin/edge/attestation/report", headers=admin_headers)
        assert report_res.status_code == 200
        report_data = report_res.json()
        assert report_data["is_valid"] is True
        assert report_data["trust_level"] in ["hardware_rooted", "simulated"]

        # 3. POST /v1/admin/edge/enclave/purge-keys
        purge_res = await client.post("/v1/admin/edge/enclave/purge-keys", headers=admin_headers)
        assert purge_res.status_code == 200
        assert purge_res.json()["status"] == "success"

        # 4. POST /v1/tenants/{tenantId}/edge/seal
        tenant_id = "00000000-0000-0000-0000-000000000001"
        tenant_headers = {
            "X-Admin-Master-Key": settings.ADMIN_MASTER_KEY,
        }
        seal_payload = {
            "tenant_id": tenant_id,
            "plaintext": "Confidential tenant vector record #9012",
            "aad": "dataset_id:enterprise_db",
        }
        seal_res = await client.post(
            f"/v1/tenants/{tenant_id}/edge/seal",
            json=seal_payload,
            headers=tenant_headers,
        )
        assert seal_res.status_code == 200
        sealed_body = seal_res.json()
        assert sealed_body["tenant_id"] == tenant_id
        assert sealed_body["cipher_suite"] == "aes_256_gcm"
        assert "ciphertext" in sealed_body
        assert "auth_tag" in sealed_body

        # 5. POST /v1/tenants/{tenantId}/edge/unseal
        unseal_payload = {
            "tenant_id": tenant_id,
            "sealed_payload": sealed_body,
        }
        unseal_res = await client.post(
            f"/v1/tenants/{tenant_id}/edge/unseal",
            json=unseal_payload,
            headers=tenant_headers,
        )
        assert unseal_res.status_code == 200
        unseal_body = unseal_res.json()
        assert unseal_body["plaintext"] == "Confidential tenant vector record #9012"
        assert unseal_body["verified_aad"] is True
