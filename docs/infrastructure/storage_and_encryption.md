---
id: DeepDive_Storage_Encryption_Envelope
title: "Infrastructure Deep-Dive: S3 Object Storage, HMAC URLs & Zero-Trust Envelope Encryption"
tier: 7_async_infrastructure
platform: retriever
tags:
  - infra/storage
  - s3
  - security/aes-256-gcm
  - platform/retriever
blast_radius: CRITICAL
security_auth: SERVICE_ROLE
invariants:
  - "Master Key Encryption Key (KEK) MUST be stored in hardware KMS or secure environment secrets."
  - "Each document MUST be encrypted with a unique Data Encryption Key (DEK)."
---

# Infrastructure Deep-Dive: S3 Object Storage, HMAC URLs & Zero-Trust Envelope Encryption

#infra #storage #s3 #encryption #aes256 #envelope #security #retriever

> **Technical architecture, envelope encryption key lifecycle, S3/R2 storage adapters, and HMAC-signed presigned download URLs.**

---

## 1. Envelope Encryption Lifecycle

Retriever implements standard 2-tier Zero-Trust Envelope Encryption for all confidential document storage:

```mermaid
flowchart TD
    KMS[(KMS / Master KEK)] -->|Wrap / Unwrap| DEK[Unique Data Encryption Key]
    
    Doc[Raw Document Binary] --> Enc[AES-256-GCM Encryption]
    DEK --> Enc
    
    Enc --> EncBlob[Encrypted Ciphertext Blob]
    Enc --> Tag[128-bit Auth Tag]
    Enc --> IV[96-bit Random IV]
    
    EncBlob & Tag & IV --> S3[(AWS S3 / Cloudflare R2 / Local FS)]
```

---

## 2. Presigned Download URL Signature Formula

Download URLs are secured via HMAC-SHA256 signatures with deterministic timestamp expiration:

\[
\text{Signature} = \operatorname{HMAC-SHA256}\left(K_{\text{tenant}}, \text{DocID} \oplus \text{ExpiresTimestamp}\right)
\]

---

## 🔗 Related Architecture & Cross-References
- [Document API Specification](../api/document.md)
- [Security & Compression Specification](../api/security_compression.md)
