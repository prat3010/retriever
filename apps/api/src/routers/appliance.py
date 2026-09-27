"""FastAPI Router for Sovereign Air-Gapped Appliance & Embedded Edge Engine (M127).

Exposes administrative telemetry, hardware attestation, vector sealing,
air-gap network compliance audits, and full-duplex offline voice queries.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.appliance import (
    AirgapEgressViolationError,
    AirgapNetworkAudit,
    ApplianceSealedLockedError,
    ApplianceStatusDTO,
    HardwareSealingTamperError,
    SealedVectorStoreMetadata,
    VoiceRAGQueryRequest,
    VoiceRAGQueryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/appliance",
    tags=["appliance", "airgap", "sovereign"],
)


class SealStoreRequest(BaseModel):
    """Payload to seal an on-disk SQLite vector database."""

    plain_db_path: str = Field(
        ..., description="Absolute or relative path to plaintext SQLite file"
    )
    sealed_db_path: str = Field(
        ..., description="Target path for sealed encrypted artifact"
    )
    chunk_count: int = Field(default=0, ge=0)
    vector_dim: int = Field(default=768, ge=1)


class UnsealStoreRequest(BaseModel):
    """Payload to unseal an encrypted vector database."""

    sealed_db_path: str = Field(..., description="Path to sealed encrypted artifact")
    unsealed_db_path: str = Field(
        ..., description="Target destination path for decrypted SQLite database"
    )


class AuditNetworkRequest(BaseModel):
    """Configuration for on-demand air-gap network audit."""

    strict_enforce: bool = Field(
        default=False,
        description="Whether to fail-closed and raise 403 on detected WAN egress",
    )


@router.get(
    "/status",
    response_model=ApplianceStatusDTO,
    dependencies=[Depends(verify_admin_key)],
)
async def get_appliance_status() -> ApplianceStatusDTO:
    """Retrieve comprehensive telemetry, hardware attestation, and sealing state."""
    try:
        manager = container.appliance_manager
        return manager.get_status()
    except Exception as exc:
        logger.error(f"Failed to fetch appliance status: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to read appliance status: {exc}",
        ) from exc


@router.post(
    "/network/audit",
    response_model=AirgapNetworkAudit,
    dependencies=[Depends(verify_admin_key)],
)
async def audit_network_isolation(
    payload: AuditNetworkRequest | None = None,
) -> AirgapNetworkAudit:
    """Execute live in-process network isolation and zero-egress audit."""
    strict = payload.strict_enforce if payload else False
    try:
        manager = container.appliance_manager
        return manager.audit_network(strict_enforce=strict)
    except AirgapEgressViolationError as exc:
        logger.warning(f"Air-gap egress violation raised: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Network audit failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network audit failed: {exc}",
        ) from exc


@router.get("/manifest", dependencies=[Depends(verify_admin_key)])
async def get_appliance_manifest() -> dict[str, Any]:
    """Retrieve the immutable distroless appliance manifest and pre-baked model checksums."""
    try:
        manager = container.appliance_manager
        return manager.get_appliance_manifest()
    except Exception as exc:
        logger.error(f"Failed to fetch appliance manifest: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to read appliance manifest: {exc}",
        ) from exc


@router.post(
    "/tenants/{tenantId}/seal",
    response_model=SealedVectorStoreMetadata,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def seal_tenant_store(
    tenantId: str, payload: SealStoreRequest
) -> SealedVectorStoreMetadata:
    """Hardware-seal an SQLite vector database file using host TPM/Enclave keys."""
    try:
        manager = container.appliance_manager
        return manager.seal_tenant_vector_store(
            tenant_id=tenantId,
            plain_db_path=payload.plain_db_path,
            sealed_db_path=payload.sealed_db_path,
            chunk_count=payload.chunk_count,
            vector_dim=payload.vector_dim,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(
            f"Sealing operation failed for tenant '{tenantId}': {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database sealing failed: {exc}",
        ) from exc


@router.post(
    "/tenants/{tenantId}/unseal",
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def unseal_tenant_store(
    tenantId: str, payload: UnsealStoreRequest
) -> dict[str, Any]:
    """Unseal an encrypted vector database if host hardware measurements match."""
    try:
        manager = container.appliance_manager
        success = manager.unseal_tenant_vector_store(
            tenant_id=tenantId,
            sealed_db_path=payload.sealed_db_path,
            unsealed_db_path=payload.unsealed_db_path,
        )
        return {"status": "unsealed", "tenant_id": tenantId, "success": success}
    except HardwareSealingTamperError as exc:
        logger.critical(
            f"Hardware sealing tamper detected for tenant '{tenantId}': {exc}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tamper detected: {exc}",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(f"Unsealing failed for tenant '{tenantId}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database unsealing failed: {exc}",
        ) from exc


@router.post(
    "/tenants/{tenantId}/voice/query",
    response_model=VoiceRAGQueryResponse,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def execute_voice_rag_query(
    tenantId: str, payload: VoiceRAGQueryRequest
) -> VoiceRAGQueryResponse:
    """Execute full-duplex offline voice RAG: Audio in -> ASR -> Retrieval -> LLM -> TTS -> Audio out."""
    if payload.tenant_id != tenantId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant mismatch: URL tenant '{tenantId}' != payload tenant '{payload.tenant_id}'.",
        )
    try:
        manager = container.appliance_manager
        return await manager.execute_voice_query(payload)
    except ApplianceSealedLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error(
            f"Voice RAG execution failed for tenant '{tenantId}': {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice RAG pipeline failed: {exc}",
        ) from exc
