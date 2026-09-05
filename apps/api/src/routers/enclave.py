"""FastAPI Router for Confidential Micro-Enclaves & Hardware Attestation (M101).

Exposes administrative attestation and tenant-scoped sealing endpoints:
- GET /v1/admin/edge/attestation/nonce: Issue challenge nonce
- POST /v1/admin/edge/attestation/verify: Verify hardware evidence and signature
- GET /v1/admin/edge/attestation/report: System-wide runtime attestation status
- POST /v1/admin/edge/enclave/purge-keys: Emergency volatile memory scrub
- POST /v1/tenants/{tenantId}/edge/seal: AES-256-GCM tenant memory sealing
- POST /v1/tenants/{tenantId}/edge/unseal: Authenticated unsealing with AAD verification
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.enclave import (
    AttestationEvidence,
    AttestationNonce,
    EnclaveSealedPayload,
    EnclaveSealRequest,
    EnclaveUnsealRequest,
    EnclaveUnsealResponse,
    EnclaveVerificationReport,
)

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/v1/admin/edge",
    tags=["edge", "enclave", "admin"],
    dependencies=[Depends(verify_admin_key)],
)

tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/edge",
    tags=["edge", "enclave", "sealing"],
    dependencies=[Depends(verify_tenant_or_admin)],
)


# ── Administrative Attestation Endpoints ─────────────────────────────────


@admin_router.get("/attestation/nonce", response_model=AttestationNonce)
async def get_attestation_nonce(
    ttl_seconds: int = Query(default=300, ge=30, le=3600, description="Nonce validity window in seconds"),
) -> AttestationNonce:
    """Generate a fresh single-use cryptographic challenge nonce."""
    try:
        enclave = container.enclave_adapter
        return enclave.generate_nonce(ttl_seconds=ttl_seconds)
    except Exception as exc:
        logger.error(f"Failed to generate attestation challenge nonce: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Nonce generation failed: {exc}",
        ) from exc


@admin_router.post("/attestation/verify", response_model=EnclaveVerificationReport)
async def verify_attestation_evidence(
    evidence: AttestationEvidence,
    expected_nonce: str | None = Query(default=None, description="Optional expected challenge nonce"),
) -> EnclaveVerificationReport:
    """Verify cryptographic remote attestation evidence and platform PCR measurements."""
    try:
        enclave = container.enclave_adapter
        report = enclave.verify_evidence(evidence=evidence, expected_nonce=expected_nonce)
        return report
    except Exception as exc:
        logger.error(f"Attestation evidence verification error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Attestation verification failed: {exc}",
        ) from exc


@admin_router.get("/attestation/report", response_model=EnclaveVerificationReport)
async def get_system_attestation_report() -> EnclaveVerificationReport:
    """Convenience endpoint generating a fresh self-attestation verification report for this node."""
    try:
        enclave = container.enclave_adapter
        nonce_obj = enclave.generate_nonce(ttl_seconds=60)
        evidence = enclave.generate_evidence(nonce=nonce_obj.nonce)
        report = enclave.verify_evidence(evidence=evidence, expected_nonce=nonce_obj.nonce)
        return report
    except Exception as exc:
        logger.error(f"Failed to generate self-attestation report: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Self-attestation failed: {exc}",
        ) from exc


@admin_router.post("/enclave/purge-keys")
async def emergency_purge_volatile_keys() -> dict[str, Any]:
    """Execute immediate emergency zero-knowledge volatile key wipe from process memory."""
    try:
        sanitizer = container.memory_sanitizer
        purged_count = sanitizer.wipe_all()
        return {
            "status": "success",
            "purged_keys": purged_count,
            "timestamp": datetime.now(UTC).isoformat(),
            "message": "All volatile encryption keys aggressively sanitized via ctypes.memset.",
        }
    except Exception as exc:
        logger.error(f"Emergency key purge failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency key wipe failed: {exc}",
        ) from exc


# ── Tenant Memory Sealing Endpoints ─────────────────────────────────────


@tenant_router.post("/seal", response_model=EnclaveSealedPayload)
async def seal_tenant_payload(
    tenantId: str,
    request: EnclaveSealRequest,
) -> EnclaveSealedPayload:
    """Cryptographically seal tenant data with AES-256-GCM bound to enclave PCR0."""
    if request.tenant_id != tenantId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload tenant_id does not match route tenantId parameter.",
        )
    try:
        enclave = container.enclave_adapter
        sealed = enclave.seal(
            tenant_id=tenantId,
            plaintext=request.plaintext,
            aad=request.aad,
        )
        return sealed
    except Exception as exc:
        logger.error(f"Failed to seal payload for tenant {tenantId}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sealing operation failed: {exc}",
        ) from exc


@tenant_router.post("/unseal", response_model=EnclaveUnsealResponse)
async def unseal_tenant_payload(
    tenantId: str,
    request: EnclaveUnsealRequest,
) -> EnclaveUnsealResponse:
    """Decrypt and verify sealed tenant payload, enforcing tenant isolation and AAD integrity."""
    if request.tenant_id != tenantId or request.sealed_payload.tenant_id != tenantId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant isolation violation: sealed payload does not belong to this tenant.",
        )
    try:
        enclave = container.enclave_adapter
        unsealed_bytes = enclave.unseal(request.sealed_payload)
        return EnclaveUnsealResponse(
            tenant_id=tenantId,
            plaintext=unsealed_bytes.decode("utf-8"),
            verified_aad=True,
            unsealed_at=datetime.now(UTC),
        )
    except ValueError as val_err:
        logger.warning(f"Unseal verification rejected for tenant {tenantId}: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error(f"Unsealing failed for tenant {tenantId}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsealing failed: {exc}",
        ) from exc
