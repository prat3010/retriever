import base64
import hashlib
import os
from cryptography.fernet import Fernet


class ConfigEncrypter:
    """Helper to encrypt and decrypt sensitive configuration properties (e.g., API keys) at rest."""

    def __init__(self, key_encryption_key: str | None = None) -> None:
        kek = key_encryption_key or os.environ.get("KEY_ENCRYPTION_KEY", "dev-key-encryption-key-must-be-32-bytes-long=")
        # Securely hash KEK to derive a valid 32-byte URL-safe base64-encoded key for Fernet
        key_bytes = hashlib.sha256(kek.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.fernet = Fernet(fernet_key)

    def encrypt(self, plaintext: str | None) -> str | None:
        """Encrypt plaintext string, returning a base64-encoded ciphertext string."""
        if not plaintext or plaintext == "********":
            return plaintext
        return self.fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str | None) -> str | None:
        """Decrypt ciphertext string, returning plaintext."""
        if not ciphertext or ciphertext == "********":
            return ciphertext
        try:
            return self.fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception:
            # Graceful migration: return ciphertext unchanged if it's plaintext
            return ciphertext
