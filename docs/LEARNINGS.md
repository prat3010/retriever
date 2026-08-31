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

## 5. Zero-Toy Authentic Algorithm Implementations & Pure Python Fallbacks

### Quirk: Dependency Drift in Lean / Edge Environments
- **Context / Framework**: Data Science & Machine Learning Adapters (e.g. `scikit-learn`, `HDBSCAN`, `c-TF-IDF`)
- **Symptom**: `ModuleNotFoundError: No module named 'sklearn'` on resource-constrained containers or edge runtimes.
- **Anti-Pattern**: Writing mock data placeholders or static strings simulating ML algorithms.
- **Enforced Solution**: Always implement the authentic mathematical algorithm in pure Python / NumPy as a zero-dependency fallback (e.g., NumPy expectation-maximization cosine KMeans and mathematical TF-IDF term weighting) while leveraging `scikit-learn` when available. Never compromise mathematical integrity with fake mocks.

---

## 6. Zero-Downtime Deployments & Automated Rollbacks

### Quirk: In-Place `git reset --hard` Deployment Failures
- **Context / Framework**: Oracle VPS / Systemd Services
- **Symptom**: Service downtime during `pip install` or broken runtime state if an Alembic migration or package compilation fails.
- **Anti-Pattern**: Running `git reset --hard origin/main && pip install -r requirements.txt && systemctl restart` directly on the active service root.
- **Enforced Solution**: Deploy into timestamped release directories (`/opt/retriever/releases/<timestamp>`), run pre-migration database snapshots, execute migrations, switch the `/opt/retriever/current` symlink atomically, and automatically roll back to the previous release if health probes (`/health/readiness`) fail within 60 seconds.

---

## 7. Agent Workflow Checklist

Before completing any task:
1. **Pre-Flight**: Run `python3 scripts/query_architecture.py --target <entity_or_api>` to inspect blast radius.
2. **Episodic Check**: Verify this `docs/LEARNINGS.md` file for known quirks.
3. **Lint & Format**: Run `ruff check --fix .`.
4. **Test Verification**: Run test suites (`pytest apps/api/tests/ -v`) to ensure zero regressions.
5. **Roadmap & Status**: Update `PROJECT_STATUS.md`, `ROADMAP.md`, `TECH_DEBT.md`, and relevant `docs/` before finishing.

