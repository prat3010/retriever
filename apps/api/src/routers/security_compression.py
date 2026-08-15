"""FastAPI Router for Context Compression and Security Encryption endpoints."""

from fastapi import APIRouter, Depends, status

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.security_compression.abstractions import (
    CompressionRequest,
    CompressionResult,
    DecryptionRequest,
    DecryptionResult,
    EncryptionRequest,
    EncryptionResult,
)

router = APIRouter(prefix="/v1", tags=["Security & Context Compression"])


@router.post(
    "/tenants/{tenantId}/context/compress",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=CompressionResult,
)
async def compress_context_window(
    tenantId: str,
    request: CompressionRequest,
) -> CompressionResult:
    """Compress context window text to reduce LLM prompt token overhead."""
    return container.context_compressor.compress(request)


@router.post(
    "/tenants/{tenantId}/security/encrypt",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=EncryptionResult,
)
async def encrypt_field_data(
    tenantId: str,
    request: EncryptionRequest,
) -> EncryptionResult:
    """Encrypt sensitive plaintext into AES-256 field ciphertext."""
    request.tenant_id = tenantId
    return container.field_encryptor.encrypt(request)


@router.post(
    "/tenants/{tenantId}/security/decrypt",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=DecryptionResult,
)
async def decrypt_field_data(
    tenantId: str,
    request: DecryptionRequest,
) -> DecryptionResult:
    """Decrypt AES-256 ciphertext back into original plaintext."""
    request.tenant_id = tenantId
    return container.field_encryptor.decrypt(request)
