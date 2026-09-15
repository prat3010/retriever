# Zero-Knowledge Proof (ZKP) Vector Attestation & Verifiable Document Grounding

> **Platform Battery:** #33 (`zkp_vector_attestation`)  
> **Category:** `SAFETY_DEFENSE`  
> **Milestone:** M118 (`v1.8.0-alpha1`)  
> **Health Check Endpoint:** `GET /v1/zkp/health`  

---

## 1. Architectural Overview

The **Zero-Knowledge Proof (ZKP) Vector Attestation** engine provides cryptographic proof of document provenance, chunk inclusion, and tamper-evident grounding for mission-critical RAG inferences:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT MERKLE TREE COMMITMENT                   │
│                                                                        │
│                      👑 Document Root Commitment (R_doc)               │
│                                 /               \                      │
│                          N_parent_0           N_parent_1               │
│                          /        \           /        \               │
│                        h_0        h_1       h_2        h_3             │
│                                                                        │
│    h_i = SHA256(tenant_id || document_id || chunk_index || content_hash)│
├────────────────────────────────────────────────────────────────────────┤
│                   GROUNDING CERTIFICATE ISSUANCE (Ed25519)             │
│                                                                        │
│    Query Turn ──► SHA256(query)    \                                   │
│    Response   ──► SHA256(response)  ──► Canonical Payload ──► Ed25519  │
│    Citations  ──► Merkle Paths π_i /                           Sign    │
├────────────────────────────────────────────────────────────────────────┤
│                 PUBLIC ZERO-KNOWLEDGE VERIFIER (POST /v1/zkp/verify)   │
│                                                                        │
│   1. Turn Integrity (Query & Response Hashes Match)                    │
│   2. Merkle Path Reconstruction (Leaf hashes up to R_doc)              │
│   3. Document Root Commitment Match (R_computed == R_registered)       │
│   4. Digital Signature Authenticity (Ed25519 Public Key Verification)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts

### 1. Deterministic Binary Merkle Trees
- **Leaf Commitment:** Each document chunk $c_i$ is hashed into an immutable leaf commitment:
  $$h_i = \text{SHA256}(\text{tenant\_id} \mathbin{\Vert} \text{document\_id} \mathbin{\Vert} \text{chunk\_index} \mathbin{\Vert} \text{chunk\_sha256})$$
- **Balanced Tree Construction:** Odd leaf counts are duplicated at each level (standard RFC 6962 Certificate Transparency padding) to construct a complete binary DAG.
- **Root Commitment ($R_{\text{doc}}$):** The 256-bit root hash represents the cryptographic fingerprint of the entire document chunk collection.

### 2. Sub-Millisecond Merkle Inclusion Proofs ($\pi_i$)
- For each cited chunk, an authentication path $\pi_i = [(\text{sibling}_k, \text{direction}_k)]$ of length $\lceil \log_2 N \rceil$ is generated.
- Allows third-party verifiers to mathematically reconstruct the root in $<0.1\text{ms}$ without receiving other sibling chunks or confidential document text.

### 3. Ed25519-Signed Grounding Certificates
- Binds conversation turn hashes (`query_hash`, `response_hash`), similarity bounds ($\ge \tau$), cited chunk commitments, and timestamp.
- Cryptographically signed by Retriever's authorized Curve25519 authority keypair (`Ed25519-SHA512`).

### 4. Zero-Knowledge Verifiability
- **The Zero-Knowledge Property:** The certificate token contains only cryptographic hashes, Merkle paths, and digital signatures.
- Verifiers, regulators, and insurance auditors can confirm that an answer was faithfully grounded in registered document policy **without ever reading the underlying confidential text**.

---

## 3. REST API Reference

| Method | Path | Description | Auth Required |
|:---|:---|:---|:---:|
| `GET` | `/v1/zkp/health` | Battery #33 operational health & public key | No |
| `POST` | `/v1/tenants/{tenantId}/zkp/merkle-root/{documentId}` | Compute/retrieve document Merkle root commitment | Yes |
| `POST` | `/v1/tenants/{tenantId}/zkp/proof/chunk/{chunkId}` | Generate Merkle inclusion proof for chunk | Yes |
| `POST` | `/v1/tenants/{tenantId}/zkp/attest` | Issue Ed25519 Grounding Certificate token | Yes |
| `POST` | `/v1/zkp/verify` | Public zero-knowledge certificate verification | **No (Public)** |
| `GET` | `/v1/tenants/{tenantId}/zkp/certificates` | List tenant compliance certificate audit trail | Yes |

---

## 4. Decoupled Client SDK Examples

### TypeScript (`@prat3010/retriever-client`)
```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  apiKey: "ret_live_...",
  baseUrl: "https://rag.prateeq.in",
  tenantId: "tn_enterprise_01",
});

// 1. Verify Grounding Certificate
const result = await client.verifyGroundingCertificate({
  certificate: groundingCert,
  query: "What is the system SLA?",
  response: "Section 1.1 guarantees 99.99% monthly availability.",
});

console.log("Grounding Verified:", result.is_valid); // true
console.log("Status:", result.status); // "verified"
console.log("Execution Latency:", result.execution_time_ms, "ms"); // 0.32 ms
```

### Python (`retriever-python`)
```python
from retriever import RetrieverClient

client = RetrieverClient(
    api_key="ret_live_...",
    base_url="https://rag.prateeq.in",
    tenant_id="tn_enterprise_01",
)

# 1. Public Zero-Knowledge Verification
report = await client.verify_grounding_certificate(
    certificate=cert_dict,
    query="What is the arbitration venue?",
    response_text="Zurich, Switzerland.",
)

assert report["is_valid"] is True
assert report["status"] == "verified"
```
