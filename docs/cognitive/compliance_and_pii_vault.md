# Cognitive Architecture Deep-Dive: Enterprise Compliance Vault & GDPR Erasure Engine

**Module:** Security, Data Sovereignty & Enterprise Compliance  
**Milestone:** 88 (Phase K)  
**Version:** `v0.73.0`  

---

## 1. Regulatory Context & Enterprise Requirements

In healthcare, fintech, and enterprise operations, transmitting un-sanitized customer data or proprietary secrets to third-party LLMs violates strict data protection regulations (GDPR, HIPAA, SOC 2, PCI-DSS).

Milestone 88 delivers the **Enterprise Compliance Vault**:
1. **Multi-Category PII & Secret Redaction Engine**: Detects and sanitizes Financial data (Luhn-validated Credit Cards, IBANs), Government IDs (SSN, Aadhaar, PAN), API Secrets (AWS/OpenAI keys, JWTs), HIPAA Health records, and Network IPs.
2. **Three Masking Topologies**: Hard Redaction (`[REDACTED_FINANCIAL]`), Synthetic Masking (`**** **** **** 1234`), and Reversible Vault Pseudonymization (`[PSEUDONYM:a1b2c3d4]`).
3. **GDPR Article 17 "Right to be Forgotten" Cryptographic Erasure**: Atomic cascading purge across documents, chunks, vectors, chat logs, and cache entries with cryptographic SHA-256 certificate generation.

---

## 2. PII Detection & Masking Taxonomy

```text
[Inbound Text / Document Stream]
               │
               ▼
   [Enterprise PII Vault Filter]
               ├── Category 1: Financial (Credit Cards with Luhn Check, IBAN, SWIFT)
               ├── Category 2: Identification (SSN, Aadhaar, PAN, Passports)
               ├── Category 3: Secrets & Keys (AWS, GitHub PATs, JWTs, Private Keys)
               ├── Category 4: HIPAA Medical (MRN, Policy IDs)
               └── Category 5: Network / Contact (IPv4, IPv6, MAC, Emails, Phones)
               │
               ▼
     [Masking Mode Selection]
         ├── REDACT:        "Contact: [REDACTED_CONTACT]"
         ├── SYNTHETIC:     "Card: **** **** **** 4242"
         └── PSEUDONYMIZE:  "Client: [PSEUDONYM:x8f9a2b1]" (Vault Hash Mapped)
               │
               ▼
  [Sanitized Tokens Dispatched to LLM]
```

### Masking Modes:
1. **`MaskingMode.REDACT`**:
   Zero-information destruction. Replaces detected tokens with standardized brackets (`[REDACTED_<CATEGORY>]`), ensuring zero sensitive tokens leak to external model APIs.
2. **`MaskingMode.SYNTHETIC`**:
   Preserves formatting for downstream parsing (e.g. credit card last 4 digits) while masking sensitive prefixes.
3. **`MaskingMode.PSEUDONYMIZE`**:
   Generates a keyed HMAC-SHA256 token pseudonym (`[PSEUDONYM:<hash[:8]>]`). The original-to-pseudonym mapping is preserved in a secure, encrypted tenant vault in PostgreSQL, allowing the orchestrator to reverse pseudonyms in the final generated answer before returning it to the user.

---

## 3. GDPR Cryptographic Wipe & Certificate Generation

When an erasure request is received (`ErasureScope.DOCUMENT` or `ErasureScope.FULL_TENANT_WIPE`):
1. **Atomic Purge Transaction:**
   A single database transaction cascades across:
   - `DocumentDb` records and local storage files.
   - `DocumentChunkDb` and dense vector embeddings in PostgreSQL `pgvector`.
   - `ChatSessionDb` and `ChatMessageDb` records.
   - `InferenceLogDb` prompt/completion payloads.
   - Redis semantic cache keys matching tenant chunk hashes.
2. **Cryptographic Certificate Generation:**
   The engine computes an immutable SHA-256 signature sealing the deletion event:
   $$\text{AuditSignature} = \text{SHA256}\left( \text{tenant\_id} + \text{requester} + \text{timestamp} + \sum \text{records\_purged} + \text{SALT} \right)$$
   This emits a verifiable `ComplianceCertificateDTO` signed by the platform authority:
   ```json
   {
     "certificate_id": "cert_gdpr_719a896ff6f44ec8",
     "tenant_id": "tn_client_123",
     "requester": "compliance@enterprise.com",
     "reason": "GDPR Article 17 Erasure Request",
     "timestamp": "2026-09-04T16:00:00Z",
     "erasure_scope": "full_tenant_wipe",
     "records_purged": {
       "documents": 14,
       "chunks": 482,
       "vectors": 482,
       "chat_messages": 89,
       "cache_entries": 34
     },
     "sha256_audit_signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
   }
   ```

---

## 4. Architectural Isolation

- Domain models and enums live in `apps/api/src/domain/abstractions/compliance.py` (0 database or framework imports).
- Repository implementation `SqlComplianceRepository` handles audit logging and RLS-enforced database queries in `src/adapters/database/compliance_repository.py`.
