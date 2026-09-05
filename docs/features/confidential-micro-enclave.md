# Confidential Micro-Enclave Encryption & Hardware KMS Remote Attestation

**Milestone:** M101 (v0.86.0)  
**System Layer:** Confidential Computing & Zero-Trust Security (Platform Battery #21)  
**Architecture:** Hexagonal Domain Protocols + Hardware Enclave Detection + Anti-Replay Nonce Attestation + HKDF-SHA256 Key Derivation + Authenticated AES-256-GCM Sealing + Zero-Knowledge Volatile RAM Sanitization  

---

## 1. Executive Summary

Milestone 101 delivers **Platform Battery #21: `zero_trust_micro_enclave`**, inaugurating **Phase M: Sovereign Edge Swarm & Confidential Zero-Trust Computing** of the Retriever platform.

Prior to Milestone 101, data at rest could be encrypted using static keys, but volatile runtime memory and physical hardware remained exposed to untrusted hypervisors, cloud root administrators, cold-boot RAM dump probes, and multi-tenant ciphertext transplanting attacks.

Milestone 101 eliminates these physical and cloud infrastructure vulnerabilities by introducing:
1. **Hardware-Rooted Confidential Enclave Isolation:** Automatic detection and binding to hardware execution environments:
   - Intel SGX (Software Guard Extensions)
   - AMD SEV-SNP (Secure Encrypted Virtualization)
   - AWS Nitro Enclaves
   - Apple Secure Enclave
   - Hardware TPM 2.0 (`/dev/tpmrm0`)
   - High-assurance software HSM simulation fallback
2. **Cryptographic Anti-Replay Remote Attestation:** Nonce-based challenge-response protocol signing evidence with asymmetric Ed25519 hardware identity keys, validating PCR0/MRENCLAVE platform integrity against trusted root hashes.
3. **Per-Tenant HKDF-SHA256 Key Isolation:** Mathematical key derivation binding each tenant's symmetric key to both the enclave root secret and the platform's measurement hash ($\text{PCR0}$).
4. **Authenticated AES-256-GCM Memory Sealing:** High-performance AEAD encryption using unique 96-bit random initialization vectors and 128-bit authentication tags, embedding `tenant_id` and PCR measurements into Additional Authenticated Data (AAD) to permanently eliminate cross-tenant data transplanting.
5. **Zero-Knowledge Ephemeral RAM Sanitization:** Strict memory hygiene where symmetric keys are stored in mutable `bytearray` buffers and actively zeroed via `ctypes.memset` immediately after cryptographic operations, reinforced by `SIGTERM` and `SIGINT` termination hooks.
6. **Retriever Admin Edge Cockpit:** Operational status inspection, live PCR0 measurement display, remote attestation challenge runner, emergency memory purging, and an interactive AES-256-GCM sealing playground.

---

## 2. Technical Architecture & Component Flow

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   MILESTONE 101 CONFIDENTIAL ENCLAVE ARCHITECTURE                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ External Client / Edge Agent ]                                                     │
│                │                                                                       │
│                │ 1. GET /v1/admin/edge/attestation/nonce (Challenge Request)          │
│                ▼                                                                       │
│   ┌─────────────────────────────┐                                                      │
│   │   FastAPI Router: enclave   │ ── AttestationNonce (TTL 300s, Anti-Replay)          │
│   └──────────────┬──────────────┘                                                      │
│                  │                                                                     │
│                  │ 2. POST /v1/admin/edge/attestation/verify                           │
│                  ▼                                                                       │
│   ┌─────────────────────────────┐                                                      │
│   │   HardwareEnclaveAdapter    │ ── Verifies Nonce Freshness & PCR0 Hardware Signature │
│   └──────────────┬──────────────┘                                                      │
│                  │                                                                     │
│                  ▼                                                                     │
│   ┌─────────────────────────────┐                                                      │
│   │ EnclaveVerificationReport   │ ── [HARDWARE_ROOTED / SECURE_ENCLAVE / VALID]        │
│   └─────────────────────────────┘                                                      │
│                                                                                        │
│   [ Tenant Vector / BLOB Sealing ]                                                     │
│                │                                                                       │
│                │ 3. POST /v1/tenants/{tenantId}/edge/seal                              │
│                ▼                                                                       │
│   ┌─────────────────────────────┐                                                      │
│   │    HKDF-SHA256 Derivation   │ ── Salt: PCR0 Hash, Info: "retriever:tenant:{id}:v1" │
│   └──────────────┬──────────────┘                                                      │
│                  │ 4. Ephemeral Key into MemorySanitizer bytearray                     │
│                  ▼                                                                     │
│   ┌─────────────────────────────┐                                                      │
│   │     AES-256-GCM Sealer      │ ── 96-bit IV + AAD(tenant_id) + 128-bit Tag          │
│   └──────────────┬──────────────┘                                                      │
│                  │ 5. Immediate wipe / sanitize key buffer                             │
│                  ▼                                                                     │
│   ┌─────────────────────────────┐                                                      │
│   │    EnclaveSealedPayload     │ ── Tamper-proof, tenant-bound ciphertext             │
│   └─────────────────────────────┘                                                      │
│                  │                                                                     │
│                  ▼                                                                     │
│   [ SIGTERM / SIGINT Trap ] ──────► EphemeralMemorySanitizer.wipe_all() (ctypes.memset)│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical Specifications

### 3.1 Tenant Key Derivation via HKDF-SHA256
Given an enclave root seed $K_{\text{master}} \in \{0, 1\}^{256}$ and platform measurement $\text{PCR0}$:

$$\text{PRK} = \text{HMAC-SHA256}(\text{Key} = \text{PCR0}, \text{Data} = K_{\text{master}})$$

$$K_{\text{tenant}} = \text{HMAC-SHA256}(\text{Key} = \text{PRK}, \text{Data} = \text{"retriever:enclave:tenant:"} \parallel \text{tenant\_id} \parallel \text{":v1"} \parallel \text{0x01})$$

### 3.2 AES-256-GCM Authenticated Sealing
For plaintext $P \in \{0, 1\}^*$, random 96-bit $\text{IV} \leftarrow \{0, 1\}^{96}$, and bound context $\text{AAD} = \text{tenant\_id} \parallel \text{":"} \parallel \text{PCR0} \parallel \text{":"} \parallel \text{custom\_aad}$:

$$(C, T) = \text{AES-GCM-Encrypt}(K_{\text{tenant}}, \text{IV}, P, \text{AAD})$$

Decryption performs tag verification $T$. If an attacker alters the ciphertext $C$ or attempts cross-tenant decryption using a mismatched $\text{tenant\_id}$ or modified $\text{PCR0}$, verification fails with `InvalidTag` ($p < 2^{-128}$).

---

## 4. API Reference

### 4.1 Administrative Attestation Endpoints (`/v1/admin/edge/attestation`)

#### Issue Challenge Nonce
```http
GET /v1/admin/edge/attestation/nonce?ttl_seconds=300
X-Admin-Master-Key: <ADMIN_MASTER_KEY>
```
**Response (200 OK):**
```json
{
  "nonce": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "issued_at": "2026-09-05T17:30:00Z",
  "expires_at": "2026-09-05T17:35:00Z",
  "consumed": false
}
```

#### Verify Hardware Remote Attestation
```http
POST /v1/admin/edge/attestation/verify?expected_nonce=e3b0c44298fc...
X-Admin-Master-Key: <ADMIN_MASTER_KEY>
Content-Type: application/json

{
  "platform": "apple_secure_enclave",
  "nonce": "e3b0c44298fc...",
  "pcr_measurement": "a7b3c2...",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...",
  "signature": "MEYCIQD...",
  "security_version": 1,
  "metadata": {
    "hardware_arch": "arm64"
  }
}
```
**Response (200 OK):**
```json
{
  "is_valid": true,
  "trust_level": "hardware_rooted",
  "platform": "apple_secure_enclave",
  "pcr_measurement": "a7b3c2...",
  "signer_identity": "ed25519_node_root",
  "verified_at": "2026-09-05T17:30:01Z",
  "details": {
    "status": "Attestation verified successfully",
    "security_version": 1,
    "hardware_arch": "arm64"
  }
}
```

#### Self-Attestation Report
```http
GET /v1/admin/edge/attestation/report
X-Admin-Master-Key: <ADMIN_MASTER_KEY>
```

#### Emergency In-Memory Key Wipe
```http
POST /v1/admin/edge/enclave/purge-keys
X-Admin-Master-Key: <ADMIN_MASTER_KEY>
```

### 4.2 Tenant Memory Sealing Endpoints (`/v1/tenants/{tenantId}/edge`)

#### Seal Tenant Data
```http
POST /v1/tenants/{tenantId}/edge/seal
X-Admin-Master-Key: <ADMIN_MASTER_KEY>
Content-Type: application/json

{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "plaintext": "Confidential edge vector embedding BLOB",
  "aad": "document_id:doc_8849"
}
```
**Response (200 OK):**
```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "key_id": "k_enc_00000000-0000-0000-0000-000000000001_3cffe309e5",
  "cipher_suite": "aes_256_gcm",
  "nonce_iv": "k4j2B...",
  "ciphertext": "a9Z1x...",
  "auth_tag": "q9L0m...",
  "aad": "document_id:doc_8849",
  "pcr_binding": "a7b3c2...",
  "sealed_at": "2026-09-05T17:30:02Z"
}
```

#### Unseal Tenant Data
```http
POST /v1/tenants/{tenantId}/edge/unseal
X-Admin-Master-Key: <ADMIN_MASTER_KEY>
Content-Type: application/json

{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "sealed_payload": { ... }
}
```
**Response (200 OK):**
```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "plaintext": "Confidential edge vector embedding BLOB",
  "verified_aad": true,
  "unsealed_at": "2026-09-05T17:30:03Z"
}
```

---

## 5. Verification & Test Suite

The test suite in [`apps/api/tests/test_enclave.py`](../../apps/api/tests/test_enclave.py) executes 8 comprehensive automated scenarios:
1. Domain layer purity (zero forbidden frameworks).
2. Challenge nonce generation, 300s expiration, and anti-replay invalidation.
3. Hardware attestation evidence generation and signature verification.
4. Forged signature rejection and tampered PCR detection.
5. AES-256-GCM memory sealing and unsealing roundtrip fidelity.
6. Tenant isolation and AAD bit-tampering rejection (`InvalidTag`).
7. In-place memory sanitization (`ctypes.memset`) and scoped key zeroing.
8. FastAPI REST integration endpoints.
