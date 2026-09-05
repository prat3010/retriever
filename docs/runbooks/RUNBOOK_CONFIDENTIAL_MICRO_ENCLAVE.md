# Operational Runbook: Confidential Micro-Enclave Encryption & Hardware KMS Remote Attestation

**Runbook ID:** RB-OPS-101  
**Audience:** Security Architects, Cryptographic Operations Engineers, Cloud SREs  
**Applies to:** Retriever AI Engine (v0.86.0+, Milestone 101)  
**Platform Battery:** Battery #21 (`confidential_micro_enclave`)  

---

## 1. System Overview & Cryptographic Flow

The Confidential Micro-Enclave architecture isolates sensitive tenant vector payloads, proprietary document embeddings, and model weights within hardware-isolated execution environments (Intel SGX, AMD SEV-SNP, AWS Nitro Enclaves, Apple Secure Enclave, TPM 2.0).

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    CONFIDENTIAL ATTESTATION & SEALING FLOW                  │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        │ 1. GET /v1/admin/edge/attestation/nonce
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         ATTESTATION NONCE ISSUANCE                          │
 │  • 64-hex-char cryptographic nonce (TTL 300s, single-use, anti-replay)      │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        │ 2. POST /v1/admin/edge/attestation/verify
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                     REMOTE HARDWARE ATTESTATION VERIFIER                    │
 │  • Asserts Ed25519 Hardware Signature, Root CA Chain, and PCR0 Registers    │
 │  • Trust Level: HARDWARE_ROOTED | EMULATED_DEVELOPMENT                      │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        │ 3. POST /v1/tenants/{tenantId}/edge/seal
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                    AES-256-GCM MEMORY SEALING (HKDF-SHA256)                 │
 │  • Key derived from Hardware Root + Salt(PCR0) + Info(TenantID)             │
 │  • Immediate volatile key buffer zeroing via ctypes.memset                   │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Health Monitoring & Verification Commands

### 2.1 Verify Enclave Platform & Battery Status
Confirm that Battery #21 is operational and inspect the active hardware isolation platform:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/admin/edge/attestation/status | jq .
```

**Expected Output:**
```json
{
  "battery_id": "confidential_micro_enclave",
  "status": "active",
  "hardware_platform": "APPLE_SECURE_ENCLAVE",
  "attestation_trust_level": "HARDWARE_ROOTED",
  "cipher_suite": "AES_256_GCM_HKDF_SHA256",
  "total_sealed_payloads": 84,
  "last_memory_wipe_timestamp": null
}
```

---

## 3. Standard Operational Procedures (SOPs)

### SOP-ENCLAVE-01: Verifying Remote Hardware Attestation

1. Request an anti-replay challenge nonce:
   ```bash
   NONCE_RESP=$(curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     https://rag.prateeq.in/v1/admin/edge/attestation/nonce)
   NONCE=$(echo "$NONCE_RESP" | jq -r .nonce)
   ```
2. Gather hardware evidence and verify attestation:
   ```bash
   curl -X POST "https://rag.prateeq.in/v1/admin/edge/attestation/verify" \
     -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d "{
       \"nonce\": \"$NONCE\",
       \"platform\": \"APPLE_SECURE_ENCLAVE\",
       \"pcr0_measurement\": \"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\",
       \"hardware_signature\": \"3045022100...\"
     }" | jq .
   ```

### SOP-ENCLAVE-02: Sealing Sensitive Tenant Vectors / BLOBs

Encrypt in-memory vectors or sensitive tenant secrets with tenant-bound AAD:

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/$TENANT_ID/edge/seal" \
  -H "Authorization: Bearer $TENANT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "plaintext": "proprietary_vector_data_or_api_secret",
    "associated_data": "retriever:tenant:8f3b2810:document:doc_01"
  }' | jq .
```

### SOP-ENCLAVE-03: Emergency Volatile Memory Wipe

In the event of suspected hardware tamper, side-channel intrusion, or physical breach of an edge node:

```bash
curl -X POST "https://rag.prateeq.in/v1/admin/edge/enclave/wipe" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Suspected side-channel cache probe anomaly on edge host",
    "force_immediate_exit": false
  }' | jq .
```
This triggers an atomic in-place `ctypes.memset(0)` across all allocated volatile key memory buffers.

---

## 4. Incident Triage & Cryptographic Alert Matrix

| Alert / Error Code | Root Cause Analysis | Remediation Action |
| :--- | :--- | :--- |
| **`400 Invalid Nonce / Replay Attack`** | Nonce expired (>300s) or attempted reuse of a single-use token. | Re-issue a fresh nonce via `SOP-ENCLAVE-01`. Investigate network latency or replay probes. |
| **`400 PCR0 Tamper Mismatch`** | Running binary checksum does not match expected secure enclave PCR0 hash. | **CRITICAL SECURITY EVENT:** Host operating system, hypervisor, or container image has been altered. Quarantine host immediately. |
| **`InvalidTag Decryption Failure`** | Ciphertext was altered in transit/storage, or tenant AAD does not match original sealing tenant ID. | Cross-tenant decryption attempt blocked. Log security incident and verify tenant authorization boundaries. |

---

## 5. Automated Verification

Execute full cryptographic enclave and remote attestation automated tests:

```bash
pytest apps/api/tests/test_enclave.py -v
```
