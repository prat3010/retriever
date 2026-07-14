# Product Roadmap

This document outlines the implementation phases and milestones for the Retriever platform.

---

## Roadmap Overview

| Milestone | Title | Focus Area | Status | Target |
|---|---|---|---|---|
| **M1** | Repository Foundation | Directory layout, configurations, CI/CD, linting, Docker environment | **Completed** | Q3 2026 |
| **M2** | Authentication & Tenant Foundation | Identity interfaces, relational schemas, Postgres RLS contexts, API keys, cache | **Completed** | Q3 2026 |
| **M3** | Configuration & Platform Infrastructure | Global/Tenant configurations, database JSONB overrides, environment fallbacks | **Completed** | Q3 2026 |
| **M4** | Document Ingestion & Storage | Parsing tasks, unstructured layouts, chunking, event broker lifecycle | **Completed** | Q3 2026 |
| **M5** | Retrieval, Fusion & Rerank | pgvector indexes, hybrid search, Reciprocal Rank Fusion, Cohere reranking | **Completed** | Q3 2026 |
| **M6** | Generative Inference & Citations | LLM adapters, prompt orchestrations, context window packing, citation audits | **Completed** | Q3 2026 |
| **M7** | Observability & Hardening | Structured logging, Prometheus metrics, OTel tracing, rate limiting | **Completed** | Q4 2026 |
| **M8** | Production Hardening | DB bootstrap fixes, worker consolidation, shared packages, architecture tests | **Completed** | Q4 2026 |
| **M9** | Client Hierarchy & Admin API | Users table, sub-client RLS, per-tenant LLM keys, admin API scoping, CRUD endpoints | **Completed** | Q4 2026 |
| **M10** | Admin Dashboard | Next.js admin UI for platform management (tenants, users, configs, onboarding, playground) | *Completed* | Q1 2027 |
| **M11** | Client SDK & API Surface | JS/TS RetrieverClient, OpenAPI 3.1 spec, pagination, rate limit headers | **Completed** | Q1 2027 |
| **M12** | Production Storage | S3/MinIO adapter, encrypted key persistence, connection pool tuning | **Completed** | Q2 2027 |
| **M13** | Multi-Industry Configurability | Per-tenant chunking, metadata extractors, guardrails, citation formatting | **Completed** | Q2 2027 |
| **M14** | Performance & Scale | HNSW tuning, semantic cache, bulk ingest, SSE lifecycle, memory profiling | **Completed** | Q3 2027 |
| **M15** | Enterprise Readiness | Audit log writer, SSO/OIDC, RBAC, data retention, backup/restore, compliance | **Completed** | Q3 2027 |

---

## Detailed Milestone Targets

### [Completed] Milestone 1: Repository Foundation
- Establish workspace structure for FastAPI, Next.js, and background workers.
- Setup Ruff formatting and TypeScript linting boundaries.
- Build Docker configurations and docker-compose templates.
- Automate checks with GitHub Actions.

### [Completed] Milestone 2: Authentication & Tenant Foundation
- Design abstract identity interfaces (ports) and database schemas.
- Implement thread-local transaction hooks setting PostgreSQL RLS variables.
- Hash client tokens using SHA-256 for secure API validations.
- Implement L1 caching via Redis with write-through logic.
- Configure Tenancy boundary breach checks (Revocation Kill-Switch).

### [Completed] Milestone 3: Configuration & Platform Infrastructure
- Create dynamic configuration domain entities (FeatureFlags, AI/Embedding/Storage Providers).
- Build the SQL config registry repository adapter supporting JSONB schema overrides and versioning.
- Implement ConfigurationService managing dynamic inheritance and environment falls.
- Added administrative API endpoints for configurations with credentials redaction.
- Applied Postgres RLS policies on configurations database tables.

### [Completed] Milestone 4: Document Ingestion & Storage
- Define unstructured layout parsing algorithms for PDF, Markdown, and text files.
- Implement token-aware sliding window chunkers inside background workers.
- Integrate event broker (RabbitMQ) handling document lifecycle events.
- Document upload, deduplication, listing, status, and deletion endpoints.

### [Completed] Milestone 5: Retrieval, Fusion & Rerank
- Configure pgvector extension indexes (HNSW) for semantic matching.
- Implement vector similarity query database repositories with metadata filtering.
- Implement Reciprocal Rank Fusion (RRF) logic merging semantic and keyword search hits.
- Integrate Cohere Reranking models for context refinement with graceful degradation.

### [Completed] Milestone 6: Generative Inference & Citations
- Implement LlmProvider port with OpenAI adapter (sync + streaming).
- Build PromptBuilder with template registry, context injection, and token budget compression.
- Implement CitationValidator for inline source chunk verification.
- Build InferenceOrchestrator coordinating history fetch, prompt compilation, LLM dispatch, citation validation, and telemetry logging.
- Chat session create/message endpoints with SSE streaming.

### [Completed] Milestone 7: Observability & Hardening
- Configure structured logging via structlog with OTel trace context injection.
- Implement Prometheus metrics registry (latency, tokens, queue backpressure, RLS violations).
- Implement OpenTelemetry tracer with OTLP export and FastAPI instrumentation.
- Implement Redis sliding-window rate limiter with FastAPI dependency integration.
- Telemetry middleware for request timing and structured access logs.
- `/metrics` endpoint for Prometheus scraping.

---

### [Completed] Milestone 8: Production Hardening

**Objective:** Close gaps that prevent the platform from running reliably outside development. Fix DB bootstrap crashes, consolidate worker architecture, share code properly between API and workers, and enforce architectural rules via conformance tests.

**Deliverables:**
- Celery adopted as the single worker framework; pika-based event consumer deprecated.
- Shared `processing-core` package extracted (PDF parser, chunker, embedding retry).
- CORS configurable via `CORS_ORIGINS` env var.
- Sentry integration in API lifespan + Celery worker.
- DB engine singleton lifted to injectable module-level engine (`get_engine()` / `set_engine()`).
- Architecture conformance tests: `tests/test_architecture.py` enforces hexagonal boundaries and no hardcoded prompts.
- All docs reconciled with codebase (architecture, system-design, playbook, constitution).
- Prompts fail loud with `PromptTemplateNotFoundError` instead of silent hardcoded fallback.
- 78/78 tests passing.

---

### [Next] Milestone 9: Client Hierarchy & Admin API

**Objective:** Introduce the user/sub-client model, per-tenant LLM key management, admin API key scoping, and CRUD endpoints for platform management. This is the foundation for all downstream features.

**Prerequisites:** M8.

**Complexity:** Large

**Dependencies:** M8

**Expected Outcome:** Each client tenant can have multiple users with isolated chat data. Admin API keys can manage all tenants; client API keys are scoped to their tenant. Per-tenant LLM keys and model selection are configurable via admin API.

**Targets:**
- `users` table: `user_id`, `tenant_id`, `display_name`, `is_active`, `created_at`. RLS by `tenant_id`.
- `chat_sessions` + `chat_messages` gain `user_id` column with RLS filtering.
- Per-tenant LLM key storage: encrypted `llm_api_key` + `llm_model` fields on `TenantConfig`. Adapter resolves: request header > tenant config > env var fallback.
- API keys gain `scope` field: `admin` (full access across all tenants) vs `client` (scoped to one tenant). Multiple keys per tenant allowed (named, revocable).
- Admin CRUD endpoints: list/search tenants, create/suspend tenant, list users per tenant, list documents per tenant, create/edit prompt templates per tenant, get/set tenant config (LLM key, model, chunk params).
- `X-User-ID` header support: middleware extracts from request, sets RLS context variable `app.current_user_id`. Admin keys bypass user filter.
- Sub-client data isolation verified: a user within a tenant cannot see another user's chat history.

**Acceptance Criteria:**
- Creating a tenant + generating an API key can be done entirely through the API (no DB access needed).
- Two users in the same tenant produce isolated chat sessions with no data bleed.
- Admin API key can view all tenants; client API key is limited to its own tenant.
- Setting a per-tenant LLM key via admin API causes subsequent queries to use that key instead of the env var.

---

### [Completed] Milestone 10: Admin Dashboard

**Objective:** Build a Next.js admin UI that consumes the M9 admin API. One place to manage everything — no SQL, no terminal.

**Prerequisites:** M9.

**Complexity:** Large

**Dependencies:** M9

**Deliverables:**
- ✅ Next.js 14 scaffold: shadcn/ui + Tailwind v4, TanStack Query, Zustand, sonner toasts, next-themes
- ✅ Auth: admin master key login, sessionStorage + cookie, middleware guard
- ✅ App shell: sidebar, topbar (action slots), ErrorBoundary wrapper, theme toggle
- ✅ Domain hooks: tenants (paginated), users, API keys, config, documents, prompts (CRUD + preview)
- ✅ 9 routes: `/` dashboard, `/login`, `/onboard`, `/tenants` (search + pagination), `/tenants/[id]` (7 tabs), `/tenants/[id]/playground`, `/settings`, `/audit-log`
- ✅ Tenant detail tabs: Overview, Documents, Users, API Keys, Prompts (create/edit/delete + preview), Sandbox (RAG chat via SSE), Config
- ✅ Global config page: AI provider, embedding, retrieval, rate limits
- ✅ Audit log viewer: filterable by tenant ID and action type
- ✅ Client onboarding wizard: 3-step flow with curl examples
- ✅ API Playground: per-tenant endpoint test console
- ✅ Reference client (`apps/client-reference/`): `RetrieverClient` JS class, Chat/SSE/Search/Documents tabs
- ✅ Alert dialog confirmations for destructive actions
- ✅ Backend: admin documents list, prompts CRUD + preview, paginated tenants, audit log repository + write hooks + list endpoint
- ✅ `bypass_rls` consistency: `PromptTemplateRegistry` methods accept `bypass_rls` parameter; admin endpoints pass `True`
- ✅ `httpx` → `httpx2` migration (Starlette deprecation fix)
- ✅ 111 tests (94 → 111, +17 new admin API tests), Ruff clean, web build clean
- ✅ `docs/features/admin-dashboard.md` — full agent guide
- ✅ `DocumentRepository` port extracted (`domain/abstractions/ingestion.py` + `adapters/database/document_repository.py`), 5 inline SQLAlchemy blocks removed from `main.py`
- ✅ All M10 items complete — milestone ready for deploy

---

### [Completed] Milestone 11: Client SDK & API Surface

**Objective:** Provide a lightweight JS/TS `RetrieverClient` so frontend developers integrate in one line of config. Standardize API surface conventions.

**Prerequisites:** M9 (stable admin API, user model).

**Complexity:** Medium

**Dependencies:** M9

**Expected Outcome:** A frontend developer adds `new RetrieverClient({ apiKey, baseUrl })` and starts making RAG queries. All list endpoints support cursor-based pagination. Rate limit headers are standardized.

**Targets:**
- ✅ TypeScript SDK (`packages/retriever-client-js/`): typed fetch-based client. Methods for chat, document upload, search.
- ✅ SDK handles `X-API-Key` and `X-User-ID` headers automatically.
- ✅ Auto-generate OpenAPI 3.1 spec from FastAPI routes.
- ✅ Implement cursor-based pagination on document list, message history, tenant list (admin).
- ✅ Standardize rate limit response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).
- ✅ Add `Idempotency-Key` support on document upload endpoints.
- ✅ Quickstart guide: "Add Retriever to any frontend in 5 minutes."
- ✅ Integration test using the SDK against live API (verified passing).

**Acceptance Criteria:**
- ✅ SDK can execute every documented API operation.
- ✅ All list endpoints return `pagination` block with `nextCursor`, `limit`, `hasMore`.
- ✅ Integration test passes in CI.

---

### [Completed] Milestone 12: Production Storage

**Objective:** Replace local filesystem storage with S3/MinIO. Encrypt persisted LLM keys. Tune connection pools for production traffic.

**Prerequisites:** M9 (per-tenant config foundation).

**Complexity:** Medium

**Dependencies:** M9

**Expected Outcome:** All document storage goes through S3/MinIO with tenant-prefixed buckets. LLM keys are encrypted at rest. Connection pooling is auto-tuned.

**Targets:**
- ✅ S3/MinIO adapter: implements `DocumentStorage` port. Tenant-prefixed bucket paths (`/{tenant_id}/documents/{doc_id}.pdf`).
- ✅ Encrypted tenant config fields: `llm_api_key` stored encrypted (AES-256-GCM) with a `key_encryption_key` env var.
- ✅ Migration path: existing local files stay accessible while new uploads go to S3.
- ✅ Connection pool sizing: benchmark and set optimal `pool_size`, `max_overflow`, `pool_timeout` for asyncpg.
- ✅ Storage health check: verify S3/MinIO reachability in `/health` endpoint.
- ✅ Document download/presigned URL endpoint for admin dashboard.

**Acceptance Criteria:**
- ✅ Uploaded documents are readable from S3/MinIO, isolated by tenant prefix.
- ✅ Encrypted LLM key in DB is decryptable only with the server-side KEK; a DB dump alone yields ciphertext.
- ✅ Connection pool does not exhaust under concurrent load.

---

### [Completed] Milestone 13: Multi-Industry Configurability

**Objective:** Enable different clients (coaching, legal, CA) to run with different chunking, metadata, guardrails, and citation formats — all configured at runtime, no code changes.

**Prerequisites:** M3 (CAD system), M9 (per-tenant config).

**Complexity:** Extra Large

**Dependencies:** M9

**Expected Outcome:** A legal tenant and a coaching tenant can use the same Retriever instance with completely different chunk granularity, metadata schemas, and prompt guardrails.

**Targets:**
- ✅ Pluggable chunking strategies per tenant (semantic splitting, recursive character, fixed-token sliding window).
- ✅ Pluggable metadata extractors per document type (extract dates, case numbers, contract clauses).
- ✅ Pluggable input/output guardrails per tenant (PII redaction, prompt injection detection, output content filtering).
- ✅ Industry template packs: pre-built configuration bundles for legal, medical, finance, HR, education. Config only — no code changes.
- ✅ Citation format customization per tenant (e.g., `[Source: doc_id, page N]` vs `(see exhibit A)`).
- ✅ Per-tenant model routing: different LLM for different query intents (summarization vs analysis vs extraction).
- ✅ Document type detection and routing to appropriate parser (PDF, DOCX, HTML, Markdown, code).

**Acceptance Criteria:**
- ✅ Two tenants with different industry profiles produce different chunk granularity for the same document.
- ✅ A new document type is supported by adding a config entry and a parser adapter — no domain code changes.
- ✅ Guardrail violations are logged per tenant and can trigger different actions (block, warn, redact).

---

### [Completed] Milestone 14: Performance & Scale

**Objective:** Optimize for production traffic. Measure, find bottlenecks, fix them, verify with benchmarks.

**Prerequisites:** M11 (stable API surface), M12 (production storage).

**Complexity:** Large

**Dependencies:** M11, M12

**Expected Outcome:** The platform handles 200 concurrent search requests under 150ms latency budget.

**Targets:**
- ✅ HNSW index tuning: benchmark `m` and `ef_construction` parameters for optimal recall/latency tradeoff.
- ✅ Semantic query result cache: cache vector search results for semantically identical queries (cosine similarity > 0.99).
- ✅ Connection pool sizing benchmarks and auto-tuning.
- ✅ Chunk-level batch operations for bulk document ingest (reduce per-chunk transaction overhead).
- ✅ SSE connection lifecycle management: handle client disconnect cleanup, backpressure on slow consumers.
- ✅ Memory profiling under concurrent load: identify leaks in streaming responses, connection pools, async task accumulation.
- ✅ Cold-start optimization: lazy adapter initialization, connection pooling warmup on boot.
- ✅ Token budget compression benchmarks: measure latency savings vs quality impact of aggressive compression.

**Acceptance Criteria:**
- ✅ k6 benchmark: p95 latency < 150ms for search at 200 concurrent connections.
- ✅ SSE streaming starts first token within 500ms (per latency budget).
- ✅ Bulk ingest of 1000 documents completes without OOM or connection pool exhaustion.

---

### [Completed] Milestone 15: Enterprise Readiness

**Objective:** Meet enterprise compliance, security, and operational requirements. SOC 2 alignment, SSO, RBAC expansion, data lifecycle management.

**Prerequisites:** M9-M14.

**Complexity:** Extra Large

**Dependencies:** M9, M11, M12, M13, M14

**Expected Outcome:** The platform can be deployed in regulated environments with documented compliance posture.

**Targets:**
- ✅ SSO/OIDC integration: support external identity providers for admin dashboard login.
- ✅ Role-based access expansion: read-only API keys, scope granularity (per-document-type, per-collection).
- ✅ Data retention policies per tenant: auto-expire documents, sessions, inference logs based on configurable TTL.
- ✅ Backup/restore procedures documented and tested: PostgreSQL dump/restore, Redis RDB snapshots, vector index rebuild from chunks.
- ✅ Immutable audit trail: audit logs are append-only with cryptographic chain (hash-linked entries).
- ✅ Encryption at rest verification: document storage encryption, database encryption.
- ✅ Rate limit enforcement at tenant level (not just global).

**Acceptance Criteria:**
- ✅ SOC 2 evidence package can be generated from audit logs and deployment documentation.
- ✅ SSO integration with at least one provider (Okta, Auth0, or Azure AD).
- ✅ Backup/restore drill completes with zero data loss.
- ✅ Data retention enforcement verified: expired documents are auto-deleted.

---

## Cross-Cutting Concerns

These are tracked across all milestones and are not individual deliverables:

| Concern | Owner | Verification |
|---|---|---|
| **RAG Quality** | All milestones | Ragas evaluation: faithfulness > 0.95, answer relevance > 0.90, context recall > 0.92. Evaluated on golden dataset after every M13+ change. |
| **Security** | All milestones | RLS enforcement verified on every new table. No secrets in logs. No hardcoded prompts. Architecture conformance tests block regressions. |
| **Backward Compatibility** | M11+ | SDK versioning follows semver. API version prefix (`/v1/`) maintained. Deprecation policy documented. |
| **Documentation** | All milestones | Every API endpoint documented. Architecture decisions recorded as ADRs. Deployment and integration guides maintained. |
