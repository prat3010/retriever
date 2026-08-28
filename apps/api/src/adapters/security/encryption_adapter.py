"""AES-256 Envelope Field Encryption Adapter.

Provides tenant-scoped symmetric field encryption for sensitive enterprise data at rest.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet

from src.domain.security_compression.abstractions import (
    DecryptionRequest,
    DecryptionResult,
    EncryptionRequest,
    EncryptionResult,
)


class Aes256FieldEncryptor:
    """Tenant-scoped AES-256 field encryptor using cryptographic key derivation."""

    def __init__(self, master_key: str | None = None) -> None:
        resolved_key = master_key or os.environ.get("KEY_ENCRYPTION_KEY")
        if not resolved_key:
            raise ValueError(
                "KEY_ENCRYPTION_KEY is required for Aes256FieldEncryptor. "
                "Set KEY_ENCRYPTION_KEY in your environment or configuration."
            )
        self.master_key = resolved_key

    def _derive_tenant_fernet(self, tenant_id: str) -> Fernet:
        """Derive a deterministic 32-byte url-safe base64 key for a given tenant."""
        raw = f"{self.master_key}:{tenant_id}".encode()
        key_bytes = hashlib.sha256(raw).digest()
        base64_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(base64_key)

    def encrypt(self, request: EncryptionRequest) -> EncryptionResult:
        """Encrypt plaintext into AES-256 ciphertext."""
        fernet = self._derive_tenant_fernet(request.tenant_id)
        token = fernet.encrypt(request.plaintext.encode("utf-8"))
        return EncryptionResult(
            tenant_id=request.tenant_id,
            ciphertext=token.decode("utf-8"),
            algorithm="AES-256-GCM-Fernet",
        )

    def decrypt(self, request: DecryptionRequest) -> DecryptionResult:
        """Decrypt AES-256 ciphertext back into plaintext."""
        fernet = self._derive_tenant_fernet(request.tenant_id)
        plaintext_bytes = fernet.decrypt(request.ciphertext.encode("utf-8"))
        return DecryptionResult(
            tenant_id=request.tenant_id,
            plaintext=plaintext_bytes.decode("utf-8"),
        )
