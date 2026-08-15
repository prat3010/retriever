"""Domain models and abstractions for Context Compression & Zero-Trust Field Encryption."""

from pydantic import BaseModel, Field


class CompressionRequest(BaseModel):
    """Input payload to trigger prompt context window compression."""

    text: str = Field(..., description="Raw text context to be compressed")
    compression_rate: float = Field(
        default=0.5, ge=0.1, le=0.9, description="Target ratio of text to retain (0.1 to 0.9)"
    )


class CompressionResult(BaseModel):
    """Output response returned by the Context Compressor."""

    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float


class EncryptionRequest(BaseModel):
    """Input payload to encrypt sensitive plaintext content."""

    tenant_id: str = Field(..., description="Target tenant ID for key derivation")
    plaintext: str = Field(..., description="Sensitive raw text payload")


class EncryptionResult(BaseModel):
    """Output payload containing AES-256 encrypted ciphertext."""

    tenant_id: str
    ciphertext: str
    algorithm: str = Field(default="AES-256-GCM-Fernet")


class DecryptionRequest(BaseModel):
    """Input payload to decrypt sensitive ciphertext content."""

    tenant_id: str = Field(..., description="Target tenant ID for key derivation")
    ciphertext: str = Field(..., description="Encrypted ciphertext payload")


class DecryptionResult(BaseModel):
    """Output payload containing decrypted plaintext."""

    tenant_id: str
    plaintext: str
