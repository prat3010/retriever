# Security Policy

The Retriever project takes the security and integrity of enterprise cognitive workloads with the utmost seriousness.

---

## 🛡️ Supported Versions

| Version | Supported | Notes |
| :--- | :---: | :--- |
| `0.81.x`+ | ✅ | Current active development (FastAPI + pgvector + Hexagonal core) |
| `< 0.80.x`| ❌ | Deprecated legacy prototypes |

---

## 🔒 Reporting a Vulnerability

If you discover a potential security vulnerability, privilege escalation, or multi-tenant isolation flaw in Retriever:

1. **Do NOT open a public GitHub issue.**
2. Email your discovery and reproduction steps directly to:
   - **`prateeqsharma@gmail.com`**
3. Include:
   - Detailed attack vector and reproduction commands or scripts.
   - Affected components (`apps/api/src/routers/`, `adapters/`, or `domain/`).
   - Potential impact (e.g. cross-tenant data leakage, prompt injection bypass, or memory exhaustion).

You will receive an initial response within **24 hours**. We will collaborate with you to evaluate, mitigate, and issue a patch release before public disclosure.

---

## 🏛️ Security Architecture & Invariants

Retriever enforces strict zero-trust cryptographic guarantees:
- **Database Row-Level Security (RLS):** Cross-tenant vector isolation is enforced in PostgreSQL 16 engine space via `current_setting('app.current_tenant_id')`.
- **Envelope Encryption:** Per-tenant AES-256 Data Encryption Keys (DEKs) protect chunks and embeddings at rest.
- **Inbound/Outbound Guardrails:** Dual-layer filtering with Llama Guard 3 and NVIDIA NeMo Colang rails.
- **Local Embedding Invariant:** Ingestion pipelines use local Ollama models (`nomic-embed-text`); raw document vectors are never exfiltrated to external LLM provider APIs.

For full architectural and cryptographic specifications, see our authoritative whitepaper:  
👉 **[`docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md`](docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md)**
