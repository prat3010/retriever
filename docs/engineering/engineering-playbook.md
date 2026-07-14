# Engineering Playbook & Coding Standards: Retriever Platform

This document serves as the canonical handbook for implementing code on the Retriever platform. It specifies mandatory patterns, directory rules, interface boundaries, and operational constraints that must be followed during feature development.

Refer to the foundational documents for contextual guidelines:
- [The Engineering Constitution (master-vision.md)](file:///Users/prateeksharma/Developer/retriever/docs/constitution/master-vision.md)
- [System Architecture Design Blueprint (architecture.md)](file:///Users/prateeksharma/Developer/retriever/docs/architecture.md)
- [System Design & Implementation Blueprint (system-design.md)](file:///Users/prateeksharma/Developer/retriever/docs/implementation/system-design.md)

---

## 1. Code Organization

The monorepo separates runtime applications, background workers, and shared dependency packages. Circular dependency flows are build-blocking errors.

### 1.1 Folder Boundaries & Ownership

```
/Users/prateeksharma/Developer/retriever/
├── apps/
│   ├── api/                     # Gateway & serving API application (FastAPI)
│   └── web/                     # Client Web playground UI application (Next.js)
├── packages/
│   ├── processing-core/         # Shared processing primitives (PDF parse, chunk, embed)
│   └── retriever-client-js/     # Frontend JS/TS client SDK (Milestone 11)
├── workers/                     # Async ingestion, OCR, and reindexing tasks
└── docs/                        # Static specifications, ADRs, and configurations
```

* **No Cross-App Imports:** Files in `apps/api` MUST NOT import code directly from `apps/web`. Sharing parameters or definitions requires moving them to a package within `packages/`.
* **Shared Package Restrictions:** Packages under `packages/` house shared primitives (e.g., `processing-core`) or SDK stubs. They MUST NOT import libraries that pull in framework dependencies or define network connections beyond their SDK scope.

### 1.2 Module Boundaries & Dependency Flow

Within `apps/api/src/domain/`, logical contexts are fully isolated:

```
[serving / presentation] (Gateway, Routers)
         │
         ▼
[domain.abstractions] (Ports) <─────── [domain.core] (Domain logic & Entities)
         ▲
         │
[adapters] (Concrete Infrastructure: DB, LLMs, Storage)
```

1. **Inward Dependencies Flow:** Dependencies MUST flow inward toward abstractions (`domain.abstractions`).
2. **Domain Isolation:** Files inside `domain/` contexts MUST NOT import database schemas, framework decorators, database drivers, or HTTP routers.
3. **Domain-to-Domain Communication:** A domain context (e.g. `inference`) MUST NOT import entities or internal models directly from another context (e.g. `knowledge`). Cross-domain communication is limited to:
   * Abstract interfaces defined under `domain.abstractions`.
   * Event publishing payloads routed through the shared message broker.

### 1.3 Layer Dependency Matrix

To maintain logical isolation and enforce architectural boundaries, all imports across project packages must strictly adhere to the following rule matrix:

| Layer | May Import | Must Never Import |
|---|---|---|
| **Domain** (`domain/`) | `domain/abstractions/` (Ports) | `adapters/`, `apps/api/routers/`, `workers/`, framework libraries (FastAPI, Next.js), database client drivers (SQLAlchemy, pgvector). |
| **Ports** (`domain/abstractions/`) | Python stdlib, domain types | All other layers. Ports must be purely abstract and contain zero implementation dependencies. |
| **Adapters** (`adapters/`) | `domain/abstractions/` (Ports), framework libraries, database clients, third-party SDKs. | Direct implementations of other adapters, core domain logic implementation (`domain/`). |
| **API Gateway** (`apps/api/src/`) | `domain/abstractions/` (Ports), framework routing libraries (FastAPI). | Direct raw database connections bypassing adapters, internal code of other applications, frontend packages. |
| **Workers** (`workers/src/`) | `workers.src.celery_app`, `packages/processing-core`, storage drivers. | API gateway HTTP routes, frontend files, core domain logic implementation (must interact through Ports). |
| **Packages** (`packages/`) | Other utility packages (only if acyclic and strictly versioned). | Application code inside `apps/`, backend adapters, database client instances. |
| **Frontend** (`apps/web/`) | HTTP calls to API Gateway at `apps/api/`. | API Gateway inner modules, database/SQL engines, backend adapters, system files. |

#### 1.3.1 Valid Dependency Direction Examples
* **Core-to-Port Call:** `apps/api/src/domain/retrieval/search_service.py` imports `domain.abstractions.retrieval.VectorSearchProvider` to execute hybrid search, satisfying inward-bound design.
* **Adapter-to-Port Implementation:** `apps/api/src/adapters/vector/vector_repository.py` implements `VectorSearchProvider` from `domain.abstractions.retrieval`.
* **API-to-Port Integration:** `apps/api/src/main.py` calls methods on adapters through FastAPI dependency injection, never directly importing domain logic.

#### 1.3.2 Invalid Dependency Direction Examples (Build-Blocking)
* **Domain Coupling to Adapter:** A domain service at `domain/inference/orchestrator.py` attempts to import `adapters.database.connection.get_session` (Domain importing infrastructure).
* **Domain Coupling to Framework:** A domain service at `domain/config/config_service.py` imports `fastapi.HTTPException` (Domain logic depending on presentation framework).
* **Frontend Bypassing API:** `apps/web/src/app/page.tsx` directly imports `apps/api/src/domain/inference/orchestrator.py` (Frontend importing server code).
* **Package Coupling to Infrastructure:** `packages/processing-core/src/processing_core/chunker.py` imports `adapters.database.models.DocumentDb` (Shared library importing infrastructure adapter).

---

## 2. Hexagonal Architecture Rules

No third-party SDK, database driver, ORM library, or communication framework may leak into core business logic.

```
       +--------------------------------------------------------------+
       |                      Infrastructure Layer                    |
       |                                                              |
|  +--------------+    +---------------+    +---------------+  |
|  |  FastAPI App |    | PgVectorSrch  |    | LocalStorage  |  |
|  +-------|------+    +-------|-------+    +-------|-------+  |
       +----------|-------------------|--------------------|----------+
                  |                   |                    |
                  | (HTTP Call)       | (SQL execution)    | (API Call)
                  v                   v                    v
       +--------------------------------------------------------------+
       |                         Ports Layer                          |
       |                                                              |
       |   [DocumentStorage]    [VectorSearchProv]  [ConfigRegistry]  |
       +------------------------------|-------------------------------+
                                      |
                                      v
       +--------------------------------------------------------------+
       |                          Core Domain                         |
       |                                                              |
       |                     +-----------------+                      |
       |                     | Ingestion Logic |                      |
       |                     +-----------------+                      |
       +--------------------------------------------------------------+
```

* **Ports:** Interfaces and abstract definitions defining the system's runtime capability requirements.
  * *Location:* `domain/abstractions/`
  * *Naming Pattern:* `[Service]Provider` (e.g. `LlmProvider`, `VectorSearchProvider`).
* **Adapters:** Concrete implementations of ports interacting with physical infrastructure (databases, caches, third-party APIs).
  * *Location:* `adapters/`
   * *Naming Pattern:* `[Technology][Service]Adapter` (e.g. `PgVectorSearchAdapter`, `S3StorageProviderAdapter`).
* **Forbidden Dependencies Rule:** The import of SQL models, SQLAlchemy sessions, Boto3 S3 clients, OpenAI SDK libraries, or FastAPI parameters inside files located under `domain/` is strictly forbidden. The automated project build checks will fail immediately on violations.

---

## 3. API Standards

All endpoints exposed by serving applications must be RESTful and use JSON formats.

* **Path Naming:** Use plural nouns and kebab-case for URL segments (e.g. `/v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages`).
* **JSON Properties Naming:** Use `camelCase` for JSON request/response keys.
* **Versioning Strategy:** URLs contain the major version segment: `/v{major}/`. Breaking changes increment the URL index, while non-breaking additions are introduced under minor version flags.
* **Idempotency Requirements:** All write path operations (HTTP `POST` and `PUT`) must support safe client retries. Clients must provide an `Idempotency-Key` header with a UUID v4 payload:
$$\text{Idempotent Request} \longrightarrow \text{Header: } \texttt{Idempotency-Key: <UUID>}$$
* Gateway endpoints cache this key in Redis (L1) for **24 hours**. If an identical request arrives while processing, the system returns a `409 Conflict` or returns the cached response if completed.
* **Pagination:** Listing endpoints MUST support cursor-based pagination. Offset-based pagination is prohibited for high-volume document and chunk queries to prevent index retrieval delays.
```json
// Response pagination metadata format
{
  "data": [...],
  "pagination": {
    "nextCursor": "chk_990a03b4...",
    "limit": 50,
    "hasMore": true
  }
}
```
* **Unified Error Schema (RFC 7807):** All API errors return a standard JSON payload:
```json
{
  "type": "https://api.retriever.io/errors/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The parameter 'chunkSize' must be a positive integer.",
  "instance": "/v1/tenants/tnt_800f72a0/config",
  "traceId": "tr_11223344556677889900aabbccddeeff"
}
```

---

## 4. Database Standards

* **Naming Conventions:** Use lowercase `snake_case` for all table names and columns.
  * *Indexes:* `idx_{table}_{column}`
  * *Foreign Keys:* `fk_{table}_{referenced_table}_{column}`
* **Migration Strategy:** All structural changes to database layouts must be managed through migration files (e.g. Alembic for Python).
  * Up and down migration scripts are mandatory.
  * Direct structural edits to databases during deployments are prohibited.
* **RLS Requirements:** All tables containing customer data (documents, chunks, sessions, templates) MUST have PostgreSQL Row-Level Security active.
  * Security policies assert that `tenant_id` context parameters match values set on connections during transaction setup:
```sql
CREATE POLICY tenant_isolation_policy ON documents
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```
* **No Soft Delete on Chunks:** Deleting documents cascade-deletes children chunks and vectors from storage. Soft deletes are only permitted for document metadata logs.
* **Database Transactions:** Relational writes and vector synchronization modifications must execute within transactions. If any sub-task fails, the transaction is rolled back, and pending records are deleted.

---

## 5. Event Standards

All asynchronous interactions must route through structured exchanges using RabbitMQ.

* **Event Naming:** Use kebab-case with past-tense verb structures: `[domain].[entity].[event-past-tense]` (e.g. `knowledge.chunk.indexed`, `ingestion.document.uploaded`).
* **Message Envelope format:** All event payloads must follow a standardized structure:
```json
{
  "eventId": "evt_889f02a3-2c1b-4b5c-a6d8-e9f01a2b3c4d",
  "eventType": "INGESTION_DOCUMENT_UPLOADED",
  "version": 1,
  "timestamp": "2026-07-12T07:34:37Z",
  "traceId": "tr_11223344556677889900aabbccddeeff",
  "payload": {}
}
```
* **Retry and DLQ Policy:** If worker tasks raise connection issues:
  1. The task is re-queued with exponential backoff:
$$\text{Delay} = \text{Base Delay} \times 2^{\text{Retry Count}} + \text{Jitter}$$
  2. If tasks fail **3 consecutive times**, they are routed to the Dead-Letter Queue (`dead.letter`).
  3. Reconcilers inspect the DLQ and send warnings to administrators.

---

## 6. Testing Strategy

Code modifications must go through a multi-tiered testing pipeline before merging.

```
       +---------------------------------------------+
       |   LLM Evaluation (Ragas, LLM-as-a-Judge)    | <-- Non-deterministic
       +---------------------------------------------+
                               │
       +---------------------------------------------+
       |   Integration & Contract (E2E API Tests)    |
       +---------------------------------------------+
                               │
       +---------------------------------------------+
       |   Unit & Property (Mock Adapters, Pure logic)| <-- Fully deterministic
       +---------------------------------------------+
```

* **Unit Tests:** Verify business logic inside domain modules. All ports must use mock implementations. Unit tests MUST run locally in milliseconds without network calls.
  * *Target Coverage:* **100%** on domain files.
* **Integration Tests:** Validate interfaces between core adapters and test instances of databases, cache modules, and local brokers.
* **Contract Tests:** Validate that API outputs match JSON OpenAPI schemas exactly.
* **End-to-End (E2E) Tests:** Automated test runs executing the entire request pipeline: upload file -> parse -> index -> search -> query.
* **Performance Latency Tests:** Automated k6 benchmark scripts run on mock endpoints to verify retrieval performance remains under **150ms** with 200 concurrent requests.
* **RAG Evaluation Tests:** Every model routing and prompt template change must be evaluated against a golden dataset using Ragas metrics:
  * *Faithfulness:* Score must exceed **0.95**.
  * *Answer Relevance:* Score must exceed **0.90**.
  * *Context Recall:* Score must exceed **0.92**.

---

## 7. Logging Standards

* **Structured Formatting:** All logs must output JSON formatted lines to standard out:
```json
{"timestamp":"2026-07-12T07:34:37Z","level":"INFO","traceId":"tr_11223344556677889900aabbccddeeff","tenantId":"tnt_800f72a0","message":"Parallel search query completed.","durationMs":95}
```
* **Sensitive Data Redaction:** Hashing and sanitization rules must filter log messages. Logging raw tokens, keys, customer names, email profiles, or document chunks content is strictly prohibited.
* **Trace Propagation:** Trace and correlation identifiers must be propagated across queue tasks, background workers, database transactions, and LLM calls.

---

## 8. Error Handling Philosophy

* **Recoverable Errors:** Handle gracefully within domain boundaries without failing requests.
  * *Example:* If a cache layer misses, fetch parameters from database and write back to cache.
* **Fatal Errors (Fail-Fast):** Terminate connections, revoke tokens, and alert operations immediately.
  * *Example:* Row-level security exceptions, tenant ID mismatches.
* **Retryable Errors:** If external network components fail, apply exponential retry loops.
  * *Example:* LLM timeout errors, database deadlock locks.
* **User-Facing Responses:** Never expose internal database stack traces, memory addresses, or raw system dependencies in API error outputs.

---

## 9. Security Standards

* **Secrets Management:** Environment secrets and API keys must be retrieved from cloud secret managers (e.g. AWS Secret Manager) at boot. Never store plain keys in code files.
* **Hashed Key Storage:** Client API keys are stored hashed using SHA-256 with random salt strings:
$$\text{Storage Key} = \text{PBKDF2-SHA256}(\text{Key String})$$
* **Validation Middleware:** Gateway endpoints sanitize all input parameters against strict Pydantic schemas. Invalid types, SQL injection patterns, or excessive string lengths are rejected before routing.
* **Prompt Injection Protection:** Construct queries separating context variables from templates:
```
[SYSTEM INSTRUCTION: You are a validator...]
---
[CONTEXT: {grounding_chunks_only}]
---
[USER QUESTION: {sanitized_input}]
```

---

## 10. AI Standards

* **Prompt Template Registry:** All prompts are stored in database configuration tables and resolved dynamically per request. Hardcoding prompts in application source code is prohibited.
* **Embedding Collection Versioning:** Suffix database collection namespaces with embedding model versions to support upgrades:
```
Collection Name: chunks_tnt_800f_text_embedding_3_small
```
* Changing embedding versions requires provisioning a new collection and running reindexing tasks.
* **Citation Verification:** The Inference orchestrator validates inline citations in responses against retrieved chunk identifiers before sending the stream to the client.

---

## 11. Performance Standards

Latency budgets are enforced across all operations, monitored through traces.

| Operation Layer | Latency Budget | Action on Breach |
|---|---|---|
| Ingress Authentication | <= 30ms | Optimize database indexing / Cache lookups |
| Vector DB Similarity Search | <= 80ms | Tune pgvector HNSW parameters |
| BM25 Text Search | <= 50ms | Optimize GIN text index |
| Context Reranking | <= 50ms | Upgrade cross-encoder worker threads |
| SSE Time-To-First-Token | <= 500ms | Flag model routing timeouts |

* **Asynchronous Execution:** Gateway processes must use asynchronous libraries (`async`/`await`) to avoid blocking thread pools.
* **Stream Processing:** Generative API responses must stream chunk tokens using Server-Sent Events (SSE).

---

## 12. Coding Conventions

The codebase requires clean, explicit implementations to ensure readability for both developers and AI tools.

### 12.1 Language Conventions (Python & TypeScript)

* **Code Styling:** 
  * *Python:* Standard PEP 8 rules. Format files using Ruff.
  * *TypeScript:* Standard ESLint configurations. Format files using Prettier.
* **Naming Conventions:**
  * *Classes:* Use `PascalCase` (e.g. `RetrievalEngine`).
  * *Variables / Functions (Python):* Use `snake_case` (e.g. `process_document`).
  * *Variables / Functions (TypeScript):* Use `camelCase` (e.g. `processDocument`).
  * *Constants:* Use uppercase `SNAKE_CASE` (e.g. `MAX_TOKENS_LIMIT`).
* **Type Hints:** Type annotations are mandatory for all function parameters and return values. The `any` keyword is banned in TypeScript.
* **Docstrings:** Public classes, methods, and interface ports must include docstrings (Google style in Python, TSDoc in TypeScript).

### 12.2 Structural File Limitations
* **Maximum File Size:** No code file may exceed **400 lines**. Large files must be refactored into smaller sub-modules.
* **Maximum Function Size:** No function may exceed **40 lines**. If a function exceeds this limit, decompose it into smaller steps.
* **Single Responsibility:** Classes must have a single responsibility. Business rules belong in domain services, and transport logic belongs in adapters.

---

## 13. Git Workflow

* **Branch Naming Conventions:**
  * Features: `feature/` followed by issue identifier or description (e.g. `feature/ingest-pdf`).
  * Bugfixes: `bugfix/` followed by description (e.g. `bugfix/rls-bypass-fix`).
  * Hotfixes: `hotfix/` (production emergency repairs).
  * Documentation: `docs/` (specification updates).
* **Commit Message Format:** Follow Conventional Commits conventions:
```
<type>(<scope>): <short description>

[Optional body text detailing design decisions]
```
* *Types:* `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`.
* *Example:* `feat(retrieval): implement reciprocal rank fusion logic`

### 13.3 Architectural Governance — Hybrid Strategy

The codebase uses two mechanisms to keep architecture honest without treating docs as a mirror:

**1. Automated conformance tests (`tests/test_architecture.py`)**
Run with every `pytest` invocation. Currently checks:
- Domain files never import adapters, FastAPI, SQLAlchemy, or other infra
- No hardcoded system prompt constants exist
Extend this file when adding new architectural rules — it's cheaper than docs.

**2. ADR Ritual — record intentional divergences**
When code must deviate from the constitution/master-vision.md:
- Don't soften the constitution (it stays the permanent north star)
- Write an ADR in `docs/decisions/` explaining the trade-off, the context, and the conditions under which you'd revert
- Reference the ADR in the code with a comment (`# see ADR-00X`)

The constitution sets the target. ADRs chronicle the map. Tests enforce the hard lines.

### 13.4 Pull Request Checklist
Before opening a pull request, verify:
* [ ] The code is formatted using Ruff / Prettier, and all linter checks pass.
* [ ] Unit test coverage on modified domain code is **100%**.
* [ ] Database migrations include both up and down scripts.
* [ ] Security policies (RLS) are active on all new customer tables.
* [ ] Dynamic prompts are stored in registry configurations, not hardcoded.
* [ ] Architecture conformance tests (`test_architecture.py`) still pass — new commits should not introduce violations.

---

## 14. Definition of Done (DoD)

A feature task is considered complete only when it meets the following criteria:

* **Testing Requirements:** Unit and integration tests cover the new code, and validation benchmarks verify response compliance.
* **Performance Validation:** Metrics verify that query pipelines meet latency budgets under concurrent load conditions.
* **Security Verification:** Row-Level Security checks are active, and input validation schemas sanitize parameters before processing.
* **Telemetry Monitoring:** Performance spans are registered, and Prometheus counter metrics track usage and latencies.
* **Error Tracking:** Sentry is initialized in both the API lifespan and Celery worker process (via `worker_process_init` signal) for exception grouping, release tracking, and breadcrumbs. Sentry integrates with OpenTelemetry so spans from both systems appear in one view. **Parser sandbox workers are excluded** from Sentry due to their zero-egress security model. Configure via `SENTRY_DSN` environment variable; Sentry is skipped entirely when the DSN is empty.
* **Documentation:** API specifications are updated in OpenAPI docs, and internal architecture plans or README configurations are updated.
* **Peer Verification:** The code passes review checks and automated CI builds successfully without warning flags.
