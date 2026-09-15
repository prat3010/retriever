"""Comprehensive Pytest Suite for Zero-Knowledge Proof (ZKP) Vector Attestation & Verifiable Grounding (M118).

Tests:
- Merkle tree construction across power-of-two and odd chunk counts
- Inclusion authentication path generation and tamper rejection
- Grounding Certificate token issuance and Ed25519 asymmetric signing
- Public zero-knowledge verification (query mismatch, response mismatch, root mismatch, signature tamper)
- FastAPI REST endpoints (/v1/zkp/health, /v1/zkp/verify, /v1/tenants/{tenantId}/zkp/...)
- Platform Battery #33 registry validation
"""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.security.zkp_attestation_adapter import ZkpAttestationAdapter
from src.domain.abstractions.zkp_attestation import (
    MerkleDirection,
    MerkleProofStep,
    VerificationStatus,
)
from src.domain.batteries.battery_service import BatteryService
from src.main import app


@pytest.fixture
def zkp_adapter() -> ZkpAttestationAdapter:
    """Fixture providing an isolated ZKP adapter with a deterministic authority seed."""
    return ZkpAttestationAdapter(authority_seed=b"0" * 32)


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Sample chunk documents for Merkle testing."""
    return [
        {"chunk_id": "chk_0", "chunk_index": 0, "text": "Section 1: Enterprise SLA Guarantees 99.99% uptime."},
        {"chunk_id": "chk_1", "chunk_index": 1, "text": "Section 2: Data residency restricted to EU-Central-1."},
        {"chunk_id": "chk_2", "chunk_index": 2, "text": "Section 3: Zero-Knowledge proof attestation verifies grounding."},
        {"chunk_id": "chk_3", "chunk_index": 3, "text": "Section 4: Penalties for breach shall not exceed 10x monthly fee."},
        {"chunk_id": "chk_4", "chunk_index": 4, "text": "Section 5: Arbitration venue is Zurich, Switzerland."},
    ]


# --- Unit Tests: Merkle Tree & Inclusion Proofs ---

def test_empty_document_merkle_tree(zkp_adapter: ZkpAttestationAdapter):
    """Test Merkle tree creation with empty chunk list."""
    doc_root = zkp_adapter.compute_document_merkle_tree("tn_test", "doc_empty", [])
    assert doc_root.chunk_count == 0
    assert doc_root.tree_depth == 0
    assert len(doc_root.root_hash) == 64


def test_single_chunk_merkle_tree(zkp_adapter: ZkpAttestationAdapter):
    """Test Merkle tree creation with single chunk."""
    chunks = [{"chunk_id": "chk_single", "chunk_index": 0, "text": "Sole clause of contract."}]
    doc_root = zkp_adapter.compute_document_merkle_tree("tn_test", "doc_single", chunks)
    assert doc_root.chunk_count == 1
    assert doc_root.tree_depth == 0

    proof = zkp_adapter.generate_chunk_inclusion_proof("tn_test", "doc_single", "chk_single", chunks)
    assert proof.leaf_hash == doc_root.root_hash
    assert zkp_adapter.verify_merkle_proof(proof.leaf_hash, proof.merkle_path, doc_root.root_hash) is True


def test_odd_chunk_count_padding(zkp_adapter: ZkpAttestationAdapter, sample_chunks: list[dict]):
    """Test that odd chunk count (5 chunks) correctly balances the tree with duplicate leaf padding."""
    doc_root = zkp_adapter.compute_document_merkle_tree("tn_test", "doc_5", sample_chunks)
    assert doc_root.chunk_count == 5
    # 5 leaves -> padded to 6, level 1 has 3 leaves -> padded to 4, level 2 has 2 -> level 3 root
    assert doc_root.tree_depth >= 3

    # All 5 chunks must have valid inclusion proofs
    for chunk in sample_chunks:
        proof = zkp_adapter.generate_chunk_inclusion_proof("tn_test", "doc_5", chunk["chunk_id"], sample_chunks)
        assert proof.document_root == doc_root.root_hash
        valid = zkp_adapter.verify_merkle_proof(proof.leaf_hash, proof.merkle_path, doc_root.root_hash)
        assert valid is True, f"Inclusion proof failed for chunk {chunk['chunk_id']}"


def test_merkle_proof_tamper_detection(zkp_adapter: ZkpAttestationAdapter, sample_chunks: list[dict]):
    """Test that altered leaf hashes, sibling hashes, or directions fail verification."""
    doc_root = zkp_adapter.compute_document_merkle_tree("tn_test", "doc_tamper", sample_chunks)
    proof = zkp_adapter.generate_chunk_inclusion_proof("tn_test", "doc_tamper", "chk_2", sample_chunks)

    # 1. Tampered leaf hash
    tampered_leaf = "f" * 64
    assert zkp_adapter.verify_merkle_proof(tampered_leaf, proof.merkle_path, doc_root.root_hash) is False

    # 2. Tampered sibling hash in path
    tampered_steps = [
        MerkleProofStep(sibling_hash="a" * 64, direction=step.direction)
        if i == 0 else step
        for i, step in enumerate(proof.merkle_path)
    ]
    assert zkp_adapter.verify_merkle_proof(proof.leaf_hash, tampered_steps, doc_root.root_hash) is False

    # 3. Inverted direction
    inverted_steps = [
        MerkleProofStep(
            sibling_hash=step.sibling_hash,
            direction=MerkleDirection.LEFT if step.direction == MerkleDirection.RIGHT else MerkleDirection.RIGHT,
        )
        if i == 0 else step
        for i, step in enumerate(proof.merkle_path)
    ]
    assert zkp_adapter.verify_merkle_proof(proof.leaf_hash, inverted_steps, doc_root.root_hash) is False


# --- Unit Tests: Grounding Certificate Issuance & Verification ---

def test_grounding_certificate_lifecycle(zkp_adapter: ZkpAttestationAdapter, sample_chunks: list[dict]):
    """Test complete issuance, signing, and verification lifecycle of Grounding Certificates."""
    query = "What is the guaranteed platform uptime?"
    response = "The platform guarantees 99.99% uptime according to Section 1."
    cited = [sample_chunks[0]]

    cert = zkp_adapter.issue_grounding_certificate(
        tenant_id="tn_compliance_01",
        document_id="doc_sla",
        query=query,
        response=response,
        cited_chunks=cited,
        all_document_chunks=sample_chunks,
        similarity_bound=0.92,
    )

    assert cert.certificate_id.startswith("cert_zkp_")
    assert cert.tenant_id == "tn_compliance_01"
    assert len(cert.chunk_commitments) == 1
    assert cert.chunk_commitments[0].chunk_id == "chk_0"
    assert len(cert.attestation_signature) == 128  # Ed25519 64-byte hex signature

    # 1. Happy path verification
    result = zkp_adapter.verify_grounding_certificate(
        certificate=cert,
        query=query,
        response=response,
        expected_document_root=cert.document_merkle_root,
    )
    assert result.is_valid is True
    assert result.status == VerificationStatus.VERIFIED
    assert result.signature_valid is True
    assert result.merkle_root_matched is True
    assert result.query_match is True
    assert result.response_match is True


def test_grounding_certificate_tampered_response(zkp_adapter: ZkpAttestationAdapter, sample_chunks: list[dict]):
    """Test that modifying the AI response causes RESPONSE_MISMATCH."""
    query = "What is data residency?"
    response = "Data is stored in EU-Central-1."
    cert = zkp_adapter.issue_grounding_certificate(
        tenant_id="tn_compliance_01",
        document_id="doc_sla",
        query=query,
        response=response,
        cited_chunks=[sample_chunks[1]],
        all_document_chunks=sample_chunks,
    )

    tampered_response = "Data is stored in US-East-1."
    result = zkp_adapter.verify_grounding_certificate(certificate=cert, response=tampered_response)
    assert result.is_valid is False
    assert result.status == VerificationStatus.RESPONSE_MISMATCH


def test_grounding_certificate_tampered_signature(zkp_adapter: ZkpAttestationAdapter, sample_chunks: list[dict]):
    """Test that a forged digital signature fails verification."""
    cert = zkp_adapter.issue_grounding_certificate(
        tenant_id="tn_compliance_01",
        document_id="doc_sla",
        query="Arbitration location?",
        response="Zurich, Switzerland.",
        cited_chunks=[sample_chunks[4]],
        all_document_chunks=sample_chunks,
    )

    # Corrupt the signature hex
    forged_cert = cert.model_copy(update={"attestation_signature": "00" * 64})
    result = zkp_adapter.verify_grounding_certificate(certificate=forged_cert)
    assert result.is_valid is False
    assert result.status == VerificationStatus.SIGNATURE_INVALID


def test_grounding_certificate_expired(zkp_adapter: ZkpAttestationAdapter, sample_chunks: list[dict]):
    """Test that expired certificates are rejected."""
    cert = zkp_adapter.issue_grounding_certificate(
        tenant_id="tn_compliance_01",
        document_id="doc_sla",
        query="Arbitration location?",
        response="Zurich, Switzerland.",
        cited_chunks=[sample_chunks[4]],
        all_document_chunks=sample_chunks,
        ttl_seconds=0.01,
    )

    time.sleep(0.02)
    result = zkp_adapter.verify_grounding_certificate(certificate=cert)
    assert result.is_valid is False
    assert result.status == VerificationStatus.CERTIFICATE_EXPIRED


# --- Integration Tests: FastAPI Endpoints ---

@pytest.mark.asyncio
async def test_fastapi_zkp_endpoints(sample_chunks: list[dict]):
    """Test all REST endpoints for ZKP attestation via ASGI AsyncClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health probe
        res = await client.get("/v1/zkp/health")
        assert res.status_code == 200
        health = res.json()
        assert health["battery_id"] == "zkp_vector_attestation"
        assert health["status"] == "healthy"
        assert "authority_public_key" in health

        # 2. Compute Document Merkle Root
        tenant_id = "tn_api_zkp_test"
        doc_id = "doc_fastapi_spec"
        res = await client.post(
            f"/v1/tenants/{tenant_id}/zkp/merkle-root/{doc_id}",
            json={"chunks": sample_chunks},
        )
        assert res.status_code == 200
        root_data = res.json()
        assert root_data["document_id"] == doc_id
        assert root_data["chunk_count"] == 5
        merkle_root = root_data["root_hash"]

        # 3. Generate Chunk Inclusion Proof
        res = await client.post(
            f"/v1/tenants/{tenant_id}/zkp/proof/chunk/chk_2",
            json={"document_id": doc_id, "chunks": sample_chunks},
        )
        assert res.status_code == 200
        proof_data = res.json()
        assert proof_data["chunk_id"] == "chk_2"
        assert proof_data["document_root"] == merkle_root
        assert len(proof_data["merkle_path"]) > 0

        # 4. Issue Grounding Certificate
        query = "What is the arbitration venue?"
        response = "Section 5 specifies Zurich, Switzerland."
        res = await client.post(
            f"/v1/tenants/{tenant_id}/zkp/attest",
            json={
                "document_id": doc_id,
                "query": query,
                "response": response,
                "cited_chunks": [sample_chunks[4]],
                "all_document_chunks": sample_chunks,
                "similarity_bound": 0.88,
            },
        )
        assert res.status_code == 200
        cert_data = res.json()
        assert cert_data["tenant_id"] == tenant_id
        assert cert_data["document_merkle_root"] == merkle_root

        # 5. Public Verification Endpoint (No auth required)
        res = await client.post(
            "/v1/zkp/verify",
            json={
                "certificate": cert_data,
                "query": query,
                "response": response,
                "expected_document_root": merkle_root,
            },
        )
        assert res.status_code == 200
        verify_data = res.json()
        assert verify_data["is_valid"] is True
        assert verify_data["status"] == "verified"
        assert verify_data["signature_valid"] is True
        assert verify_data["merkle_root_matched"] is True

        # 6. List Recent Certificates
        res = await client.get(f"/v1/tenants/{tenant_id}/zkp/certificates")
        assert res.status_code == 200
        cert_list = res.json()
        assert len(cert_list) >= 1
        assert cert_list[0]["certificate_id"] == cert_data["certificate_id"]


def test_battery_33_registration():
    """Verify Battery #33 (zkp_vector_attestation) is properly registered in BatteryService."""
    service = BatteryService()
    battery = service.get_battery("zkp_vector_attestation")
    assert battery is not None
    assert battery.id == "zkp_vector_attestation"
    assert battery.name == "Zero-Knowledge Proof (ZKP) Vector Attestation & Verifiable Document Grounding"
    assert battery.milestone == "M118 (v1.8.0-alpha1)"
    assert battery.health_check_endpoint == "/v1/zkp/health"
