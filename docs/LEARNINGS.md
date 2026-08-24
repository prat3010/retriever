# Architectural Learnings & Episodic Memory Bank (`retriever`)

This document serves as the **Episodic Long-Term Memory** for AI agents and developers working on the `retriever` RAG engine. AI agents MUST consult this file before undertaking architecture modifications, refactors, or debugging sessions to prevent repeating known traps.

---

## 1. Architectural Boundary Rules (Hexagonal Architecture)

### Quirk: Hexagonal Domain Pollution
- **Context / Framework**: Hexagonal Architecture / Python
- **Symptom**: Circular dependencies, tightly-coupled unit tests requiring live databases, or leaky domain abstractions.
- **Root Cause**: Code in `src/domain/` directly importing infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), database frameworks (`sqlalchemy`), or external API SDKs.
- **Anti-Pattern**:
  ```python
  # BAD: In src/domain/services/document_service.py
  from sqlalchemy.orm import Session
  from src.adapters.database.models import DocumentModel
  from openai import OpenAI
  ```
- **Enforced Solution**: Domain files MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python libraries. Infrastructure details are injected via constructor interfaces.
  ```python
  # GOOD: In src/domain/services/document_service.py
  from src.domain.abstractions.repositories import DocumentRepositoryInterface
  from src.domain.abstractions.embedder import EmbedderInterface
  ```

---

## 2. Multi-Tenancy & Data Isolation

### Quirk: Leaky Multi-Tenancy Queries & Guest UUID Defaults
- **Context / Framework**: Multi-Tenant Vector & Relational Store
- **Symptom**: Data leaking across tenants, missing tenant filters in raw vector search, or silent guest fallbacks.
- **Root Cause**: Omitting `tenant_id` filter in SQLAlchemy queries or hardcoding default UUIDs in frontend/backend adapters.
- **Anti-Pattern**:
  ```python
  # BAD: Querying without tenant scoping
  docs = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
  ```
- **Enforced Solution**: Every database query, repository method, and vector similarity search MUST explicitly scope by `tenant_id == current_tenant.id`.
  ```python
  # GOOD: Strict multi-tenant isolation
  docs = db.query(DocumentModel).filter(
      DocumentModel.id == doc_id,
      DocumentModel.tenant_id == current_tenant.id
  ).first()
  ```

---

## 3. Vector Embeddings & Local Compute Invariant

### Quirk: Cloud LLM Rate Limiting on Vector Ingestion
- **Context / Framework**: Embedding Model Pipelines
- **Symptom**: `429 Rate Limit Exceeded` errors or high API costs during bulk document ingestion.
- **Root Cause**: Using client-provided cloud LLM API keys (Gemini, OpenAI, Cohere) for generating dense vector embeddings.
- **Anti-Pattern**: Calling cloud LLM endpoints for vector embedding calculations.
- **Enforced Solution**: ALWAYS use local Ollama (`nomic-embed-text`) running on `http://host.docker.internal:11434/v1` for vector embedding generation. Preserve external cloud LLMs strictly for generative completions.

---

## 4. Alembic Migrations & Model Registry

### Quirk: `alembic revision --autogenerate` Missing Newly Created Models
- **Context / Framework**: Alembic + SQLAlchemy
- **Symptom**: Generated migration files have empty `upgrade()` and `downgrade()` blocks even though new tables or columns were added.
- **Root Cause**: `apps/api/alembic/env.py` must import all database models from `models.py` into `target_metadata` before executing autogenerate.
- **Enforced Solution**: Ensure all newly created tables in `apps/api/src/adapters/database/models.py` are explicitly imported or registered on `Base.metadata` in `alembic/env.py`.

---

## 5. Agent Workflow Checklist

Before completing any task:
1. **Pre-Flight**: Run `python3 scripts/query_architecture.py --target <entity_or_api>` to inspect blast radius.
2. **Episodic Check**: Verify this `docs/LEARNINGS.md` file for known quirks.
3. **Lint & Format**: Run `ruff check --fix .`.
4. **Test Verification**: Run `pytest tests/unit` to ensure zero regressions.
5. **Roadmap & Status**: Update `PROJECT_STATUS.md` and `ROADMAP.md` before finishing.
