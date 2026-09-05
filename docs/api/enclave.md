---
id: Retriever_API_v1_enclave
title: "API Specification: Confidential Micro-Enclave KMS & Remote Attestation (/v1/admin/edge/attestation, /v1/tenants/{tenantId}/edge)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/enclave
  - security/attestation
  - security/sealing
  - platform/retriever
blast_radius: CRITICAL
security_auth: ADMIN_KEY_OR_BEARER_JWT
invariants:
  - "Challenge nonces MUST be cryptographically randomized, single-use, and expire after 300s."
  - "Key derivation MUST cryptographically bind tenant_id and PCR0 measurements via HKDF-SHA256."
  - "Unsealing MUST verify AES-256-GCM authentication tags and reject mismatched tenant AAD."
---

# API Specification: Confidential Micro-Enclave KMS & Remote Attestation (`/v1/enclave`)

#api #enclave #kms #attestation #aes_gcm #retriever

> **Authoritative REST API specification for Confidential Micro-Enclave remote attestation nonce challenges, cryptographic PCR evidence verification, AES-256-GCM memory sealing, and emergency volatile memory scrubbing (Platform Battery #21).**

---

## 1. Overview & Enclave Sealing Protocol

The Enclave API provides confidential computing primitives protecting sensitive vector payloads and tenant secrets:
- **Remote Attestation:** Issues challenge nonces to prevent replay attacks and verifies hardware signatures (Intel SGX, AMD SEV-SNP, Nitro Enclaves, Apple Secure Enclave, TPM 2.0).
- **AES-256-GCM Sealing:** Derives isolated symmetric keys via HKDF-SHA256 bound to hardware measurements, encrypting data with Additional Authenticated Data (AAD) that binds the payload to a specific `tenant_id`.

```text
  [ Client / Edge Node ]                                 [ Retriever Enclave Router ]
            │                                                         │
            │ 1. GET /v1/admin/edge/attestation/nonce                 │
            ├────────────────────────────────────────────────────────►│ (Generate 64-char Hex Nonce)
            │◄────────────────────────────────────────────────────────┤
            │                                                         │
            │ 2. POST /v1/admin/edge/attestation/verify               │
            │    { "nonce": "...", "pcr0": "...", "signature": "..." }│
            ├────────────────────────────────────────────────────────►│ (Verify Ed25519 & Trust Root)
            │◄────────────────────────────────────────────────────────┤
            │    { "is_valid": true, "trust_level": "HARDWARE_ROOTED"}│
            │                                                         │
            │ 3. POST /v1/tenants/{id}/edge/seal                      │
            │    { "plaintext_base64": "..." }                        │
            ├────────────────────────────────────────────────────────►│ (HKDF Derivation + AES-256-GCM)
            │◄────────────────────────────────────────────────────────┤
            │    { "ciphertext": "...", "iv": "...", "tag": "..." }   │
```

---

## 2. Admin Endpoints

### 2.1 Issue Attestation Challenge Nonce
* **Endpoint:** `GET /v1/admin/edge/attestation/nonce`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Query Parameters:** `ttl_seconds` (default: 300, min: 30, max: 3600).
* **Response (200 OK):**
```json
{
  "nonce": "3cffe309e530970aed48d94967dabb3ec3cba75259e1034cfa03281dfde8ac4d",
  "created_at": "2026-09-05T18:00:00Z",
  "expires_at": "2026-09-05T18:05:00Z"
}
```

### 2.2 Verify Attestation Evidence
* **Endpoint:** `POST /v1/admin/edge/attestation/verify`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Request Body:**
```json
{
  "nonce": "3cffe309e530970aed48d94967dabb3ec3cba75259e1034cfa03281dfde8ac4d",
  "pcr0": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signature": "base64_ed25519_signature_bytes...",
  "public_key": "base64_ed25519_public_key...",
  "platform": "apple_secure_enclave"
}
```
* **Response (200 OK):**
```json
{
  "is_valid": true,
  "trust_level": "HARDWARE_ROOTED",
  "verified_at": "2026-09-05T18:00:01Z",
  "platform": "apple_secure_enclave",
  "measurement_matched": true,
  "details": "Attestation signature and PCR0 measurement verified against hardware root."
}
```

### 2.3 Emergency Memory Scrub
* **Endpoint:** `POST /v1/admin/edge/enclave/purge-keys`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Immediately invokes `ctypes.memset` zeroing across all tracked volatile key buffers in memory.
* **Response (200 OK):**
```json
{
  "success": true,
  "buffers_wiped": 14,
  "bytes_zeroed": 448,
  "purged_at": "2026-09-05T18:00:02Z"
}
```

---

## 3. Tenant Endpoints

### 3.1 Seal Memory Payload (AES-256-GCM)
* **Endpoint:** `POST /v1/tenants/{tenantId}/edge/seal`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "plaintext_base64": "SGVsbG8gQ29uZmlkZW50aWFsIENvbXB1dGluZw==",
  "key_context": "vector_blob_v1"
}
```
* **Response (200 OK):**
```json
{
  "ciphertext_base64": "vW8j2L9...",
  "iv_base64": "aBcDeFgHiJkL",
  "tag_base64": "128bitAuthTagBase64==",
  "tenant_id": "c7a8b9c0-1234-5678-90ab-cdef12345678",
  "cipher_suite": "AES-256-GCM",
  "sealed_at": "2026-09-05T18:00:03Z"
}
```

### 3.2 Unseal Memory Payload
* **Endpoint:** `POST /v1/tenants/{tenantId}/edge/unseal`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:** Sealed payload structure matching the output of `/seal`.
* **Response (200 OK):**
```json
{
  "plaintext_base64": "SGVsbG8gQ29uZmlkZW50aWFsIENvbXB1dGluZw==",
  "unsealed_at": "2026-09-05T18:00:04Z",
  "integrity_verified": true
}
```
