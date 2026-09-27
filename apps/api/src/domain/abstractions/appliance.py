"""Hexagonal Domain Abstractions for Sovereign Air-Gapped Appliance & Embedded Edge Engine (M127).

Defines pure domain entities, enums, data models, protocols, and exceptions for:
- Sovereign air-gapped deployment modes and appliance lifecycle
- Hardware-rooted vector index sealing (TPM 2.0 / Apple Secure Enclave / Linux Keyring)
- Zero-egress network isolation verification and fail-closed security invariants
- Offline full-duplex neural voice RAG query orchestration
- Standalone distroless appliance manifest and integrity attestation

Strictly Hexagonal: Zero database, ORM, cryptographic library, or web framework imports.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

# ── Domain Exceptions ────────────────────────────────────────────────────────


class AirgapEgressViolationError(Exception):
    """Raised when an outbound non-loopback network socket or WAN egress is detected."""


class HardwareSealingTamperError(Exception):
    """Raised when hardware PCR measurements, signatures, or cryptographic tags fail verification."""


class ApplianceSealedLockedError(Exception):
    """Raised when attempting vector search or database operations on a sealed or locked appliance."""


# ── Enums ────────────────────────────────────────────────────────────────────


class ApplianceDeploymentMode(StrEnum):
    """Deployment mode governing network and hardware sealing invariants."""

    AIR_GAPPED_STRICT = "air_gapped_strict"
    TACTICAL_EDGE = "tactical_edge"
    HYBRID_EDGE = "hybrid_edge"
    STANDALONE_DEV = "standalone_dev"


class ApplianceSealingState(StrEnum):
    """Cryptographic at-rest state of the embedded vector store."""

    UNSEALED = "unsealed"
    SEALED = "sealed"
    LOCKED_TAMPER_DETECTED = "locked_tamper_detected"
    PROVISIONING = "provisioning"


class AirgapNetworkState(StrEnum):
    """Network egress posture of the host environment."""

    ISOLATED_COMPLIANT = "isolated_compliant"
    EGRESS_VIOLATION_DETECTED = "egress_violation_detected"
    AUDIT_PENDING = "audit_pending"


class HardwareRootType(StrEnum):
    """Hardware security module or processor root of trust."""

    TPM2_PCR = "tpm2_pcr"
    APPLE_SECURE_ENCLAVE = "apple_secure_enclave"
    LINUX_KEYRING = "linux_keyring"
    SIMULATED_HSM = "simulated_hsm"


# ── Domain Models & DTOs ─────────────────────────────────────────────────────


class ApplianceHardwareAttestation(BaseModel):
    """Hardware attestation quote binding the appliance to physical silicon."""

    platform: str = Field(..., description="Operating system architecture and kernel")
    hardware_root: HardwareRootType = Field(default=HardwareRootType.TPM2_PCR)
    pcr_measurement: str = Field(
        ..., description="SHA-256 measurement digest of boot/firmware state"
    )
    key_id: str = Field(..., description="Identifier of the hardware-bound sealing key")
    sealed_at: datetime = Field(..., description="Timestamp of the sealing operation")
    signature: str = Field(
        ..., description="Hardware-signed attestation quote or HMAC digest"
    )


class AirgapNetworkAudit(BaseModel):
    """Detailed result of an in-process network isolation inspection."""

    audited_at: datetime = Field(..., description="Timestamp of network inspection")
    active_interfaces: list[str] = Field(
        default_factory=list, description="Network interfaces detected on host"
    )
    active_sockets_count: int = Field(
        default=0, description="Total active listening/connected sockets"
    )
    dns_resolvers: list[str] = Field(
        default_factory=list, description="Configured system DNS servers"
    )
    blocked_egress_attempts: int = Field(
        default=0, description="Number of rejected external connection attempts"
    )
    is_compliant: bool = Field(
        ..., description="Whether appliance satisfies zero-egress invariants"
    )
    audit_notes: str = Field(
        default="", description="Diagnostic details or detected anomalies"
    )


class SealedVectorStoreMetadata(BaseModel):
    """Cryptographic metadata associated with a sealed on-disk vector database."""

    tenant_id: str = Field(..., description="Tenant owning the sealed vector database")
    database_file: str = Field(
        ..., description="Path or basename of the sealed database artifact"
    )
    chunk_count: int = Field(default=0, description="Number of indexed document chunks")
    vector_dimension: int = Field(default=768, description="Embedding vector dimension")
    sealing_state: ApplianceSealingState = Field(default=ApplianceSealingState.SEALED)
    cipher_suite: str = Field(
        default="aes_256_gcm",
        description="Symmetric authenticated encryption algorithm",
    )
    sealed_checksum_sha256: str = Field(
        ..., description="SHA-256 integrity hash of the sealed database file"
    )
    hardware_fingerprint: str = Field(
        ..., description="Fingerprint of the hardware root that sealed the database"
    )


class EmbeddedModelManifestItem(BaseModel):
    """Manifest entry for pre-baked models present in the sovereign appliance."""

    model_name: str
    model_type: str  # "embedding", "asr_whisper", "tts_piper", "slm_synthesis"
    quantization: str  # "q4_k_m", "fp16", "onnx_int8"
    file_size_bytes: int
    sha256_checksum: str
    is_loaded: bool = True


class ApplianceStatusDTO(BaseModel):
    """Unified telemetry and status report for the sovereign appliance."""

    appliance_id: str = Field(..., description="Unique appliance node identifier")
    version: str = Field(
        default="2.5.0", description="Retriever Sovereign Appliance release version"
    )
    deployment_mode: ApplianceDeploymentMode = Field(
        default=ApplianceDeploymentMode.AIR_GAPPED_STRICT
    )
    sealing_state: ApplianceSealingState = Field(default=ApplianceSealingState.UNSEALED)
    network_state: AirgapNetworkState = Field(
        default=AirgapNetworkState.ISOLATED_COMPLIANT
    )
    hardware_attestation: ApplianceHardwareAttestation | None = None
    network_audit: AirgapNetworkAudit | None = None
    sealed_vector_stores: list[SealedVectorStoreMetadata] = Field(default_factory=list)
    embedded_models: list[EmbeddedModelManifestItem] = Field(default_factory=list)
    uptime_seconds: float = Field(default=0.0)


# ── Full-Duplex Voice RAG Models ─────────────────────────────────────────────


class VoiceRAGQueryRequest(BaseModel):
    """Request payload for an end-to-end sovereign offline voice query."""

    tenant_id: str = Field(..., description="Tenant context for search and answering")
    audio_bytes_base64: str = Field(
        ..., description="Base64-encoded audio bytes (PCM16, WAV, or Opus)"
    )
    sample_rate_hz: int = Field(
        default=16000, description="Sampling rate of input audio in Hertz"
    )
    top_k: int = Field(
        default=5, description="Number of hybrid context chunks to retrieve"
    )
    timbre: str = Field(
        default="neural_natural", description="Voice timbre preset for synthesis"
    )
    system_prompt: str | None = Field(
        default=None, description="Optional custom system prompt"
    )


class VoiceRAGQueryResponse(BaseModel):
    """Response payload containing transcribed query, synthesized speech, and metrics."""

    session_id: str = Field(
        ..., description="Unique voice interaction session identifier"
    )
    tenant_id: str = Field(...)
    transcribed_text: str = Field(
        ..., description="Transcribed query produced by local Whisper"
    )
    answer_text: str = Field(
        ..., description="Grounded answer produced by sovereign engine"
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list, description="Grounding source citations"
    )
    audio_bytes_base64: str = Field(
        ..., description="Base64-encoded synthesized neural speech audio"
    )
    audio_format: str = Field(
        default="pcm16", description="Codec of returned synthesized audio"
    )
    audio_duration_ms: float = Field(
        default=0.0, description="Duration of synthesized speech in milliseconds"
    )
    asr_latency_ms: float = Field(
        default=0.0, description="Whisper ASR transcription latency"
    )
    retrieval_latency_ms: float = Field(
        default=0.0, description="Hybrid vector + FTS5 search latency"
    )
    synthesis_latency_ms: float = Field(
        default=0.0, description="LLM/SLM generation latency"
    )
    tts_latency_ms: float = Field(
        default=0.0, description="Piper neural TTS synthesis latency"
    )
    total_latency_ms: float = Field(
        default=0.0, description="Total full-duplex turn-taking latency"
    )


# ── Abstract Protocols ───────────────────────────────────────────────────────


class VectorSealerProtocol(Protocol):
    """Abstract contract for hardware-bound vector database encryption at rest."""

    def seal_database(
        self,
        tenant_id: str,
        plain_db_path: str,
        sealed_db_path: str,
        pcr_measurement: str,
    ) -> SealedVectorStoreMetadata:
        """Seal an SQLite vector database using hardware-derived AES-256-GCM."""
        ...

    def unseal_database(
        self,
        tenant_id: str,
        sealed_db_path: str,
        unsealed_db_path: str,
        pcr_measurement: str,
    ) -> bool:
        """Unseal an encrypted vector database if PCR measurements match."""
        ...


class AirgapSentinelProtocol(Protocol):
    """Abstract contract for in-process network isolation and egress auditing."""

    def audit_isolation(self, strict_enforce: bool = True) -> AirgapNetworkAudit:
        """Inspect network interfaces, sockets, and routes to verify air-gap compliance."""
        ...
