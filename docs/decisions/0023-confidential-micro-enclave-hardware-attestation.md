# ADR-023: Zero-Trust Micro-Enclave Encryption & Hardware KMS Remote Attestation

**Status:** Accepted  
**Date:** 2026-09-05  
**Deciders:** Principal Security Architects, Confidential Computing Engineers, Cryptographic Operations Leads  
**Consulted:** Sovereign Edge Teams, Compliance Officers, Platform Tenants  
**Informed:** Enterprise Clients, Open-Source Community  

---

## 1. Context and Problem Statement

As Retriever expanded to support sovereign edge runtimes (Milestone 98), multi-cloud distributed failover (Milestone 99), and local audio edge processing (Milestone 100), vector databases, cached chunks, and tenant-scoped knowledge documents are frequently stored and processed on client hardware, branch office nodes, or edge VPS instances.

In distributed deployments, host operating systems and physical infrastructure cannot be inherently trusted:
1. **Host RAM Probing & Cold-Boot Dumping:** An untrusted hypervisor, cloud infrastructure root administrator, or physical thief could dump volatile RAM to extract cryptographic keys and raw plaintext embeddings.
2. **Static Encryption-at-Rest Vulnerabilities:** Traditional encryption solutions relying on static master keys in environment variables (`KEY_ENCRYPTION_KEY`) expose all tenant data if the host filesystem or process environment is compromised.
3. **Cross-Tenant Ciphertext Transplanting:** In multi-tenant environments without cryptographic tenant binding, an attacker could attempt to transplant encrypted BLOBs between tenant databases.
4. **Lack of Hardware Remote Attestation:** Without cryptographically verified hardware root-of-trust evidence, external orchestrators cannot verify whether an edge node is running genuine, untampered software within an isolated execution environment (Intel SGX, AMD SEV-SNP, AWS Nitro Enclaves, Apple Secure Enclave, or TPM 2.0).

To eliminate these vulnerabilities, Retriever required **Platform Battery #21: Zero-Trust Micro-Enclave Encryption & Hardware KMS Remote Attestation** (Milestone 101, `v0.86.0`), inaugurating **Phase M: Sovereign Edge Swarm & Confidential Zero-Trust Computing**.

---

## 2. Decision Drivers

- **Hardware-Rooted Confidentiality Invariant:** Edge vector BLOBs, SQLite database files, and sensitive tenant documents must be cryptographically sealed with hardware-derived keys, ensuring root admins and cloud operators cannot inspect tenant data.
- **Anti-Replay Remote Attestation:** Challenge-response attestation using cryptographically generated single-use nonces and vendor root-of-trust signatures (Ed25519) to prove enclave authenticity before issuing secrets.
- **Strict Tenant & Platform Binding (AAD):** AES-256-GCM authenticated encryption must bind `tenant_id` and the platform measurement (`PCR0`/`MRENCLAVE`) as Additional Authenticated Data (AAD), mathematically preventing cross-tenant decryption or replay on modified enclave images.
- **Zero-Knowledge Ephemeral RAM Hygiene:** Symmetric keys derived in memory must be held exclusively in mutable buffers and aggressively scrubbed via `ctypes.memset` immediately after cryptographic sealing, complemented by OS signal traps (`SIGTERM`, `SIGINT`) on process shutdown.
- **Hexagonal Architecture Boundaries:** The domain layer (`src/domain/abstractions/enclave.py`) must remain pure Pydantic with zero cryptography or framework imports, while all ciphers, nonces, and memory sanitizers reside strictly in `src/adapters/security/`.

---

## 3. Considered Options

### Option 1: Static Symmetric AES-256 Field Encryption (Fernet / AES-CBC)
- *Pros:* Simple implementation using existing `KEY_ENCRYPTION_KEY`.
- *Cons:* No hardware attestation; static keys remain vulnerable to memory dumping; no cryptographic platform measurement binding; does not protect against root hypervisor attacks.

### Option 2: Cloud-Only KMS Delegation (AWS KMS / Google Cloud KMS)
- *Pros:* Offloads key management to managed cloud services.
- *Cons:* Violates the air-gapped sovereign edge requirement; requires continuous Internet connectivity; introduces per-call cloud latency (~50–150ms); compromises zero-cloud-dependency guarantees.

### Option 3: Hexagonal Hardware-Rooted Enclave Adapter with HKDF-SHA256, AES-256-GCM Sealing & Volatile RAM Sanitizer (Chosen)
- *Pros:*
  - **Local Air-Gapped Operation:** Operates autonomously on local edge hardware with sub-millisecond key derivation.
  - **Hardware Root of Trust:** Automatically senses underlying hardware platform (`apple_secure_enclave`, `intel_sgx`, `amd_sev`, `aws_nitro`, `tpm2`, or `simulated_hsm`).
  - **Cryptographic Attestation:** Nonce-based challenge-response protocol with Ed25519 digital signatures and PCR0 platform hash verification.
  - **Active Zero-Knowledge Sanitization:** In-memory key tracking with `ctypes.memset` zeroing and OS termination traps.
  - **Zero Incremental Cost:** Pure mathematical cryptography without third-party SaaS charges.

---

## 4. Decision Outcome

We selected **Option 3**. The confidential micro-enclave and hardware remote attestation architecture was implemented as follows:

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
│                  ▼                                                                     │
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

### Mathematical & Cryptographic Formulations

#### 1. Tenant Key Derivation via HKDF-SHA256
From the enclave root master seed $K_{\text{master}}$ and the platform measurement $\text{PCR0}$, each tenant receives an isolated 256-bit symmetric key $K_{\text{tenant}}$:

$$\text{PRK} = \text{HMAC-SHA256}(\text{Key} = \text{PCR0}, \text{Data} = K_{\text{master}})$$

$$K_{\text{tenant}} = \text{HMAC-SHA256}(\text{Key} = \text{PRK}, \text{Data} = \text{"retriever:enclave:tenant:"} \parallel \text{tenant\_id} \parallel \text{":v1"} \parallel \text{0x01})$$

#### 2. Authenticated AES-256-GCM Sealing with Additional Authenticated Data (AAD)
For plaintext payload $P$, random 96-bit initialization vector $\text{IV} \leftarrow \{0, 1\}^{96}$, and bound authenticated data $\text{AAD} = \text{tenant\_id} \parallel \text{":"} \parallel \text{PCR0} \parallel \text{":"} \parallel \text{custom\_aad}$:

$$(C, T) = \text{AES-GCM-Encrypt}(K_{\text{tenant}}, \text{IV}, P, \text{AAD})$$

Decryption strictly asserts tag validity $T$: if an attacker alters $C$, attempts cross-tenant decryption with a different $\text{tenant\_id}$, or executes on an untrusted enclave with mismatched $\text{PCR0}$, decryption fails with `InvalidTag`.

#### 3. Remote Attestation Signature
For challenge nonce $N$ issued by the verifier and platform measurement $\text{PCR0}$:

$$\sigma = \text{Ed25519-Sign}(SK_{\text{enclave}}, N \parallel \text{":"} \parallel \text{PCR0})$$

---

## 5. Implementation Summary

1. **Domain Abstractions (`src/domain/abstractions/enclave.py`):**
   - Pure protocols: `HardwareAttestationProtocol`, `EnclaveKeySealerProtocol`, `MemorySanitizerProtocol`.
   - Data contracts: `AttestationNonce`, `AttestationEvidence`, `EnclaveVerificationReport`, `EnclaveSealedPayload`, `EnclaveSealRequest`, `EnclaveUnsealRequest`, `EnclaveUnsealResponse`.
2. **Hardware Enclave Adapter (`src/adapters/security/enclave_adapter.py`):**
   - Implements remote attestation, Ed25519 digital signing, challenge nonce lifecycle management, and AES-256-GCM sealing with HKDF-SHA256.
3. **Memory Sanitizer Adapter (`src/adapters/security/memory_sanitizer.py`):**
   - In-memory volatile key storage with `ctypes.memset` zeroing and `SIGTERM`/`SIGINT` traps.
4. **Platform Battery #21 (`src/domain/batteries/battery_service.py`):**
   - Registered `zero_trust_micro_enclave` in `BatteryService` under `SAFETY_DEFENSE`.
5. **FastAPI Endpoints (`src/routers/enclave.py`):**
   - Administrative attestation endpoints (`/v1/admin/edge/attestation/*`) and tenant sealing endpoints (`/v1/tenants/{tenantId}/edge/seal` and `/unseal`).
6. **Retriever Admin Dashboard UI (`apps/web/src/app/(dashboard)/edge/page.tsx`):**
   - Added interactive Confidential Micro-Enclave card, PCR0 inspector, attestation challenge tester, emergency memory wipe, and live AES-256-GCM sealing playground.

---

## 6. Verification and Validation

- **Automated Test Suite:** `apps/api/tests/test_enclave.py` passes 8/8 comprehensive unit and REST integration tests.
- **Platform Batteries:** `apps/api/tests/test_batteries.py` asserts all 21 platform batteries pass cleanly.
- **Hexagonal Conformance:** `apps/api/tests/test_architecture.py` asserts 0 forbidden framework imports and router container isolation.
- **Web UI:** `retriever/apps/web` compiles cleanly in Next.js 16 with Turbopack (19/19 routes static/dynamic).
