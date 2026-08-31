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

### 10. Spec-First Contract Blueprinting & Post-Milestone Graph Sync
- **Pre-Milestone Spec-First Rule:** Before writing implementation code for a new milestone or FastAPI router:
  1. **Draft High-Definition Architecture Nodes:** Create or update specification nodes in `docs/architecture_nodes/` defining Pydantic schemas, HTTP route signatures, non-negotiable invariants, and test plans.
  2. **Strict Status Tagging:** Explicitly set `status: planned` in the node's YAML frontmatter so agents recognize the target contract without hallucinating that runtime code already exists.
  3. **Low-Definition Horizon:** Keep future milestones (M+3 and beyond) in high-level roadmap markdowns (`docs/`, `ROADMAP.md`), avoiding premature line-by-line over-specification.
- **Post-Milestone Synchronization Rule:** Immediately upon completing code implementation and verifying tests:
  1. **Promote Node Status:** Update the frontmatter from `status: planned` → `status: production`.
  2. **Synchronize Roadmaps & Learnings:** Update milestone checkboxes in `ROADMAP.md` / `PROJECT_STATUS.md` and document any runtime quirks/learnings in `docs/LEARNINGS.md`.
  3. **Regenerate Canvases & Vault Index:** Execute:
     ```bash
     python3 ../Prateek_website/scripts/sync_graph_with_code.py
     ```
  4. **Zero-Drift Invariant:** Never finish a milestone task while leaving Obsidian canvases, architecture index files, or markdown PRDs desynchronized from the live codebase.

### 11. Production-First & Zero-Toy Utility Invariant Rule (No Mocks, No Gimmicks)
- **Rule:** All backend algorithms, adapters, cognitive workflows, and administrative endpoints MUST be genuine, production-grade implementations with verified enterprise utility.
- **Strict Invariants:**
  1. **Zero Algorithmic Shortcuts or Fakes:** Do NOT implement naive regex heuristics and mislabel them as SOTA ML algorithms (e.g. calling simple regex "LongLLMLingua" or keyword matching "Llama Guard 3"). If an algorithm is specified, implement the authentic model/math or provide a transparent, explicitly labeled fallback.
  2. **Zero Mock Data Returns:** All endpoints must query real database models, execute genuine vector operations, and emit verified telemetry. Never return static synthetic mock data in production routers.
  3. **Pragmatic Production Value:** Prioritize core platform reliability (safe blue/green releases, atomic symlinks, rollback gates, concurrent load testing benchmarks, and unsupervised GraphRAG clustering) over cosmetic features.
  4. **Strict Conformance:** Every endpoint and adapter must be verified by automated Pytest suites with genuine database and memory integration.



