---
id: Retriever_API_v1_security_compression
title: "API Specification: Context Compression & Envelope Encryption (/v1/security-compression)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/security-compression
  - cognitive/longllmlingua
  - security/aes-256-gcm
  - platform/retriever
blast_radius: HIGH
security_auth: BEARER_JWT
invariants:
  - "Zero-trust envelope encryption MUST use AES-256-GCM with 96-bit random IV."
  - "Prompt compression target ratio MUST be bounded between 0.2 and 0.8."
---

# API Specification: Context Compression & Envelope Encryption (`/v1/security-compression`)

#api #compression #security #encryption #longllmlingua #aes256 #retriever

> **Authoritative specification for LongLLMLingua prompt token compression and Zero-Trust AES-256-GCM Envelope Encryption.**

---

## 1. Security & Token Compression Pipeline

```mermaid
flowchart LR
    Prompt[Raw Long Context Prompt 12k Tokens] --> Comp[LongLLMLingua Perplexity Filter]
    Comp --> Reduced[Compressed Prompt 4k Tokens (66% Savings)]
    
    Data[Sensitive PII / Confidential Data] --> Enc[AES-256-GCM Master Key]
    Enc --> Cipher[Encrypted Blob + Auth Tag + IV]
```

---

## 2. API Endpoints

### 2.1 Compress Context Prompt

- **HTTP Method:** `POST`
- **Path:** `/v1/tenants/{tenantId}/compress`
- **Authentication:** `Bearer <TOKEN>`
- **Request Body:**
```json
{
  "context": "Comprehensive legal contract with extensive boilerplate text...",
  "targetRatio": 0.4,
  "question": "What is the non-compete duration?"
}
```

#### Response Schema (`200 OK`)
```json
{
  "originalTokens": 2400,
  "compressedTokens": 960,
  "compressionRatio": 0.40,
  "tokensSaved": 1440,
  "compressedText": "Non-compete duration: 24 months post termination."
}
```

---

## 🔗 Related Architecture & Cross-References
- [Context Compression Deep-Dive](../cognitive/context_compression.md)
- [Storage & Zero-Trust Envelope Encryption](../infrastructure/storage_and_encryption.md)
