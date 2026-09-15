"""Domain Abstractions for Zero-Knowledge Proof (ZKP) Vector Attestation & Verifiable Document Grounding (M118).

Conforms strictly to Hexagonal Architecture boundaries:
- Pure Pydantic models, StrEnums, and standard library typing.
- Zero infrastructure, framework, or database dependencies.
- Cryptographically verifiable chunk commitments and Merkle DAG inclusion proofs.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class VerificationStatus(StrEnum):
    """Cryptographic attestation and verification outcome status."""

    VERIFIED = "verified"
    ROOT_MISMATCH = "root_mismatch"
    PROOF_INVALID = "proof_invalid"
    QUERY_MISMATCH = "query_mismatch"
    RESPONSE_MISMATCH = "response_mismatch"
    SIGNATURE_INVALID = "signature_invalid"
    CERTIFICATE_EXPIRED = "certificate_expired"


class MerkleDirection(StrEnum):
    """Direction of sibling node in a binary Merkle tree traversal."""

    LEFT = "left"
    RIGHT = "right"


class MerkleProofStep(BaseModel):
    """A single node step along the Merkle inclusion authentication path."""

    sibling_hash: str
    direction: MerkleDirection


class ChunkMerkleProof(BaseModel):
    """Cryptographic inclusion proof verifying that a chunk belongs to a document Merkle root."""

    chunk_id: str
    chunk_index: int = Field(ge=0)
    leaf_hash: str
    merkle_path: list[MerkleProofStep]
    document_root: str


class ChunkCommitment(BaseModel):
    """Zero-knowledge commitment to a cited vector chunk without revealing its raw text."""

    chunk_id: str
    chunk_index: int = Field(ge=0)
    leaf_hash: str
    merkle_proof: list[MerkleProofStep]
    similarity_score: float | None = None


class DocumentMerkleRoot(BaseModel):
    """The canonical root commitment of an indexed document's binary Merkle tree."""

    document_id: str
    tenant_id: str
    root_hash: str
    chunk_count: int = Field(ge=0)
    tree_depth: int = Field(ge=0)
    computed_at: float = Field(default_factory=time.time)


class ZkpGroundingCertificate(BaseModel):
    """Tamper-evident, cryptographically signed zero-knowledge grounding attestation certificate."""

    certificate_id: str
    tenant_id: str
    document_id: str
    document_merkle_root: str
    query_hash: str
    response_hash: str
    similarity_bound: float = Field(default=0.0, ge=0.0, le=1.0)
    chunk_commitments: list[ChunkCommitment] = Field(default_factory=list)
    issued_at: float = Field(default_factory=time.time)
    expires_at: float | None = None
    authority_public_key: str  # Hex-encoded Ed25519 public key
    attestation_signature: str  # Hex-encoded Ed25519 signature


class GroundingVerificationResult(BaseModel):
    """Comprehensive diagnostic verification report for a grounding attestation certificate."""

    status: VerificationStatus
    is_valid: bool
    details: str
    verified_at: float = Field(default_factory=time.time)
    checked_leaf_count: int = 0
    merkle_root_matched: bool = False
    signature_valid: bool = False
    query_match: bool = False
    response_match: bool = False
    execution_time_ms: float = 0.0


class ZkpAttestationPort(Protocol):
    """Hexagonal Port for ZKP Vector Attestation and Verifiable Document Grounding."""

    def compute_document_merkle_tree(
        self,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> DocumentMerkleRoot:
        """Construct binary Merkle tree across document chunks and return root commitment."""
        ...

    def generate_chunk_inclusion_proof(
        self,
        tenant_id: str,
        document_id: str,
        chunk_id: str,
        chunks: list[dict[str, Any]],
    ) -> ChunkMerkleProof:
        """Compute Merkle authentication path for an individual chunk leaf."""
        ...

    def issue_grounding_certificate(
        self,
        tenant_id: str,
        document_id: str,
        query: str,
        response: str,
        cited_chunks: list[dict[str, Any]],
        all_document_chunks: list[dict[str, Any]],
        similarity_bound: float = 0.7,
        ttl_seconds: float = 86400.0,
    ) -> ZkpGroundingCertificate:
        """Issue an Ed25519-signed Grounding Certificate verifying cited chunks belong to document root."""
        ...

    def verify_grounding_certificate(
        self,
        certificate: ZkpGroundingCertificate,
        query: str | None = None,
        response: str | None = None,
        expected_document_root: str | None = None,
    ) -> GroundingVerificationResult:
        """Publicly verify a Grounding Certificate against Merkle roots and signature."""
        ...

    def verify_merkle_proof(
        self,
        leaf_hash: str,
        proof_steps: list[MerkleProofStep],
        expected_root: str,
    ) -> bool:
        """Verify that a leaf hash correctly reconstructs the expected Merkle root."""
        ...

    def get_authority_public_key(self) -> str:
        """Return the hex-encoded Ed25519 public key of the attestation authority."""
        ...
