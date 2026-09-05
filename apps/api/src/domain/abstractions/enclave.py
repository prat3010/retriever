"""Hexagonal Domain Abstractions for Confidential Micro-Enclaves & Hardware Attestation (M101).

Pure domain layer with zero infrastructure or framework imports.
Defines contracts for:
- Hardware enclave identity and remote attestation verification
- Nonce challenge-response protocols
- Authenticated AES-256-GCM memory sealing
- Zero-knowledge ephemeral memory sanitization
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class EnclavePlatform(StrEnum):
    """Supported hardware confidential computing and TPM environments."""

    INTEL_SGX = "intel_sgx"
    AMD_SEV = "amd_sev"
    AWS_NITRO = "aws_nitro"
    APPLE_SECURE_ENCLAVE = "apple_secure_enclave"
    TPM2 = "tpm2"
    SIMULATED_HSM = "simulated_hsm"


class AttestationTrustLevel(StrEnum):
    """Cryptographic attestation trust tiers."""

    HARDWARE_ROOTED = "hardware_rooted"
    VIRTUAL_ENCLAVE = "virtual_enclave"
    SIMULATED = "simulated"
    UNTRUSTED = "untrusted"


class CipherSuite(StrEnum):
    """Authenticated encryption cipher suites."""

    AES_256_GCM = "aes_256_gcm"


class AttestationNonce(BaseModel):
    """Cryptographic challenge nonce preventing replay attacks."""

    nonce: str = Field(..., description="Cryptographic hex challenge string")
    issued_at: datetime = Field(..., description="Timestamp of issuance")
    expires_at: datetime = Field(..., description="Expiry timestamp (default 300s)")
    consumed: bool = Field(default=False, description="Whether nonce was already consumed")


class AttestationEvidence(BaseModel):
    """Remote attestation payload emitted by the hardware enclave."""

    platform: EnclavePlatform = Field(..., description="Underlying enclave hardware architecture")
    nonce: str = Field(..., description="Challenge nonce echoed from the verifier")
    pcr_measurement: str = Field(..., description="SHA-256 platform measurement (PCR0 / MRENCLAVE)")
    public_key_pem: str = Field(..., description="Enclave ephemeral or persistent public key")
    signature: str = Field(..., description="Cryptographic digital signature over (nonce + pcr)")
    security_version: int = Field(default=1, ge=1, description="Enclave security version number (SVN)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Hardware firmware details")


class EnclaveVerificationReport(BaseModel):
    """Audit verification result validating hardware identity."""

    is_valid: bool = Field(..., description="True if signature, nonce freshness, and PCR match")
    trust_level: AttestationTrustLevel = Field(..., description="Assessed trust tier")
    platform: EnclavePlatform = Field(..., description="Enclave platform")
    pcr_measurement: str = Field(..., description="Verified PCR measurement")
    signer_identity: str = Field(..., description="Subject or fingerprint of the signing key")
    verified_at: datetime = Field(..., description="Verification timestamp")
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic audit metadata")


class EnclaveSealRequest(BaseModel):
    """Request to seal sensitive tenant data under hardware enclave protection."""

    tenant_id: str = Field(..., description="Target tenant UUID")
    plaintext: str = Field(..., description="Plaintext content to be sealed")
    aad: str | None = Field(default=None, description="Optional Additional Authenticated Data")


class EnclaveSealedPayload(BaseModel):
    """Tamper-proof sealed payload bound to tenant and hardware enclave."""

    tenant_id: str = Field(..., description="Tenant identifier")
    key_id: str = Field(..., description="Unique key identifier derived from root HKDF")
    cipher_suite: CipherSuite = Field(default=CipherSuite.AES_256_GCM)
    nonce_iv: str = Field(..., description="Base64-encoded 96-bit initialization vector")
    ciphertext: str = Field(..., description="Base64-encoded ciphertext")
    auth_tag: str = Field(..., description="Base64-encoded 128-bit authentication tag")
    aad: str | None = Field(default=None, description="Additional Authenticated Data used during sealing")
    pcr_binding: str = Field(..., description="PCR measurement bound to this payload")
    sealed_at: datetime = Field(..., description="Timestamp when payload was sealed")


class EnclaveUnsealRequest(BaseModel):
    """Request to decrypt and unseal a sealed payload."""

    tenant_id: str = Field(..., description="Tenant identifier")
    sealed_payload: EnclaveSealedPayload = Field(..., description="Sealed payload to decrypt")


class EnclaveUnsealResponse(BaseModel):
    """Result of unsealing operation."""

    tenant_id: str = Field(..., description="Tenant identifier")
    plaintext: str = Field(..., description="Decrypted plaintext string")
    verified_aad: bool = Field(default=True, description="True if AAD was verified")
    unsealed_at: datetime = Field(..., description="Timestamp when payload was unsealed")


# ── Protocols (Pure Interfaces) ──────────────────────────────────────────


class HardwareAttestationProtocol(Protocol):
    """Protocol for generating and cryptographically verifying hardware remote attestation."""

    def generate_nonce(self, ttl_seconds: int = 300) -> AttestationNonce:
        """Generate a fresh single-use cryptographic challenge nonce."""
        ...

    def generate_evidence(self, nonce: str) -> AttestationEvidence:
        """Generate hardware-signed attestation evidence containing PCR measurements."""
        ...

    def verify_evidence(
        self,
        evidence: AttestationEvidence,
        expected_nonce: str | None = None,
    ) -> EnclaveVerificationReport:
        """Verify attestation evidence freshness and digital signature against trusted roots."""
        ...


class EnclaveKeySealerProtocol(Protocol):
    """Protocol for tenant-scoped hardware-rooted authenticated memory sealing."""

    def seal(
        self,
        tenant_id: str,
        plaintext: bytes | str,
        aad: str | None = None,
    ) -> EnclaveSealedPayload:
        """Encrypt and seal data under tenant-derived key with AES-256-GCM."""
        ...

    def unseal(
        self,
        payload: EnclaveSealedPayload,
    ) -> bytes:
        """Decrypt and verify sealed payload, enforcing tenant isolation and AAD integrity."""
        ...


class MemorySanitizerProtocol(Protocol):
    """Protocol for ephemeral key management with zero-knowledge memory scrubbing."""

    def allocate_ephemeral_key(self, key_id: str, key_bytes: bytes) -> str:
        """Store volatile key bytes in a tracked mutable buffer."""
        ...

    def get_ephemeral_key(self, key_id: str) -> bytes | None:
        """Retrieve key bytes from the buffer if still allocated."""
        ...

    def wipe_key(self, key_id: str) -> bool:
        """Aggressively zero memory buffer for specific key in-place."""
        ...

    def wipe_all(self) -> int:
        """Zero all allocated volatile keys immediately."""
        ...
