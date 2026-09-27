# Sovereign Air-Gapped Appliance & Embedded Edge Engine (Platform Battery #41)

**Milestone:** M127 (v2.5.0)  
**Status:** Production Ready  
**Category:** Edge Distribution & Hardware Security  
**Latency Profile:** <15ms (Search) / <350ms (Full-Duplex Voice RAG)  
**Platform Battery:** #41 (`sovereign_air_gapped_appliance`)

---

## 1. Executive Summary & Problem Space

Regulated enterprise operators—including defense agencies, critical infrastructure SCADA environments, maritime and offshore tactical outposts, intelligence communities, and sovereign banking enclaves—operate under strict physical and logical **air-gap mandates**.

In these environments:
1. **Zero Internet Egress:** Systems must not connect to external SaaS APIs, remote CDNs, or cloud vector databases.
2. **Physical Capture & Tamper Protection:** Devices deployed to field edge locations face extraction risk. On-disk vector indices, document chunks, and embeddings must be cryptographically sealed to host silicon hardware roots of trust (TPM 2.0 / Apple Secure Enclave).
3. **Autonomous Self-Sufficiency:** The system must run completely self-contained with embedded storage (SQLite FTS5 + Vector BLOBs) and local neural voice models (Whisper ASR + Piper TTS) with zero external microservice dependencies.

Milestone 127 delivers an end-to-end, enterprise-grade sovereign appliance that meets all these requirements while adhering strictly to Retriever's Hexagonal Architecture and Zero-Toy utility invariants.

---

## 2. Core Architecture & Component Hierarchy

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      Sovereign Edge Physical Host                      │
 │   ┌───────────────────────────┐      ┌──────────────────────────────┐  │
 │   │ Hardware Root of Trust    │      │ Zero-Egress Network Sentinel │  │
 │   │ (TPM 2.0 PCRs / Enclave)  │      │ (Socket Audit & Fail-Closed) │  │
 │   └─────────────┬─────────────┘      └──────────────┬───────────────┘  │
 └─────────────────┼───────────────────────────────────┼──────────────────┘
                   │                                   │
                   │ Hardware Key Derivation (HKDF)    │ Zero Outbound Verification
                   ▼                                   ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │            Sovereign Air-Gapped Appliance Core (Retriever)             │
 │                                                                        │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Hardware Vector Sealer (AES-256-GCM + AAD Binding)               │  │
 │  │   • Encrypts/Decrypts on-disk SQLite vector database files       │  │
 │  │   • Validates PCR measurements; instant wipe on tamper detection │  │
 │  └──────────────────────────────┬───────────────────────────────────┘  │
 │                                 │ Unsealed in-memory / tmpfs           │
 │                                 ▼                                      │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Embedded SQLite Vector & FTS5 Engine (sqlite_edge_engine.py)     │  │
 │  │   • Sublinear Okapi BM25 keyword search via FTS5 virtual table   │  │
 │  │   • Cosine similarity nearest-neighbor over vector BLOBs         │  │
 │  │   • Reciprocal Rank Fusion (RRF) candidate ranking               │  │
 │  └──────────────────────────────▲───────────────────────────────────┘  │
 │                                 │                                      │
 │                                 │ Search & Context                     │
 │                                 │                                      │
 │  ┌──────────────────────────────┴───────────────────────────────────┐  │
 │  │ Offline Full-Duplex Voice RAG Engine (voice_rag_engine.py)       │  │
 │  │   [Mic / Audio In] ──► Whisper.cpp ASR (VAD Endpointing)         │  │
 │  │                    ──► Sovereign Hybrid Retrieval                │  │
 │  │                    ──► Local SLM Synthesis (Qwen / Llama)        │  │
 │  │                    ──► Piper Neural TTS (PCM16 Audio Chunks)     │  │
 │  │                    ──► [Audio Out + Grounded Citations]          │  │
 │  └──────────────────────────────────────────────────────────────────┘  │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Cryptographic Hardware Vector Sealing

### Mathematical Key Derivation
Keys are never stored in plaintext on disk. They are derived ephemerally via HKDF-SHA256:

$$\text{Key} = \text{HKDF-Extract-and-Expand}(PRK=\text{MasterSeed},\, \text{Salt}=\text{PCR0},\, \text{Info}=\text{"retriever:vector\_sealer:"} \parallel \text{TenantID},\, L=32)$$

### Authenticated Encryption & AAD Binding
On-disk SQLite vector stores are sealed using authenticated AES-256-GCM. The Associated Authenticated Data (AAD) binds the ciphertext cryptographically to both the `tenant_id` and the silicon hardware measurement:

$$\text{AAD} = \text{JSON}(\{\text{"tenant\_id"}: T,\, \text{"pcr\_measurement"}: \text{PCR0}\})$$

$$C,\, \text{Tag} = \text{AES-256-GCM-Encrypt}(\text{Key},\, \text{Nonce}_{96},\, P_{\text{SQLite}},\, \text{AAD})$$

### Tamper Detection & Fail-Fast Locking
If the vector file is moved to another physical host, if the host firmware/kernel changes (altering PCR0), or if a single bit of ciphertext or metadata is modified:
1. `HardwareSealingTamperError` is immediately raised.
2. The derived symmetric key is scrubbed in-place using `EphemeralMemorySanitizer.sanitize_buffer()`.
3. The database file remains locked in ciphertext.

---

## 4. Zero-Egress Network Sentinel (Fail-Closed)

The `AirgapNetworkSentinel` continuously verifies that the appliance runtime operates in 100% network isolation:
1. **Socket Auditing:** Checks active socket bindings against `LOOPBACK_HOSTS` (`127.0.0.1`, `localhost`, `::1`).
2. **DNS Resolver Inspection:** Audits `/etc/resolv.conf` to guarantee no external public WAN resolvers (such as `8.8.8.8` or `1.1.1.1`) are configured.
3. **Fail-Closed Egress Enforcement:** Any outbound network socket targeting external WAN IPs raises `AirgapEgressViolationError` and transitions system status to `AirgapNetworkState.EGRESS_VIOLATION_DETECTED`.

---

## 5. Offline Full-Duplex Neural Voice RAG

The `SovereignVoiceRAGEngine` enables hands-free voice interactions for operators in the field:
1. **Audio Ingress & VAD:** Ingests raw PCM16/WAV audio frames. The Whisper transcription adapter computes RMS energy and zero-crossing rates for endpointing.
2. **Local ASR:** Transcribes query via local Whisper model with zero cloud calls.
3. **Embedded Hybrid Retrieval:** Executes BM25 keyword matching via SQLite FTS5 and vector similarity scoring.
4. **Local SLM Generation:** Composes grounded tactical answers backed by local document citations.
5. **Neural Speech Synthesis:** Generates high-fidelity PCM16 audio chunks using Piper TTS with sub-350ms total conversational latency.

---

## 6. REST API Endpoints

| Endpoint | Method | Role | Description |
|---|---|---|---|
| `/v1/appliance/status` | `GET` | Admin | Comprehensive status, hardware attestation, sealing states, and model inventory. |
| `/v1/appliance/network/audit` | `POST` | Admin | Triggers on-demand zero-egress network isolation audit. |
| `/v1/appliance/manifest` | `GET` | Admin | Exports distroless build manifest and model checksums. |
| `/v1/appliance/tenants/{tenantId}/seal` | `POST` | Tenant/Admin | Hardware-seals on-disk SQLite vector store with AES-256-GCM. |
| `/v1/appliance/tenants/{tenantId}/unseal` | `POST` | Tenant/Admin | Unseals encrypted database verifying host PCR measurements. |
| `/v1/appliance/tenants/{tenantId}/voice/query` | `POST` | Tenant/Admin | Executes offline voice query: Audio in $\to$ ASR $\to$ Search $\to$ TTS $\to$ Audio out. |

---

## 7. Platform Battery #41 Registration

Platform Battery #41 is registered in `BatteryService` under `BatteryCategory.EDGE_DISTRIBUTION`:

```python
PlatformBatteryDTO(
    id="sovereign_air_gapped_appliance",
    name="Sovereign Air-Gapped Appliance & Hardware Vector Sealing",
    category=BatteryCategory.EDGE_DISTRIBUTION,
    status=BatteryStatus.ACTIVE,
    algorithm_foundation="TPM 2.0 / Apple Secure Enclave AES-256-GCM Hardware Vector Sealing & Zero-Egress Network Sentinel",
    milestone="M127 (v2.5.0)",
    latency_profile="<15ms (Search) / <350ms (Voice RAG)",
    description="Self-contained sovereign edge appliance bundling embedded SQLite vector/FTS5 indexing, hardware-bound AES-256-GCM vector sealing, fail-closed zero-egress network enforcement, and offline full-duplex Whisper/Piper neural voice RAG.",
    active_parameters={
        "sealing_cipher": "aes_256_gcm",
        "zero_egress_strict": True,
        "hardware_roots": ["tpm2_pcr", "apple_secure_enclave", "linux_keyring"],
        "voice_asr_engine": "whisper_cpp",
        "voice_tts_engine": "piper_neural",
        "embedded_storage": "sqlite_fts5_vector",
        "distroless_ready": True,
        "zero_toy_verified": True,
    },
    health_check_endpoint="/v1/appliance/status",
)
```
