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
| **M16** | User Feedback & Quality Loops | Thumbs up/down endpoints, rating logs, admin dashboard analytics | **Completed** | Q4 2027 |
| **M17** | Secure Document Distribution | Client-scoped document download links, temporary presigned R2/S3 URLs | **Completed** | Q4 2027 |
| **M18** | Metadata & Tag Filtering | Tag/Collection-based search filtering, advanced boolean queries | **Completed** | Q1 2028 |
| **M19** | Smart Model Failover | Auto-retry on provider downtime, multi-LLM dynamic translation routing | **Completed** | Q1 2028 |
| **M20** | Token Cost Optimization | Long chat history summarization compression, token billing tracking | **Completed** | Q2 2028 |
| **M21** | Web Search Grounding | Tavily/Brave Search fallback APIs, dynamic internet context injections | **Completed** | Q2 2028 |
| **M22** | Structured Data Extraction | JSON Schema-based document parsing endpoints, structured LLM outputs | **Completed** | Q3 2028 |
| **M23** | Multi-Modal Processing | Image & scanned PDF OCR pipelines, vision-model page descriptors | **Completed** | Q3 2028 |
| **M24** | Self-Querying Retrieval | Natural language query translation, SQL metadata filter compilers | **Completed** | Q4 2028 |
| **M25** | SaaS Tenant Resource Quotas | Hard/soft limits on files, storage, and tokens, 402/429 status hooks | **Planned** | Q4 2028 |
| **M26** | Multi-Workspace Collections | Tenant sub-partitioning, workspace-scoped vector and GIN queries | **Planned** | Q1 2029 |
| **M27** | Interactive Chunking Auditor | Sandbox chunk-preview APIs, visual text highlight chunk dividers | **Planned** | Q1 2029 |
| **M28** | A/B Testing Platform | Create/start/stop experiments via admin API, per-variant metrics dashboard | **Planned** | Q2 2029 |

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

### [Completed] Milestone 9: Client Hierarchy & Admin API

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

### [Completed] Milestone 16: User Feedback & Quality Loops

**Objective:** Capture and analyze end-user feedback on RAG replies directly in production, enabling quality analytics inside the Admin Dashboard.

**Complexity:** Medium

**Dependencies:** M9, M10, M11

**Targets:**
- Create `FeedbackDb` relational schema scoped by tenant and linked to `chat_messages`.
- Implement client-scoped feedback submission endpoint: `POST /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages/{messageId}/feedback`.
- Add feedback statistics (thumbs up/down ratio, common negative flags) and custom text comments search tool inside the Admin Dashboard.

**Acceptance Criteria:**
- Feedback submission validates the message exists and belongs to the active tenant/user.
- Dashboard renders real-time quality curves based on logged ratings.

---

### [Completed] Milestone 17: Secure Document Distribution

**Objective:** Safely serve source document downloads to authenticated mobile and web users using secure, temporary links, resolving citation file clicks.

**Complexity:** Medium

**Dependencies:** M12, M15

**Targets:**
- Implement client-scoped file access validation endpoint: `GET /v1/tenants/{tenantId}/documents/{documentId}/download-url`.
- Implement `S3Storage.generate_presigned_url` method returning temporary access tokens (e.g. 5-minute expiry).
- Integrate Cloudflare R2 signature policies for expiring downloads.

**Acceptance Criteria:**
- Requesting download URLs without valid user JWT fails with 401.
- Generated URLs expire and refuse access immediately after configured timeout (e.g., 5 mins).

---

### [Completed] Milestone 18: Metadata & Tag Filtering

**Objective:** Enable users to restrict search and chat queries to specific document tags, collections, or custom fields.

**Complexity:** Medium

**Dependencies:** M11, M13

**Targets:**
- ✅ Typed `MetadataFilter` Pydantic model with 10 operators (`eq`, `neq`, `in`, `gt`, `gte`, `lt`, `lte`, `exists`, `contains`, `regex`).
- ✅ `tags: list[str]` field on documents — new `TEXT[]` column + GIN index.
- ✅ Document-level tag filtering via `JOIN documents ... d.tags @> ARRAY[:tags]` in both vector and keyword search legs.
- ✅ Chunk-level metadata filtering with rich operators (`->>` for scalar, `?|` for array, `@>` for containment, `~*` for regex, `?` for key-existence).
- ✅ Shared `build_filter_clause()` in `adapters/vector/filter_builder.py` — deduplicated from two copies to one.
- ✅ GIN index `ix_document_chunks_meta_data` on `meta_data` JSONB column for index-scan performance.
- ✅ Filters and tags wired into both `SearchRequest` (`POST /v1/tenants/{tenantId}/search`) and `ChatMessageRequest` (`POST .../chat/sessions/{sessionId}/messages`).
- ✅ TypeScript SDK updated: `MetadataFilter` type + `filters`/`tags` params on `search()`, `chat()`, `chatStream()`.
- ✅ Alembic migration `4a2b3c5d6e7f` for `documents.tags` column + both GIN indexes.
- ✅ 18 new tests covering all filter operators, tag filtering, combined filters, and domain model defaults.
- ✅ 173/173 tests passing (was 155).

**Acceptance Criteria:**
- ✅ Querying with `tags: ["financial_statements"]` returns only chunks belonging to matching documents (verified by test).
- ✅ Search queries with metadata filters maintain p95 latency < 150ms (GIN index covers JSONB operators).

---

### [Completed] Milestone 19: Smart Model Failover

**Objective:** Build high availability into the inference engine to dynamically recover from third-party LLM outages without client downtime.

**Complexity:** Medium

**Dependencies:** M6, M13

**Deliverables:**
- ✅ `ProviderUnavailableError` exception — adapters catch retryable SDK errors (timeout, connection, 5xx, rate limit) and raise this.
- ✅ `fallback_provider`, `fallback_model`, `retry_attempts`, `retry_delay_ms` on `AIProviderConfig`.
- ✅ `InferenceLog.notes` field for telemetry.
- ✅ OpenAI adapter: catches `InternalServerError`, `APITimeoutError`, `APIConnectionError`, `RateLimitError` → `ProviderUnavailableError`. Auth errors (401) propagate correctly.
- ✅ Anthropic adapter: same pattern with `InternalServerError`, `OverloadedError`, `APITimeoutError`, `APIConnectionError`, `RateLimitError`.
- ✅ `RoutingLLMProvider` retries primary with exponential backoff, then falls back to secondary provider. Injects `_actual_provider` in config dict + info events in stream.
- ✅ `InferenceOrchestrator` reads `_actual_provider` → logs in `notes`.
- ✅ 16 tests covering retry, fallback, all-providers-down, non-retryable passthrough, streaming failover, adapter error wrapping.

**Acceptance Criteria:**
- ✅ Primary provider timeout triggers retry (2 attempts with backoff), then fallback to secondary provider.
- ✅ Fallback events are logged in telemetry with `actual_provider=` in notes.

---

### [Completed] Milestone 20: Token Cost Optimization

**Objective:** Control input token billing on long chat sessions by introducing context summarization compression.

**Complexity:** Large

**Dependencies:** M6, M14

**Deliverables:**
- ✅ `ModelPricing` schema (`input_cost_per_1k`, `output_cost_per_1k`) + `DEFAULT_PRICING` dict covering gemini, gpt-4o, claude models on `AIProviderConfig.pricing`.
- ✅ `cost_usd: float` on `Usage`, `InferenceLog`, and `InferenceLogDb` + Alembic migration `7b3c4d5e6f8g`.
- ✅ `cost_calculator.py` utility: apply model pricing to token counts.
- ✅ Orchestrator calculates cost post-inference and logs it; increments `TOKEN_CONSUMPTION` (input/output) and `COST_SPEND` Prometheus counters.
- ✅ `MetricsRegistry` injected into orchestrator constructor (optional, defaults to None).
- ✅ Conversation summarizer: `_summarize_history` compresses history older than `summarize_after_turns` (default 15) into a single summary via the LLM. Configured via `RetrievalSettings.summarize_after_turns`. Applied in both `generate()` and `generate_stream()`. Fails safe on LLM error.
- ✅ Anthropic streaming now captures usage from `message_delta` events.
- ✅ 14 tests covering pricing config, cost calculation, metrics emission, summarization trigger/skip, and anthropic streaming usage.

**Acceptance Criteria:**
- ✅ Chats extending to 50+ messages trigger summarization, reducing context window usage.
- ✅ Token cost is tracked per-inference and available in `InferenceLog.cost_usd`.

---

### [Completed] Milestone 21: Web Search Grounding

**Objective:** Fallback to live web search results when the local database does not contain relevant context chunks.

**Complexity:** Large

**Dependencies:** M5, M6

**Deliverables:**
- ✅ `WebSearchProvider` port with `WebSearchResult` model — abstract `search(query, max_results)` method.
- ✅ `TavilySearchAdapter` — calls `api.tavily.com/search` via httpx, returns clean content. Graceful no-op when API key is empty.
- ✅ `enable_web_search` flag on `FeatureFlags`, plus `web_search_threshold`, `web_search_provider`, `web_search_max_results` on `RetrievalSettings`.
- ✅ `HybridSearchService.search()`: after local search, if top score < threshold, fires web search and appends results with scores below local max. Sorts and trims to `top_k`. Fails safe on API errors.
- ✅ `TAVILY_API_KEY` env var in `settings.py`, wired into `main.py`.
- ✅ Web search fields passed through `SearchQuery` in both search and chat endpoints.
- ✅ 12 tests covering port defaults, Tavily adapter, config fields, low-score trigger, high-score skip, flag-off skip, graceful degradation, and no-web-provider case.

**Acceptance Criteria:**
- ✅ Queries on topics not in local documents (scores < 0.65) trigger Tavily web search.
- ✅ Web results appear as `[Web: Title](url)` citations in the LLM prompt.

---

### [Completed] Milestone 22: Structured Data Extraction

**Objective:** Extract clean, structured JSON payloads directly from unstructured documents using client-specified JSON schemas.

**Complexity:** Medium

**Dependencies:** M11, M13

**Deliverables:**
- `DocumentChunk` domain model confirmed; `get_document_chunks` method on `DocumentRepository` port and `SqlDocumentRepository` adapter.
- `json_schema` field on `InferenceRequest` wired into OpenAI adapter (`response_format={"type": "json_object"}`) and Anthropic adapter (schema appended to system prompt).
- New extraction endpoint: `POST /v1/tenants/{tenantId}/documents/{documentId}/extract` with `ExtractRequest`/`ExtractResponse` DTOs.
- LLM response parsed as JSON; invalid JSON returns 422.

**Acceptance Criteria:**
- Extraction API returns valid JSON output conforming to input schemas.
- Adapters respect `json_schema` field and configure provider accordingly.
- 215+ tests passing.

---

### [Completed] Milestone 23: Multi-Modal Processing

**Objective:** Add OCR and vision support for scanned PDFs and image files during worker ingestion.

**Complexity:** Large

**Dependencies:** M4, M12

**Deliverables:**
- `ChatMessage.images: list[dict]` field added to domain model; `model_dump()` backward-compatible (empty list = string content).
- OpenAI adapter converts `images` to content blocks (`text` + `image_url`) when present; `generate_stream` similarly wired.
- Anthropic adapter converts `images` to Anthropic content blocks (`text` + `image` with base64 source) when present.
- `AIProviderConfig.vision_model` config field (default `gpt-4o`); `Settings.VISION_MODEL` env var.
- Worker extraction pipeline: `mime_type` passed from upload endpoint to Celery task. New `_describe_with_vision()` function in worker calls OpenAI vision API for images and zero-text PDFs (first page).
- `Pillow>=10.0.0`, `openai>=1.0.0` added to worker deps.

**Acceptance Criteria:**
- Uploaded JPEG/PNG images are processed, described, chunked, and indexed.
- Scanned PDFs (zero extractable text) fall through to vision LLM (first page described).
- Text PDFs and plain text files unaffected (no regression).
- 286+ tests passing.

---

### [Completed] Milestone 24: Self-Querying Retrieval

**Objective:** Convert natural language search queries into structured database metadata filters.

**Complexity:** Medium

**Dependencies:** M5, M18

**Deliverables:**
- `SelfQueryProvider` port + `LLMSelfQueryAdapter` — parses natural language into `MetadataFilter` list via LLM (gemini-1.5-flash, 2s timeout, structured JSON output).
- Wired into `HybridSearchService` as step 0: parsed filters merged with existing filters before fan-out search.
- Auto-retry/fallback: adapter returns empty list on any failure (timeout, invalid JSON, LLM error).
- Query rewriting (HyDE) reuses the same pattern via `QueryRewriterProvider` + `LLMQueryRewriterAdapter`, generating a hypothetical document for embedding.
- Full integration coverage with 9 tests.

**Acceptance Criteria:**
- ✅ Querying "invoices from 2025" appends `[{"field": "doc_type", "eq": "invoice"}, {"field": "date_reference", "eq": "2025"}]` filters to the search.
- ✅ On LLM timeout/crash, search proceeds without filters (graceful degradation).
- ✅ 312+ tests passing.

---

### [Planned] Milestone 25: SaaS Tenant Resource Quotas

**Objective:** Enforce SaaS resource limits (file counts, storage volumes, token budgets) at the tenant API level.

**Complexity:** Medium

**Dependencies:** M9, M15

**Targets:**
- Add limits configuration schemas (`max_documents`, `max_storage_bytes`, `monthly_token_budget`) to `tenant_configs` DB table.
- Implement quota validation hooks on document upload and chat message API endpoints.
- Trigger `402 Payment Required` or `429 Quota Exceeded` exceptions when thresholds are crossed.

**Acceptance Criteria:**
- Uploading documents beyond the tenant's configured limit is blocked and throws 402.

---

### [Planned] Milestone 26: Multi-Workspace Collections

**Objective:** Allow tenants to partition their documents into isolated collections/workspaces.

**Complexity:** Medium

**Dependencies:** M9, M13, M18

**Targets:**
- Add `collection_id` uuid column to `documents`, `document_chunks`, and `vector_records`.
- Update API endpoints to accept optional `collection_id` scoping parameters.
- Restrict vector and hybrid search queries to matching collection boundaries.

**Acceptance Criteria:**
- Search and chat queries within collection "Legal" never return search chunks from collection "HR".

---

### [Planned] Milestone 27: Interactive Chunking Auditor

**Objective:** Provide administrative users with a visual preview sandbox to audit document chunking splits before indexing.

**Complexity:** Medium

**Dependencies:** M10, M13

**Targets:**
- Implement chunk preview API: `POST /v1/admin/tenants/{tenantId}/documents/chunk-preview`.
- Calculate character and token bounds for different parsing algorithms (character, semantic, recursive) dynamically.
- Build visual highlighting highlighting chunk dividers in the Admin Dashboard playground.

**Acceptance Criteria:**
- Auditor endpoint returns exact split positions and token size estimations for visual dashboard rendering.

---

### [Planned] Milestone 28: A/B Testing Platform

**Objective:** Full experiment management lifecycle — create, start, stop experiments via admin API, with dashboard visibility into variant performance.

**Complexity:** Large

**Dependencies:** M10 (admin dashboard), E-5 minimal (foundation)

**Targets:**
- `experiments` DB table: `experiment_id`, `tenant_id`, `name`, `status` (draft/running/stopped), `variants` JSONB, `created_at`, `started_at`, `stopped_at`.
- Admin CRUD API: create/edit/start/stop experiments.
- `experiment_id` + `variant` columns on `inference_logs` and `chat_message_feedback`.
- Admin Dashboard: experiment list view, per-variant metrics (cost, latency, feedback scores).
- Statistical significance calculation (chi-square or Bayesian) between control & treatment.
- Auto-stop on detected regression (negative impact > 5% with 95% confidence).

**Acceptance Criteria:**
- Admin can create an experiment, start it, see live per-variant metrics in the dashboard.
- Stopping an experiment immediately routes all traffic back to the control config.
- Dashboard shows "Statistically significant improvement" or "No significant difference" per metric.

---

## Cross-Cutting Concerns

These are tracked across all milestones and are not individual deliverables:

| Concern | Owner | Verification |
|---|---|---|
| **RAG Quality** | All milestones | Ragas evaluation: faithfulness > 0.95, answer relevance > 0.90, context recall > 0.92. Evaluated on golden dataset after every M13+ change. |
| **Security** | All milestones | RLS enforcement verified on every new table. No secrets in logs. No hardcoded prompts. Architecture conformance tests block regressions. |
| **Backward Compatibility** | M11+ | SDK versioning follows semver. API version prefix (`/v1/`) maintained. Deprecation policy documented. |
| **Documentation** | All milestones | Every API endpoint documented. Architecture decisions recorded as ADRs. Deployment and integration guides maintained. |
