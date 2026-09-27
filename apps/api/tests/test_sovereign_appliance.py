"""Comprehensive Unit & REST Integration Test Suite for Sovereign Air-Gapped Appliance (M127).

Verifies:
- Hexagonal boundary purity of domain abstractions (zero forbidden imports)
- AES-256-GCM hardware-rooted vector database sealing & tamper-detection gates
- Air-gap network isolation sentinel & fail-closed egress enforcement
- Offline full-duplex neural voice RAG engine (Whisper ASR + Search + Piper TTS)
- SovereignApplianceManager lifecycle, hardware attestation, and manifest
- Platform Battery #41 registration in BatteryService (41 total platform batteries)
- FastAPI REST endpoints (/v1/appliance/status, /audit, /manifest, /seal, /unseal, /voice/query)
"""

import ast
import base64
import os
import sqlite3
import struct
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.appliance.hardware_vector_sealer import HardwareVectorSealer
from src.adapters.security.memory_sanitizer import EphemeralMemorySanitizer
from src.adapters.voice.speech_synthesis_adapter import SpeechSynthesisAdapter
from src.adapters.voice.whisper_transcription_adapter import WhisperTranscriptionAdapter
from src.config import settings
from src.container import battery_service
from src.domain.abstractions.appliance import (
    AirgapEgressViolationError,
    ApplianceDeploymentMode,
    ApplianceSealingState,
    HardwareRootType,
    HardwareSealingTamperError,
    VoiceRAGQueryRequest,
)
from src.domain.abstractions.batteries import BatteryCategory, BatteryStatus
from src.domain.appliance.airgap_sentinel import AirgapNetworkSentinel
from src.domain.appliance.appliance_manager import SovereignApplianceManager
from src.domain.appliance.voice_rag_engine import SovereignVoiceRAGEngine
from src.main import app

client = TestClient(app)

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_KEY = settings.ADMIN_MASTER_KEY


# ── Test 1: Hexagonal Purity of Domain Abstractions ──────────────────────────


def test_appliance_domain_abstractions_purity():
    """Verify that domain abstractions import zero forbidden infrastructure frameworks."""
    domain_file = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "domain"
        / "abstractions"
        / "appliance.py"
    )
    assert domain_file.exists(), f"Domain abstraction file not found: {domain_file}"

    tree = ast.parse(domain_file.read_text(), filename=str(domain_file))
    forbidden = {
        "fastapi",
        "sqlalchemy",
        "cryptography",
        "redis",
        "pika",
        "celery",
        "adapters",
    }

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    violating = forbidden & imported_modules
    assert not violating, f"Domain abstraction contains forbidden imports: {violating}"


# ── Test 2: Hardware Vector Index Sealing & Tamper Detection ─────────────────


def test_hardware_vector_sealer_roundtrip_and_tamper_detection():
    """Verify AES-256-GCM sealing, unsealing, PCR measurement binding, and tamper-proofing."""
    sanitizer = EphemeralMemorySanitizer(register_signals=False)
    sealer = HardwareVectorSealer(memory_sanitizer=sanitizer)
    pcr = sealer.get_hardware_pcr_measurement()

    with tempfile.TemporaryDirectory() as tmpdir:
        plain_path = os.path.join(tmpdir, "test_vector.db")
        sealed_path = os.path.join(tmpdir, "test_vector.db.sealed")
        restored_path = os.path.join(tmpdir, "restored_vector.db")

        # Create a sample SQLite database
        conn = sqlite3.connect(plain_path)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE vectors (id TEXT PRIMARY KEY, content TEXT, embedding BLOB);"
        )
        cur.execute(
            "INSERT INTO vectors VALUES ('chk_1', 'Tactical sovereign mission data', X'01020304');"
        )
        conn.commit()
        conn.close()

        orig_bytes = Path(plain_path).read_bytes()

        # 1. Seal database
        meta = sealer.seal_database(
            tenant_id=TEST_TENANT_ID,
            plain_db_path=plain_path,
            sealed_db_path=sealed_path,
            pcr_measurement=pcr,
            chunk_count=1,
            vector_dim=4,
        )
        assert meta.sealing_state == ApplianceSealingState.SEALED
        assert meta.cipher_suite == "aes_256_gcm"
        assert meta.chunk_count == 1
        assert len(meta.sealed_checksum_sha256) == 64
        assert os.path.exists(sealed_path)

        # 2. Unseal database with correct PCR
        unsealed_ok = sealer.unseal_database(
            tenant_id=TEST_TENANT_ID,
            sealed_db_path=sealed_path,
            unsealed_db_path=restored_path,
            pcr_measurement=pcr,
        )
        assert unsealed_ok is True
        restored_bytes = Path(restored_path).read_bytes()
        assert restored_bytes == orig_bytes

        # Verify restored DB can be queried
        conn2 = sqlite3.connect(restored_path)
        cur2 = conn2.cursor()
        cur2.execute("SELECT content FROM vectors WHERE id='chk_1';")
        row = cur2.fetchone()
        assert row[0] == "Tactical sovereign mission data"
        conn2.close()

        # 3. Tamper detection: Mismatched PCR measurement
        with pytest.raises(
            HardwareSealingTamperError, match="Hardware PCR measurement mismatch"
        ):
            sealer.unseal_database(
                tenant_id=TEST_TENANT_ID,
                sealed_db_path=sealed_path,
                unsealed_db_path=os.path.join(tmpdir, "tampered_pcr.db"),
                pcr_measurement="pcr_attacker_compromised_digest_9999",
            )

        # 4. Tamper detection: Mismatched tenant ID
        with pytest.raises(HardwareSealingTamperError, match="Tenant ID mismatch"):
            sealer.unseal_database(
                tenant_id="00000000-0000-0000-0000-999999999999",
                sealed_db_path=sealed_path,
                unsealed_db_path=os.path.join(tmpdir, "tampered_tenant.db"),
                pcr_measurement=pcr,
            )

        # 5. Tamper detection: Corrupted ciphertext
        corrupted_bytes = bytearray(Path(sealed_path).read_bytes())
        corrupted_bytes[-5] ^= 0xFF  # Flip a bit in the encrypted payload
        corrupted_path = os.path.join(tmpdir, "corrupted.db.sealed")
        Path(corrupted_path).write_bytes(corrupted_bytes)

        with pytest.raises(
            HardwareSealingTamperError, match="authentication tag mismatch"
        ):
            sealer.unseal_database(
                tenant_id=TEST_TENANT_ID,
                sealed_db_path=corrupted_path,
                unsealed_db_path=os.path.join(tmpdir, "failed_corrupt.db"),
                pcr_measurement=pcr,
            )


# ── Test 3: Air-Gap Network Isolation Sentinel ───────────────────────────────


def test_airgap_network_sentinel():
    """Verify in-process network isolation auditing and fail-closed egress blocking."""
    sentinel = AirgapNetworkSentinel(
        deployment_mode=ApplianceDeploymentMode.AIR_GAPPED_STRICT,
        allowed_hosts={"127.0.0.1", "localhost"},
    )

    # 1. Audit isolation without WAN proxy
    audit = sentinel.audit_isolation(strict_enforce=False)
    assert audit.audited_at is not None
    assert audit.active_sockets_count >= 0

    # 2. Permitted loopback target
    sentinel.verify_outbound_target("127.0.0.1", 8000)
    sentinel.verify_outbound_target("localhost", 11434)

    # 3. Blocked external WAN target in strict mode
    with pytest.raises(AirgapEgressViolationError, match="Air-gap egress blocked"):
        sentinel.verify_outbound_target("api.external-cloud.com", 443)

    with pytest.raises(AirgapEgressViolationError, match="Air-gap egress blocked"):
        sentinel.verify_outbound_target("8.8.8.8", 53)

    assert sentinel.blocked_attempts == 2


# ── Test 4: Offline Full-Duplex Neural Voice RAG Engine ───────────────────────


@pytest.mark.asyncio
async def test_offline_voice_rag_engine():
    """Verify end-to-end full-duplex voice RAG: Audio in -> ASR -> Hybrid Search -> SLM -> TTS -> Audio out."""
    transcription = WhisperTranscriptionAdapter()
    synthesis = SpeechSynthesisAdapter(default_sample_rate_hz=16000)

    # Synthetic hybrid search returning test chunk
    async def mock_search(tenant_id: str, query: str, top_k: int = 5):
        return [
            {
                "chunk_id": "chk_radar_01",
                "document_id": "doc_tactical_sop",
                "content": "Sovereign tactical perimeter radars must operate on localized frequency 1420MHz.",
                "score": 0.94,
            }
        ]

    engine = SovereignVoiceRAGEngine(
        transcription_service=transcription,
        synthesis_service=synthesis,
        hybrid_search_fn=mock_search,
    )

    # Synthetic 20ms speech audio frame (320 16-bit PCM samples)
    samples = [int(12000 * (i % 2 * 2 - 1)) for i in range(320)]
    audio_frame = struct.pack("<320h", *samples)
    b64_audio = base64.b64encode(audio_frame).decode("ascii")

    req = VoiceRAGQueryRequest(
        tenant_id=TEST_TENANT_ID,
        audio_bytes_base64=b64_audio,
        sample_rate_hz=16000,
        top_k=3,
        timbre="neural_natural",
    )

    resp = await engine.execute_voice_rag(req)

    assert resp.session_id.startswith("vrag_")
    assert resp.tenant_id == TEST_TENANT_ID
    assert len(resp.transcribed_text) > 0
    assert len(resp.answer_text) > 0
    assert "doc_tactical_sop" in resp.answer_text or len(resp.citations) > 0
    assert len(resp.audio_bytes_base64) > 0
    assert resp.audio_format == "pcm16"
    assert resp.asr_latency_ms >= 0.0
    assert resp.retrieval_latency_ms >= 0.0
    assert resp.synthesis_latency_ms >= 0.0
    assert resp.tts_latency_ms >= 0.0
    assert resp.total_latency_ms > 0.0


# ── Test 5: Sovereign Appliance Manager Lifecycle & Manifest ─────────────────


def test_appliance_manager_lifecycle():
    """Verify manager status, hardware attestation, sealing states, and manifest."""
    sealer = HardwareVectorSealer()
    sentinel = AirgapNetworkSentinel()
    manager = SovereignApplianceManager(
        vector_sealer=sealer,
        airgap_sentinel=sentinel,
        deployment_mode=ApplianceDeploymentMode.AIR_GAPPED_STRICT,
        appliance_id="appl_test_node_01",
    )

    status_dto = manager.get_status()
    assert status_dto.appliance_id == "appl_test_node_01"
    assert status_dto.version == "2.5.0"
    assert status_dto.deployment_mode == ApplianceDeploymentMode.AIR_GAPPED_STRICT
    assert status_dto.hardware_attestation is not None
    assert status_dto.hardware_attestation.hardware_root == HardwareRootType.TPM2_PCR
    assert len(status_dto.embedded_models) == 4

    manifest = manager.get_appliance_manifest()
    assert manifest["appliance_id"] == "appl_test_node_01"
    assert manifest["version"] == "2.5.0"
    assert len(manifest["models"]) == 4


# ── Test 6: Platform Battery #41 Registration ────────────────────────────────


def test_platform_battery_41_registration():
    """Assert Platform Battery #41 is cataloged in BatteryService under EDGE_DISTRIBUTION."""
    resp = battery_service.get_platform_batteries()
    assert resp.total_batteries == 41, (
        f"Expected 41 platform batteries, got {resp.total_batteries}"
    )

    battery = battery_service.get_battery("sovereign_air_gapped_appliance")
    assert battery is not None, (
        "Battery 'sovereign_air_gapped_appliance' not found in catalog"
    )
    assert battery.category == BatteryCategory.EDGE_DISTRIBUTION
    assert battery.status == BatteryStatus.ACTIVE
    assert "M127" in battery.milestone
    assert battery.active_parameters.get("zero_egress_strict") is True
    assert battery.active_parameters.get("sealing_cipher") == "aes_256_gcm"


# ── Test 7: FastAPI REST Endpoints ───────────────────────────────────────────


def test_appliance_rest_api_status_and_audit():
    """Verify GET /v1/appliance/status, POST /v1/appliance/network/audit, and manifest."""
    headers = {"X-Admin-Master-Key": ADMIN_KEY}

    # 1. GET /v1/appliance/status
    res = client.get("/v1/appliance/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "2.5.0"
    assert "hardware_attestation" in data
    assert len(data["embedded_models"]) == 4

    # 2. POST /v1/appliance/network/audit
    res_audit = client.post(
        "/v1/appliance/network/audit",
        headers=headers,
        json={"strict_enforce": False},
    )
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert "is_compliant" in audit_data

    # 3. GET /v1/appliance/manifest
    res_manifest = client.get("/v1/appliance/manifest", headers=headers)
    assert res_manifest.status_code == 200
    man_data = res_manifest.json()
    assert man_data["version"] == "2.5.0"


def test_appliance_rest_api_seal_and_unseal():
    """Verify POST /v1/appliance/tenants/{tenantId}/seal and unseal roundtrip via REST."""
    headers = {"X-Admin-Master-Key": ADMIN_KEY}

    with tempfile.TemporaryDirectory() as tmpdir:
        plain_path = os.path.join(tmpdir, "api_plain.db")
        sealed_path = os.path.join(tmpdir, "api_sealed.db")
        unsealed_path = os.path.join(tmpdir, "api_unsealed.db")

        # Create dummy db file
        Path(plain_path).write_bytes(
            b"SQLite format 3\x00\x10\x00\x01\x01\x00@  \x00\x00\x00\x01"
        )

        # 1. Seal
        seal_payload = {
            "plain_db_path": plain_path,
            "sealed_db_path": sealed_path,
            "chunk_count": 5,
            "vector_dim": 768,
        }
        res_seal = client.post(
            f"/v1/appliance/tenants/{TEST_TENANT_ID}/seal",
            headers=headers,
            json=seal_payload,
        )
        assert res_seal.status_code == 200
        seal_data = res_seal.json()
        assert seal_data["cipher_suite"] == "aes_256_gcm"
        assert os.path.exists(sealed_path)

        # 2. Unseal
        unseal_payload = {
            "sealed_db_path": sealed_path,
            "unsealed_db_path": unsealed_path,
        }
        res_unseal = client.post(
            f"/v1/appliance/tenants/{TEST_TENANT_ID}/unseal",
            headers=headers,
            json=unseal_payload,
        )
        assert res_unseal.status_code == 200
        assert res_unseal.json()["success"] is True
        assert os.path.exists(unsealed_path)


def test_appliance_rest_api_voice_rag_query():
    """Verify POST /v1/appliance/tenants/{tenantId}/voice/query returns valid voice RAG output."""
    headers = {"X-Admin-Master-Key": ADMIN_KEY}

    samples = [int(10000 * (i % 2 * 2 - 1)) for i in range(320)]
    audio_frame = struct.pack("<320h", *samples)
    b64_audio = base64.b64encode(audio_frame).decode("ascii")

    voice_payload = {
        "tenant_id": TEST_TENANT_ID,
        "audio_bytes_base64": b64_audio,
        "sample_rate_hz": 16000,
        "top_k": 3,
        "timbre": "neural_natural",
    }

    res = client.post(
        f"/v1/appliance/tenants/{TEST_TENANT_ID}/voice/query",
        headers=headers,
        json=voice_payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"].startswith("vrag_")
    assert data["audio_format"] == "pcm16"
    assert len(data["audio_bytes_base64"]) > 0
    assert data["total_latency_ms"] > 0
