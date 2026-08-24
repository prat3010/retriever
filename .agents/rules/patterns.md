# Retriever Backend & RAG Engine — Enforced Architectural Patterns

> **Source:** Extracted & Learned Conventions for `retriever`  
> **Status:** Active & Enforced Across All Agents & Developers

---

### 1. Strict Hexagonal Boundary Rule (`src/domain/`)
- **Rule:** Core domain logic residing in `src/domain/` MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python built-in modules.
- **Constraint:** **NEVER** import infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), ORM/Database frameworks (`sqlalchemy`), or third-party LLM SDKs directly in domain models or services.

### 2. Mandatory Multi-Tenancy Scoping (`tenant_id`)
- **Rule:** Every database entity, query method, vector search index, and REST API endpoint MUST strictly scope operations by `tenant_id`.
- **Constraint:** Frontend clients and backend adapters MUST NOT hardcode fallback tenant UUIDs or silently default unauthenticated requests to guest UUIDs.

### 3. Local Model Embeddings Only (`nomic-embed-text`)
- **Rule:** Vector embeddings MUST be generated using a local embedding model (e.g. Ollama `nomic-embed-text` on `http://host.docker.internal:11434/v1`).
- **Constraint:** **DO NOT** consume client-provided LLM keys (Gemini, OpenAI, Cohere) for chunk embedding to preserve quota limits and prevent API rate-limit errors.

### 4. Citation Integrity & Presigned Download URLs
- **Rule:** All RAG search results must return verified citation metadata and presigned download URLs (`getDownloadUrl`).
- **Constraint:** Semantic cache hits MUST emit cache indicators (`⚡ Cached`), and 👍/👎 user feedback MUST be persisted with full tenant context.

### 5. Mandatory Python Formatting & Linting (`ruff`)
- **Rule:** All modified or newly created Python files MUST be checked and auto-fixed using `ruff check --fix`.
- **Constraint:** Never commit Python code with failing ruff checks or unformatted imports.

### 6. Documentation & Roadmap Audit Contract
- **Rule:** Whenever any code change is executed (bug fixes, schema updates, parameter tweaks, or refactors), the agent MUST update `ROADMAP.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`, and relevant `docs/` before completing the task.
- **Constraint:** Features are not considered done until all project tracking markdowns accurately reflect the codebase state.

### 7. Database Migration & Conformance Testing
- **Rule:** Schema changes require Alembic migration scripts, verified by Pytest suites.
- **Constraint:** Zero over-engineering — keep domain logic minimal, decoupled, and completely covered by tests.

### 8. Agent Architecture Pre-Flight & Blast Radius Inspection
- **Rule:** Before writing or modifying code in `apps/api/`, `workers/`, or `packages/`:
  ```bash
  python3 scripts/query_architecture.py --target <component_or_endpoint>
  ```
- **Constraint:** Verify all cross-repo callers (e.g. `prateeq.in/scoping`, `prateeq.in/rag/app`, `prateeq_scoping` dogfooding tenant) before modifying endpoint signatures or schemas.

### 9. Episodic Memory Bank & Failure Postmortems
- **Rule:** Before attempting any complex refactor, database migration, or debugging task, the agent **MUST** inspect `docs/LEARNINGS.md` for known framework quirks (e.g. Hexagonal domain pollution, multi-tenant leaks, local embedding constraints, alembic model detection).
- **Constraint:** Whenever a non-trivial bug or architectural quirk is resolved, the agent **MUST** document the failure signature, root cause, anti-pattern, and enforced solution in `docs/LEARNINGS.md`.

