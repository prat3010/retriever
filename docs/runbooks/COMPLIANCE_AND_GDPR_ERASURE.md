# Operational Runbook: Enterprise Compliance Vault & GDPR Cryptographic Wipe

**Document Status:** Production-Ready  
**Milestone:** 88 (v0.73.0)  
**Target Audience:** Compliance Officers, Security Engineers, SREs & External SOC 2 / GDPR Auditors  

---

## 1. Executive Summary & Compliance Standards

The Retriever Enterprise Compliance Vault provides native, zero-footprint data protection satisfying:
- **GDPR Article 17 ("Right to be Forgotten"):** Permanent data expungement backed by cryptographic proof.
- **PCI-DSS Requirement 3:** Protection of stored cardholder data with algorithmic card validation and masking.
- **HIPAA Safe Harbor Rule (45 CFR § 164.514):** Automated de-identification of medical records and patient identifiers.
- **SOC 2 Trust Services Criteria (Common Criteria 6.1 & 6.7):** Confidentiality, credential redaction, and data retention enforcement.

---

## 2. Context-Aware PII Anonymizer & Entity Recognition

Before raw text is split into semantic chunks and sent to embedding models, the **Presidio-grade PII Redactor (`apps/api/src/domain/compliance/pii_anonymizer.py`)** automatically scans, validates, and masks sensitive entities.

### A. Supported Detection Domains & Recognizers

```text
Domain              Recognizer Patterns / Algorithmic Rules
──────────────────  ──────────────────────────────────────────────────────────────────
Financial           • Credit Cards: Visa, Mastercard, Amex, Discover, RuPay (Validated via LUHN checksum)
                    • IBAN (International Bank Account Numbers)
                    • Indian Financial System Code (IFSC)
──────────────────  ──────────────────────────────────────────────────────────────────
Identity            • US Social Security Numbers (SSN: `\d{3}-\d{2}-\d{4}`)
                    • Indian Aadhaar Numbers (12-digit UID)
                    • Indian Permanent Account Numbers (PAN: `[A-Z]{5}\d{4}[A-Z]`)
                    • International Passports
──────────────────  ──────────────────────────────────────────────────────────────────
Secrets & Secrets   • AWS Access Keys (`AKIA[0-9A-Z]{16}`)
                    • OpenAI API Keys (`sk-[a-zA-Z0-9_-]{20,}`)
                    • GitHub Personal Access Tokens (`ghp_[a-zA-Z0-9]{36}`)
                    • JSON Web Tokens (`eyJ...`)
                    • Cryptographic Private Key Headers (`-----BEGIN ... PRIVATE KEY-----`)
──────────────────  ──────────────────────────────────────────────────────────────────
Healthcare (HIPAA)  • Medical Record Numbers (MRN-XXXXX) & Patient Case Codes
──────────────────  ──────────────────────────────────────────────────────────────────
Network & Infra     • IPv4 (`\b(?:\d{1,3}\.){3}\d{1,3}\b`)
                    • IPv6 & MAC Addresses
──────────────────  ──────────────────────────────────────────────────────────────────
Contact Info        • RFC 5322 Compliant Email Addresses
                    • International E.164 Telephone Numbers
```

### B. Luhn Checksum Validation for Credit Cards
To eliminate false alarms on random 16-digit tracking codes or serial numbers, all candidate credit card strings are validated using the **Luhn Algorithm (Mod 10)**:
```python
def luhn_checksum(number_str: str) -> bool:
    digits = [int(d) for d in number_str if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    return checksum % 10 == 0
```
Only strings passing the mathematical Luhn checksum are masked as credit cards.

### C. Non-Overlapping Interval Scheduling
When text contains overlapping matches (e.g. an Aadhaar pattern embedded within a credit card), greedy regex substitution corrupts byte offsets. Retriever uses interval scheduling:
1. All candidate matches are gathered across all active domain recognizers.
2. Candidates are sorted by span length descending `(m.end - m.start)`.
3. Non-overlapping spans are selected (longer match wins).
4. Text substitutions are performed in reverse index order to preserve string indices.

### D. Masking Strategies

| Mode | Behavior | Example Input | Masked Output |
| :--- | :--- | :--- | :--- |
| **`REDACT`** | Replaces with descriptive bracketed token | `4532-0151-1283-0366` | `[REDACTED_CREDIT_CARD]` |
| **`SYNTHETIC`** | Preserves format and last-4 digits | `4532-0151-1283-0366` | `****-****-****-0366` |
| **`PSEUDONYMIZE`** | Deterministic SHA-256 hash token for search | `alice@hospital.org` | `[PSEUDONYM:3f8e4c1a]` |

> [!TIP]
> **Why Pseudonymization?**  
> `PSEUDONYMIZE` mode allows cross-document correlation searches (e.g. finding all emails from the same pseudonymized user) without storing or exposing the real identity in vector embeddings.

---

## 3. SLA Data Retention Worker

Contractual compliance often dictates that documents older than $N$ days must be purged:
```bash
# Trigger an automated SLA retention scan across tenant documents
curl -X POST "https://rag.prateeq.in/v1/admin/tenants/{tenantId}/compliance/retention?retention_days=90" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```

The worker:
1. Queries documents where `created_at < NOW() - INTERVAL 'retention_days'`.
2. Initiates hard-purge cascading through chunk metadata and vector index partitions.
3. Emits an audit log event with total scanned and purged document counts.

---

## 4. GDPR Article 17 Hard Purge & Cryptographic Certificates

When a user exercises their Right-to-be-Forgotten, a simple soft-delete (`is_deleted = true`) is legally insufficient. Retriever executes a true **Cascade Hard Purge**:

```text
[Hard Purge Request]
        │
        ▼
1. DELETE FROM documents WHERE tenant_id = :id
        │  (Cascade FK to document_chunks)
        ▼
2. DELETE FROM vector_records WHERE tenant_id = :id
        │  (Prunes HNSW vector partitions)
        ▼
3. PURGE FROM Redis Cache (DEL tenant:* query caches)
        │
        ▼
4. DELETE FROM graph_triples WHERE tenant_id = :id
        │
        ▼
5. ISSUE HMAC-SHA256 Signed Compliance Deletion Certificate
```

### Digital Signature Format
To make certificates tamper-evident, the canonical payload is signed using HMAC-SHA256:
$$\text{Signature} = \text{HMAC-SHA256}\Big(\text{SECRET\_KEY},\; \text{cert\_id} \mathbin{\Vert} \text{tenant\_id} \mathbin{\Vert} \text{scope} \mathbin{\Vert} \text{target\_id} \mathbin{\Vert} \text{timestamp} \mathbin{\Vert} \text{records\_json}\Big)$$

If any record count, tenant UUID, or timestamp is altered in the certificate, signature verification immediately fails.

---

## 5. Third-Party Auditor Verification

External auditors can cryptographically verify certificate authenticity without requiring database access or sensitive tenant credentials:

```bash
curl -X GET "https://rag.prateeq.in/v1/compliance/verify/cert_gdpr_10293847"
```

**Auditor Response:**
```json
{
  "certificate_id": "cert_gdpr_10293847",
  "is_valid": true,
  "message": "Certificate signature cryptographically verified via HMAC-SHA256.",
  "timestamp": "2026-09-04T03:10:00Z",
  "sha256_audit_signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 6. Admin Dashboard Compliance Cockpit

In the Web Console (**`/compliance`**):
1. **Zero-Footprint PII Sanitizer Sandbox:** Paste sample text containing SSNs, API secrets, or credit cards; toggle domains and masking strategies in real-time.
2. **Audit Certificate Ledger:** View all past GDPR deletion certificates with 1-click **Verify** and **Download JSON** buttons.
3. **Hard-Purge Confirmation:** Double-confirmation modal preventing accidental deletions.
