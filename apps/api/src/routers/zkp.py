"""FastAPI Router for Zero-Knowledge Proof (ZKP) Vector Attestation & Verifiable Document Grounding (M118).

Exposes:
- Battery #33 operational health probe (`/v1/zkp/health`)
- Document Merkle tree root commitment computation (`/v1/tenants/{tenantId}/zkp/merkle-root/{documentId}`)
- Chunk Merkle inclusion proof generation (`/v1/tenants/{tenantId}/zkp/proof/chunk/{chunkId}`)
- Grounding Certificate token issuance (`/v1/tenants/{tenantId}/zkp/attest`)
- Public zero-knowledge certificate verification (`/v1/zkp/verify`)
- Tenant compliance certificate audit trail (`/v1/tenants/{tenantId}/zkp/certificates`)
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.container import container
from src.domain.abstractions.zkp_attestation import (
    ChunkMerkleProof,
    DocumentMerkleRoot,
    GroundingVerificationResult,
    ZkpGroundingCertificate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Zero-Knowledge Vector Attestation & Grounding"])


# --- Request/Response DTOs ---

class ZkpHealthResponse(BaseModel):
    """Health check and parameter status for Platform Battery #33."""

    battery_id: str = "zkp_vector_attestation"
    status: str = "healthy"
    authority_public_key: str
    hash_algorithm: str = "sha256"
    signature_algorithm: str = "ed25519"
    merkle_tree_padding: str = "duplicate_leaf"
    zero_knowledge_commitments: bool = True
    public_verification_endpoint: str = "/v1/zkp/verify"


class ComputeMerkleRootRequest(BaseModel):
    """Payload for computing or retrieving document Merkle root commitment."""

    chunks: list[dict[str, Any]] = Field(default_factory=list)


class GenerateChunkProofRequest(BaseModel):
    """Payload for computing a Merkle inclusion authentication path for a chunk."""

    document_id: str
    chunks: list[dict[str, Any]] = Field(default_factory=list)


class IssueCertificateRequest(BaseModel):
    """Payload for issuing a cryptographically signed Grounding Certificate."""

    document_id: str
    query: str
    response: str
    cited_chunks: list[dict[str, Any]] = Field(default_factory=list)
    all_document_chunks: list[dict[str, Any]] = Field(default_factory=list)
    similarity_bound: float = Field(default=0.7, ge=0.0, le=1.0)
    ttl_seconds: float = Field(default=86400.0, ge=0.0)


class VerifyCertificateRequest(BaseModel):
    """Public verification request payload."""

    certificate: ZkpGroundingCertificate
    query: str | None = None
    response: str | None = None
    expected_document_root: str | None = None


# --- Endpoints ---

@router.get("/v1/zkp/health", response_model=ZkpHealthResponse)
async def get_zkp_health() -> ZkpHealthResponse:
    """Operational health probe and authority public key for Battery #33."""
    adapter = container.zkp_attestation_adapter
    return ZkpHealthResponse(
        authority_public_key=adapter.get_authority_public_key(),
    )


@router.post(
    "/v1/tenants/{tenantId}/zkp/merkle-root/{documentId}",
    response_model=DocumentMerkleRoot,
)
async def compute_document_merkle_root(
    tenantId: str = Path(..., description="Tenant ID"),
    documentId: str = Path(..., description="Document ID"),
    payload: ComputeMerkleRootRequest = ComputeMerkleRootRequest(),
) -> DocumentMerkleRoot:
    """Compute or retrieve canonical binary Merkle tree root commitment for a document."""
    try:
        adapter = container.zkp_attestation_adapter
        return adapter.compute_document_merkle_tree(
            tenant_id=tenantId,
            document_id=documentId,
            chunks=payload.chunks,
        )
    except Exception as exc:
        logger.error(f"Failed to compute document Merkle root: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Merkle root computation failed: {exc}",
        ) from exc


@router.post(
    "/v1/tenants/{tenantId}/zkp/proof/chunk/{chunkId}",
    response_model=ChunkMerkleProof,
)
async def generate_chunk_inclusion_proof(
    payload: GenerateChunkProofRequest,
    tenantId: str = Path(..., description="Tenant ID"),
    chunkId: str = Path(..., description="Chunk ID"),
) -> ChunkMerkleProof:
    """Generate cryptographic Merkle inclusion proof for an individual chunk leaf."""
    try:
        adapter = container.zkp_attestation_adapter
        return adapter.generate_chunk_inclusion_proof(
            tenant_id=tenantId,
            document_id=payload.document_id,
            chunk_id=chunkId,
            chunks=payload.chunks,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to generate chunk inclusion proof: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proof generation failed: {exc}",
        ) from exc


@router.post(
    "/v1/tenants/{tenantId}/zkp/attest",
    response_model=ZkpGroundingCertificate,
)
async def issue_grounding_certificate(
    payload: IssueCertificateRequest,
    tenantId: str = Path(..., description="Tenant ID"),
) -> ZkpGroundingCertificate:
    """Issue an Ed25519-signed Grounding Certificate verifying citations belong to the document root."""
    try:
        adapter = container.zkp_attestation_adapter
        return adapter.issue_grounding_certificate(
            tenant_id=tenantId,
            document_id=payload.document_id,
            query=payload.query,
            response=payload.response,
            cited_chunks=payload.cited_chunks,
            all_document_chunks=payload.all_document_chunks,
            similarity_bound=payload.similarity_bound,
            ttl_seconds=payload.ttl_seconds,
        )
    except Exception as exc:
        logger.error(f"Failed to issue grounding certificate: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Certificate issuance failed: {exc}",
        ) from exc


@router.post(
    "/v1/zkp/verify",
    response_model=GroundingVerificationResult,
)
async def verify_grounding_certificate(
    payload: VerifyCertificateRequest,
) -> GroundingVerificationResult:
    """Public zero-knowledge verification endpoint to validate any grounding certificate."""
    try:
        adapter = container.zkp_attestation_adapter
        return adapter.verify_grounding_certificate(
            certificate=payload.certificate,
            query=payload.query,
            response=payload.response,
            expected_document_root=payload.expected_document_root,
        )
    except Exception as exc:
        logger.error(f"Public certificate verification failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification process failed: {exc}",
        ) from exc


@router.get(
    "/v1/tenants/{tenantId}/zkp/certificates",
    response_model=list[ZkpGroundingCertificate],
)
async def list_recent_certificates(
    tenantId: str = Path(..., description="Tenant ID"),
    limit: int = 50,
) -> list[ZkpGroundingCertificate]:
    """Retrieve recently issued grounding certificates for tenant compliance audits."""
    adapter = container.zkp_attestation_adapter
    return adapter.list_recent_certificates(tenant_id=tenantId, limit=limit)
