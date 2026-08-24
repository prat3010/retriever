---
name: security-auditor
description: Scans retriever backend for Multi-Tenancy isolation, raw SQL injection, unauthorized tenant leakage, and embedding key safety.
---

# Security & Multi-Tenancy Auditor Skill (Retriever)

This skill enforces strict multi-tenancy isolation across the Python FastAPI backend and database adapters.

## Core Audit Rules

1. **Multi-Tenancy Scoping (`tenant_id`)**:
   - Every SQLAlchemy query, repository method, and vector similarity search MUST explicitly filter by `tenant_id == current_tenant.id`.
   - Never fall back to hardcoded guest UUIDs or trust unauthenticated client-provided tenant parameters.

2. **Local Model Invariant**:
   - Vector chunk embeddings MUST strictly use local Ollama (`nomic-embed-text`).
   - External LLM API keys must never be consumed for embeddings.

3. **Sandboxed Code Execution**:
   - Python REPL execution for RLM (Recursive Language Model) tools must execute strictly inside the isolated sandbox adapter (`apps/api/src/adapters/sandbox/python_sandbox_adapter.py`).

## Audit Command
When invoked, run:
```bash
ruff check --fix . && pytest tests/unit
```
