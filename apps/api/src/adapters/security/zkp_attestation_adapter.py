"""ZKP Vector Attestation & Verifiable Document Grounding Adapter (M118).

Implements ZkpAttestationPort using:
- Deterministic SHA-256 Binary Merkle Trees with odd-leaf duplicate padding
- Zero-Knowledge Leaf Commitments bound to tenant, document, index, and chunk hashes
- Sub-millisecond Merkle inclusion authentication paths
- Asymmetric Ed25519 digital signatures for tamper-evident Grounding Certificates
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import time
from typing import Any
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from src.domain.abstractions.zkp_attestation import (
    ChunkCommitment,
    ChunkMerkleProof,
    DocumentMerkleRoot,
    GroundingVerificationResult,
    MerkleDirection,
    MerkleProofStep,
    VerificationStatus,
    ZkpAttestationPort,
    ZkpGroundingCertificate,
)

logger = logging.getLogger(__name__)


class ZkpAttestationAdapter(ZkpAttestationPort):
    """Production-grade cryptographic adapter for ZKP Vector Attestation and Grounding."""

    def __init__(self, authority_seed: bytes | None = None) -> None:
        """Initialize authority Ed25519 signing key and in-memory Merkle cache."""
        env_seed = os.environ.get("ZKP_AUTHORITY_SEED")
        if authority_seed:
            seed = authority_seed
        elif env_seed:
            seed = hashlib.sha256(env_seed.encode("utf-8")).digest()
        else:
            node_identifier = f"retriever_zkp_authority_{platform.node()}"
            seed = hashlib.sha256(node_identifier.encode("utf-8")).digest()

        # Deterministic 32-byte private key from seed
        self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        self._public_key = self._private_key.public_key()
        self._public_key_hex = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()

        # Cache: document_id -> (DocumentMerkleRoot, list_of_levels, chunk_id_to_index)
        self._merkle_cache: dict[str, tuple[DocumentMerkleRoot, list[list[str]], dict[str, int]]] = {}
        # Certificate ledger: list of recent certificates (in-memory audit trail)
        self._certificate_store: list[ZkpGroundingCertificate] = []

    def get_authority_public_key(self) -> str:
        """Return the hex-encoded Ed25519 public key of the attestation authority."""
        return self._public_key_hex

    def _compute_leaf_hash(
        self,
        tenant_id: str,
        document_id: str,
        chunk_index: int,
        content: str | None = None,
        content_hash: str | None = None,
    ) -> str:
        """Compute zero-knowledge cryptographic leaf commitment for a chunk."""
        if not content_hash:
            text = content or ""
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        leaf_preimage = f"{tenant_id}:{document_id}:{chunk_index}:{content_hash}"
        return hashlib.sha256(leaf_preimage.encode("utf-8")).hexdigest()

    def compute_document_merkle_tree(
        self,
        tenant_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> DocumentMerkleRoot:
        """Construct binary Merkle tree across document chunks and return root commitment."""
        cache_key = f"{tenant_id}:{document_id}"

        if not chunks:
            empty_root = hashlib.sha256(b"retriever:empty_document").hexdigest()
            doc_root = DocumentMerkleRoot(
                document_id=document_id,
                tenant_id=tenant_id,
                root_hash=empty_root,
                chunk_count=0,
                tree_depth=0,
                computed_at=time.time(),
            )
            self._merkle_cache[cache_key] = (doc_root, [[empty_root]], {})
            return doc_root

        # Build leaf hashes in order
        leaf_hashes: list[str] = []
        chunk_id_map: dict[str, int] = {}

        for idx, chunk in enumerate(chunks):
            cid = str(chunk.get("chunk_id") or chunk.get("id") or f"chk_{idx}")
            chunk_id_map[cid] = idx
            text = chunk.get("content") or chunk.get("chunk_text") or chunk.get("text") or ""
            c_hash = chunk.get("content_hash")
            leaf = self._compute_leaf_hash(tenant_id, document_id, idx, text, c_hash)
            leaf_hashes.append(leaf)

        # Build tree level by level
        current_level = list(leaf_hashes)
        levels: list[list[str]] = [current_level]

        while len(current_level) > 1:
            # If odd number of nodes at this level, duplicate the last node
            if len(current_level) % 2 != 0:
                current_level = list(current_level) + [current_level[-1]]

            next_level: list[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]
                parent = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
                next_level.append(parent)

            current_level = next_level
            levels.append(current_level)

        root_hash = levels[-1][0]
        tree_depth = len(levels) - 1

        doc_root = DocumentMerkleRoot(
            document_id=document_id,
            tenant_id=tenant_id,
            root_hash=root_hash,
            chunk_count=len(chunks),
            tree_depth=tree_depth,
            computed_at=time.time(),
        )

        self._merkle_cache[cache_key] = (doc_root, levels, chunk_id_map)
        return doc_root

    def generate_chunk_inclusion_proof(
        self,
        tenant_id: str,
        document_id: str,
        chunk_id: str,
        chunks: list[dict[str, Any]],
    ) -> ChunkMerkleProof:
        """Compute Merkle authentication path for an individual chunk leaf."""
        cache_key = f"{tenant_id}:{document_id}"

        if cache_key not in self._merkle_cache:
            self.compute_document_merkle_tree(tenant_id, document_id, chunks)

        doc_root, levels, chunk_id_map = self._merkle_cache[cache_key]

        if chunk_id not in chunk_id_map:
            raise ValueError(f"Chunk ID '{chunk_id}' not found in document '{document_id}' chunks.")

        leaf_idx = chunk_id_map[chunk_id]
        leaf_hash = levels[0][leaf_idx]

        # Traverse levels to build inclusion path
        proof_steps: list[MerkleProofStep] = []
        current_idx = leaf_idx

        for level in levels[:-1]:  # all levels except the root level
            padded_level = list(level)
            if len(padded_level) % 2 != 0:
                padded_level.append(padded_level[-1])

            if current_idx % 2 == 0:
                # Leaf is left child; sibling is right child
                sibling_idx = current_idx + 1
                proof_steps.append(
                    MerkleProofStep(
                        sibling_hash=padded_level[sibling_idx],
                        direction=MerkleDirection.RIGHT,
                    )
                )
            else:
                # Leaf is right child; sibling is left child
                sibling_idx = current_idx - 1
                proof_steps.append(
                    MerkleProofStep(
                        sibling_hash=padded_level[sibling_idx],
                        direction=MerkleDirection.LEFT,
                    )
                )

            current_idx = current_idx // 2

        return ChunkMerkleProof(
            chunk_id=chunk_id,
            chunk_index=leaf_idx,
            leaf_hash=leaf_hash,
            merkle_path=proof_steps,
            document_root=doc_root.root_hash,
        )

    def verify_merkle_proof(
        self,
        leaf_hash: str,
        proof_steps: list[MerkleProofStep],
        expected_root: str,
    ) -> bool:
        """Verify that a leaf hash correctly reconstructs the expected Merkle root."""
        curr = leaf_hash
        for step in proof_steps:
            if step.direction == MerkleDirection.RIGHT:
                combined = curr + step.sibling_hash
            else:
                combined = step.sibling_hash + curr
            curr = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        return curr == expected_root

    def _canonical_payload(
        self,
        certificate_id: str,
        tenant_id: str,
        document_id: str,
        document_merkle_root: str,
        query_hash: str,
        response_hash: str,
        similarity_bound: float,
        issued_at: float,
    ) -> str:
        """Build deterministic canonical string for digital signing and verification."""
        return (
            f"{certificate_id}:{tenant_id}:{document_id}:{document_merkle_root}:"
            f"{query_hash}:{response_hash}:{similarity_bound:.4f}:{issued_at:.2f}"
        )

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
        now = time.time()
        certificate_id = f"cert_zkp_{uuid4().hex[:16]}"
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()

        # Compute document Merkle root
        doc_root = self.compute_document_merkle_tree(tenant_id, document_id, all_document_chunks)

        # Build chunk commitments with Merkle proofs
        commitments: list[ChunkCommitment] = []
        for chunk in cited_chunks:
            cid = str(chunk.get("chunk_id") or chunk.get("id") or "")
            if not cid:
                continue
            proof = self.generate_chunk_inclusion_proof(tenant_id, document_id, cid, all_document_chunks)
            score = chunk.get("similarity") or chunk.get("score") or similarity_bound
            commitments.append(
                ChunkCommitment(
                    chunk_id=cid,
                    chunk_index=proof.chunk_index,
                    leaf_hash=proof.leaf_hash,
                    merkle_proof=proof.merkle_path,
                    similarity_score=float(score),
                )
            )

        payload_to_sign = self._canonical_payload(
            certificate_id=certificate_id,
            tenant_id=tenant_id,
            document_id=document_id,
            document_merkle_root=doc_root.root_hash,
            query_hash=query_hash,
            response_hash=response_hash,
            similarity_bound=similarity_bound,
            issued_at=now,
        )

        signature_bytes = self._private_key.sign(payload_to_sign.encode("utf-8"))
        signature_hex = signature_bytes.hex()

        cert = ZkpGroundingCertificate(
            certificate_id=certificate_id,
            tenant_id=tenant_id,
            document_id=document_id,
            document_merkle_root=doc_root.root_hash,
            query_hash=query_hash,
            response_hash=response_hash,
            similarity_bound=similarity_bound,
            chunk_commitments=commitments,
            issued_at=now,
            expires_at=now + ttl_seconds if ttl_seconds > 0 else None,
            authority_public_key=self._public_key_hex,
            attestation_signature=signature_hex,
        )

        # Append to audit store
        self._certificate_store.append(cert)
        if len(self._certificate_store) > 500:
            self._certificate_store.pop(0)

        return cert

    def verify_grounding_certificate(
        self,
        certificate: ZkpGroundingCertificate,
        query: str | None = None,
        response: str | None = None,
        expected_document_root: str | None = None,
    ) -> GroundingVerificationResult:
        """Publicly verify a Grounding Certificate against Merkle roots and signature."""
        start_t = time.perf_counter()
        now = time.time()

        # 1. Freshness / expiration check
        if certificate.expires_at and now > certificate.expires_at:
            return GroundingVerificationResult(
                status=VerificationStatus.CERTIFICATE_EXPIRED,
                is_valid=False,
                details=f"Certificate expired at {certificate.expires_at} (current time: {now:.2f})",
                execution_time_ms=(time.perf_counter() - start_t) * 1000,
            )

        # 2. Query hash integrity check (if query provided)
        query_match = True
        if query is not None:
            computed_query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
            if computed_query_hash != certificate.query_hash:
                return GroundingVerificationResult(
                    status=VerificationStatus.QUERY_MISMATCH,
                    is_valid=False,
                    details="Provided query does not match the attested query hash.",
                    query_match=False,
                    execution_time_ms=(time.perf_counter() - start_t) * 1000,
                )

        # 3. Response hash integrity check (if response provided)
        response_match = True
        if response is not None:
            computed_response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()
            if computed_response_hash != certificate.response_hash:
                return GroundingVerificationResult(
                    status=VerificationStatus.RESPONSE_MISMATCH,
                    is_valid=False,
                    details="Provided response does not match the attested response hash.",
                    query_match=query_match,
                    response_match=False,
                    execution_time_ms=(time.perf_counter() - start_t) * 1000,
                )

        # 4. Expected Document Merkle Root check
        root_matched = True
        if expected_document_root is not None:
            if expected_document_root != certificate.document_merkle_root:
                return GroundingVerificationResult(
                    status=VerificationStatus.ROOT_MISMATCH,
                    is_valid=False,
                    details=(
                        f"Expected document root '{expected_document_root}' does not match "
                        f"certificate root '{certificate.document_merkle_root}'."
                    ),
                    merkle_root_matched=False,
                    execution_time_ms=(time.perf_counter() - start_t) * 1000,
                )

        # 5. Merkle inclusion proof check for all cited chunks
        for comm in certificate.chunk_commitments:
            valid_path = self.verify_merkle_proof(
                leaf_hash=comm.leaf_hash,
                proof_steps=comm.merkle_proof,
                expected_root=certificate.document_merkle_root,
            )
            if not valid_path:
                return GroundingVerificationResult(
                    status=VerificationStatus.PROOF_INVALID,
                    is_valid=False,
                    details=(
                        f"Merkle inclusion proof failed for chunk '{comm.chunk_id}' "
                        f"(index {comm.chunk_index}). Leaf hash did not evaluate to root."
                    ),
                    checked_leaf_count=len(certificate.chunk_commitments),
                    execution_time_ms=(time.perf_counter() - start_t) * 1000,
                )

        # 6. Ed25519 digital signature verification
        canonical_payload = self._canonical_payload(
            certificate_id=certificate.certificate_id,
            tenant_id=certificate.tenant_id,
            document_id=certificate.document_id,
            document_merkle_root=certificate.document_merkle_root,
            query_hash=certificate.query_hash,
            response_hash=certificate.response_hash,
            similarity_bound=certificate.similarity_bound,
            issued_at=certificate.issued_at,
        )

        try:
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(certificate.authority_public_key)
            )
            pub_key.verify(
                bytes.fromhex(certificate.attestation_signature),
                canonical_payload.encode("utf-8"),
            )
            signature_valid = True
        except (InvalidSignature, ValueError) as exc:
            return GroundingVerificationResult(
                status=VerificationStatus.SIGNATURE_INVALID,
                is_valid=False,
                details=f"Authority digital signature verification failed: {exc}",
                signature_valid=False,
                execution_time_ms=(time.perf_counter() - start_t) * 1000,
            )

        elapsed_ms = (time.perf_counter() - start_t) * 1000

        return GroundingVerificationResult(
            status=VerificationStatus.VERIFIED,
            is_valid=True,
            details="Grounding certificate cryptographically verified. All Merkle inclusion paths and signatures are valid.",
            checked_leaf_count=len(certificate.chunk_commitments),
            merkle_root_matched=root_matched,
            signature_valid=signature_valid,
            query_match=query_match,
            response_match=response_match,
            execution_time_ms=round(elapsed_ms, 3),
        )

    def list_recent_certificates(self, tenant_id: str | None = None, limit: int = 50) -> list[ZkpGroundingCertificate]:
        """Return recently issued grounding certificates, optionally filtered by tenant."""
        certs = [c for c in self._certificate_store if tenant_id is None or c.tenant_id == tenant_id]
        return list(reversed(certs[-limit:]))
