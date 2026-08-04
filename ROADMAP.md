# Product Roadmap

This document outlines the implementation phases and milestones for the Retriever platform.

---

## Roadmap Overview

| Milestone | Title | Focus Area | Status |
|---|---|---|---|
| **M1** | Repository Foundation | Directory layout, configurations, CI/CD, linting, Docker environment | **Completed** |
| **M2** | Authentication & Tenant Foundation | Identity interfaces, relational schemas, Postgres RLS contexts, API keys, cache | **Completed** |
| **M3** | Configuration & Platform Infrastructure | Global/Tenant configurations, database JSONB overrides, environment fallbacks | **Completed** |
| **M4** | Document Ingestion & Storage | Parsing tasks, unstructured layouts, chunking, event broker lifecycle | **Completed** |
| **M5** | Retrieval, Fusion & Rerank | pgvector indexes, hybrid search, Reciprocal Rank Fusion, Cohere reranking | **Completed** |
| **M6** | Generative Inference & Citations | LLM adapters, prompt orchestrations, context window packing, citation audits | **Completed** |
| **M7** | Observability & Hardening | Structured logging, Prometheus metrics, OTel tracing, rate limiting | **Completed** |
| **M8** | Production Hardening | DB bootstrap fixes, worker consolidation, shared packages, architecture tests | **Completed** |
| **M9** | Client Hierarchy & Admin API | Users table, sub-client RLS, per-tenant LLM keys, admin API scoping, CRUD endpoints | **Completed** |
| **M10** | Admin Dashboard | Next.js admin UI for platform management (tenants, users, configs, onboarding, playground) | *Completed* |
| **M11** | Client SDK & API Surface | JS/TS RetrieverClient, OpenAPI 3.1 spec, pagination, rate limit headers | **Completed** |
| **M12** | Production Storage | S3/MinIO adapter, encrypted key persistence, connection pool tuning | **Completed** |
| **M13** | Multi-Industry Configurability | Per-tenant chunking, metadata extractors, guardrails, citation formatting | **Completed** |
| **M14** | Performance & Scale | HNSW tuning, semantic cache, bulk ingest, SSE lifecycle, memory profiling | **Completed** |
| **M15** | Enterprise Readiness | Audit log writer, SSO/OIDC, RBAC, data retention, backup/restore, compliance | **Completed** |
| **M16** | User Feedback & Quality Loops | Thumbs up/down endpoints, rating logs, admin dashboard analytics | **Completed** |
| **M17** | Secure Document Distribution | Client-scoped document download links, temporary presigned R2/S3 URLs | **Completed** |
| **M18** | Metadata & Tag Filtering | Tag/Collection-based search filtering, advanced boolean queries | **Completed** |
| **M19** | Smart Model Failover | Auto-retry on provider downtime, multi-LLM dynamic translation routing | **Completed** |
| **M20** | Token Cost Optimization | Long chat history summarization compression, token billing tracking | **Completed** |
| **M21** | Web Search Grounding | Tavily/Brave Search fallback APIs, dynamic internet context injections | **Completed** |
| **M22** | Structured Data Extraction | JSON Schema-based document parsing endpoints, structured LLM outputs | **Completed** |
| **M23** | Multi-Modal Processing | Image & scanned PDF OCR pipelines, vision-model page descriptors | **Completed** |
| **M24** | Self-Querying Retrieval | Natural language query translation, SQL metadata filter compilers | **Completed** |
| **M25** | Developer Console & Local Ingestion | Next.js Developer Console, local Ollama RAG ingestion, RLS verification | **Completed** |
| **M26** | SaaS Tenant Resource Quotas | Hard/soft limits on files, storage, and tokens, 402/429 status hooks | **Completed** |
| **M27** | Multi-Workspace Collections | Tenant sub-partitioning, workspace-scoped vector and GIN queries | **Completed** |
| **M28** | Interactive Chunking Auditor | Sandbox chunk-preview APIs, visual text highlight chunk dividers | **Completed** |
| **M29** | A/B Testing Platform | Create/start/stop experiments via admin API, per-variant metrics dashboard | **Completed** |
| **M30** | Production Polish | Deployment hardening, observability, CI/CD, secrets management, docs alignment | **Completed** |
| **M31** | Security Hardening & Secrets Remediation | Credential rotation, fail-safe defaults, proxy validation, port hardening | *Completed* |
| **M32** | Onboarding & Client UX Overhaul | User creation in wizard, fixed form defaults, short IDs, admin UX polish | *Completed* |
| **M33** | Code Quality & Architecture | Split main.py, shared TypeScript types, consolidate constants, clean up clients | *Completed* |
| **M34** | Production Operations & DevOps | Auto-deploy pipeline, Sentry, uptime monitoring, pagination | *Completed* |
| **M35** | Final Polish & Infrastructure Self-Detection | Server-spec auto-detection, model updates, docker infrastructure removal | *Completed* |
| **M36** | SaaS Data Connectors Framework | WebCrawler + cloud-drive connectors, admin CRUD, sync ingestion | **Completed** |
| **M37** | GraphRAG & Knowledge Graph Indexing | Entity-relationship graph extraction and hybrid graph+vector reasoning | **Completed** |
| **M38** | Critical Security Remediation | Google OAuth verification, JWT secret, SQL-injection-safe filters, file-serve traversal & HMAC hardening, upload caps, RLS coverage, error redaction | **Completed** (v0.36.0) |
| **M39** | Agentic Workflow Execution Engine | Autonomous multi-step tool calling and agent execution loops | **Planned** |
| **M40** | Layout-Aware Vision OCR & Table Parsing | Replace PyPDF2 with Docling/Unstructured layout-aware OCR for scanned PDFs & tables | **Planned** |
| **M41** | Chunk-Level Granular Access Control (ACL) | Add allowed_roles/allowed_users to chunk metadata & enforce DB engine RLS | **Planned** |
| **M42** | Active Real-Time LLM Safety Guardrails | Integrate Llama Guard / NeMo for prompt injection, jailbreak, and output safety | **Planned** |
| **M43** | Online Production Hallucination Tracing | Continuous real-time faithfulness & context relevance scoring on live API streams | **Planned** |
| **M44** | Learned Sparse (SPLADE) & Reranker Microservice | Upgrade sparse search to SPLADE / Qdrant and offload Cross-Encoder to GPU worker | **Planned** |
| **M45** | Context Compression & Zero-Trust Encryption | Implement LongLLMLingua chunk compression and envelope encryption for vector/text storage | **Planned** |
| **M46** | Dynamic Multi-Embedding Vector Schemas | Dynamic vector table partitioning for variable model dimensions (768, 1536, 3072) | **Planned** |
| **M47** | Multi-Agent Consensus & Critic Reflection | Generator vs. Critic multi-agent reflection loops for high-stakes enterprise verification | **Planned** |
| **M48** | Compliance & Data Sovereignty Lifecycle | Automated GDPR vector purge, data retention schedulers, and zero-footprint PII redaction | **Planned** |
| **M49** | GraphRAG Productionization & Retrieval Integration | Neo4j driver dependency + connectivity, graph-evidence wiring into search/chat, fix verified M37 defects (document_id no-op delete, silent extractor failures) | **Planned** |

---

## Detailed Milestone Targets

### [Completed] Milestone 1: Repository Foundation
- Establish workspace structure for FastAPI, Next.js, and background workers.
- Setup Ruff formatting and TypeScript linting boundaries.
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
- S3-compatible presigned URLs (covers AWS S3 / MinIO / Cloudflare R2) for expiring downloads.

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

### [Completed] Milestone 25: Developer Console & Local Ingestion

**Objective:** Build a Next.js Developer Console with a local Ollama indexing pipeline and validate dynamic configuration fallback logic.

**Complexity:** Medium

**Dependencies:** M10, M11

**Targets:**
- Bootstrapped `apps/developer-console` using Next.js 16 and `@prat3010/retriever-client-js`.
- Configured local Ollama embeddings (`nomic-embed-text`) inside `ingest_self.py` to index the codebase.
- Enforced platform key access rules matching backend endpoint API validation.
- Implemented chat playground with real-time SSE token stream rendering.

---

### [Completed] Milestone 26: SaaS Tenant Resource Quotas

**Objective:** Enforce SaaS resource limits (file counts, storage volumes, token budgets, daily requests) at the tenant API level.

**Complexity:** Medium

**Dependencies:** M9, M15

**Targets:**
- ✅ Add limits configuration schemas (`max_documents`, `max_storage_bytes`, `max_monthly_tokens`, `max_daily_requests`, `soft_limit_percentage`) to `TenantQuotaSettings`.
- ✅ Implement `QuotaService` domain component and `SqlQuotaRepository` adapter for real-time usage calculation.
- ✅ Implement quota validation hooks on document upload (`/v1/documents`) and chat message (`/v1/chat`) API endpoints.
- ✅ Trigger `402 Payment Required` or `429 Quota Exceeded` exceptions with quota response headers (`Quota-Exceeded-Resource`, `Quota-Limit`, `Quota-Usage`).
- ✅ Attach `X-Quota-Warning` header when soft limit percentage is crossed.

**Acceptance Criteria:**
- ✅ Uploading documents beyond the tenant's configured limit is blocked and throws 402 Payment Required.
- ✅ Exceeding token or request budgets returns 429 Too Many Requests.
- ✅ 7/7 unit tests pass in `test_tenant_quotas.py`.

---

### [Completed] Milestone 27: Multi-Workspace Collections

**Objective:** Allow tenants to partition their documents into isolated collections/workspaces.

**Complexity:** Medium

**Dependencies:** M9, M13, M18

**Targets:**
- ✅ Add `collection_id` uuid column to `documents`, `document_chunks`, and `vector_records` tables with indexing.
- ✅ Update document upload, list, search, and chat API endpoints to accept optional `collectionId` scoping parameters.
- ✅ Restrict vector (`pgvector`), sparse (`tsvector`), and hybrid search queries to matching collection boundaries when specified.
- ✅ Inherit `collection_id` from document down to generated chunks and vector embeddings during ingestion.

**Acceptance Criteria:**
- ✅ Search and chat queries within collection "Legal" never return search chunks from collection "HR".
- ✅ 6/6 unit tests pass in `test_workspace_collections.py`.

---

### [Completed] Milestone 28: Interactive Chunking Auditor

**Objective:** Provide administrative users with a visual preview sandbox to audit document chunking splits before indexing.

**Complexity:** Medium

**Dependencies:** M10, M13

**Targets:**
- ✅ Implement chunk preview sandbox API: `POST /v1/admin/tenants/{tenantId}/documents/chunk-preview`.
- ✅ Build `ChunkerFactory` supporting `sliding`, `semantic`, and `hierarchical` chunking strategies.
- ✅ Calculate character start/end index offsets (`startCharIdx`, `endCharIdx`), character lengths, and token counts without database or vector store side effects.
- ✅ Expose structured preview payloads (`totalChunks`, `totalTokens`, `totalChars`, `avgChunkTokens`) for administrative auditor inspection.

**Acceptance Criteria:**
- ✅ Auditor endpoint returns exact split positions and token size estimations for visual dashboard rendering.
- ✅ 5/5 unit tests pass in `test_chunking_auditor.py`.

---

### [Completed] Milestone 29: A/B Testing Platform

**Objective:** Full experiment management lifecycle — create, start, stop experiments via admin API, with per-variant performance telemetry.

**Complexity:** Medium

**Dependencies:** M10, M14, M19

**Targets:**
- ✅ Admin experiment CRUD APIs: `GET`, `POST`, `PUT`, `DELETE` `/v1/admin/tenants/{tenantId}/experiments`.
- ✅ Status lifecycle management: `POST /v1/admin/tenants/{tenantId}/experiments/{experimentId}/status` (`draft`, `active`, `paused`, `completed`).
- ✅ Per-variant metrics aggregation: `GET /v1/admin/tenants/{tenantId}/experiments/{experimentId}/metrics` (requests, tokens, avg/p95 latency).
- ✅ Deterministic variant allocation (`assign_variant`) and overrides (`apply_overrides`) in both `chat` and `search` routers.

**Acceptance Criteria:**
- ✅ Admin can create, start, pause, edit, delete, and inspect per-variant metrics for A/B experiments.
- ✅ Pausing or stopping an experiment routes traffic back to baseline tenant configuration.
- ✅ 3/3 unit tests pass in `test_ab_testing.py`.

---

### [Completed] Milestone 30: Production Polish

**Objective:** Close the gap between a feature-complete codebase and a production-hardened deployment. Real-world Oracle VPS operation revealed gaps in deployment docs, secrets management, observability, CI/CD, and LLM key lifecycle.

**Prerequisites:** M25 (all prior features are complete).

**Complexity:** Medium

**Dependencies:** None

**Expected Outcome:** Deployment topology documented accurately; secrets managed via .env with rotation process; basic monitoring and alerting active; CI/CD pipeline exists; LLM API key provisioning is documented and repeatable.

**Targets:**
- ✅ Real deployment topology documented: Oracle VPS, systemd, nginx reverse proxy, Let's Encrypt SSL, Ollama sidecar — replaces stale K8s/Docker references.
- ✅ Secrets management: all env vars in single `.env` on server; encrypted LLM keys at rest (AES-256-GCM KEK verified in code); rotation process documented.
- ✅ Observability: `/metrics` endpoint exposed and reachable via https (verified `curl https://rag.prateeq.in/metrics` → 200); **Sentry configured** (DSN live, EU region, test error ingested 2026-07-31); uptime monitoring ⬜ unverifiable (external service).
- ✅ Basic alerting: `scripts/quota-alert.sh` — daily cron check of LLM key usage (OpenRouter `/auth/key`), ntfy.sh push + optional webhook when remaining < 20%/10%. ⚠️ Platform key is currently free-tier → reports "not monitorable"; monitorable once a prepaid key is used.
- ✅ Backup automation: `scripts/backup-db.sh` — nightly cron (02:30 UTC), per-table gzipped CSV over the Supabase pooler (pg_dump incompatible with pgbouncer), 14-day retention, manifest per run. Verified: 20 tables backed up. Restore procedure in DEPLOYMENT.md (schema rebuilt via Alembic).
- ✅ CI/CD: GitHub Actions workflow for deploy (`deploy-api.yml` — SSH + `systemctl restart` + post-deploy smoke test); all secrets configured (verified `ORACLE_HOST/USER/SSH_KEY/PORT` in GitHub secrets).
- ✅ Nginx hardening: rate limiting (`20r/s` zone, burst 40) + HSTS/CSP/nosniff/DENY headers verified live; fail2ban `sshd` jail active (maxretry 4, bantime 1h).
- ✅ LLM key operational process: documented how to provision a new key, update tenant config, and verify chat works end-to-end (DEPLOYMENT.md provisioning checklist).
- ✅ Staging environment: documented process (local dev + CI + auto-deploy smoke test; second Oracle VM optional) in DEPLOYMENT.md.
- ✅ Root cause documentation: addendum added to DEPLOYMENT.md explaining the initial deploy chat outage (both LLM keys exhausted quota; M19 failover had no healthy fallback; lessons applied).

**Acceptance Criteria:**
- ⬜ New developer can deploy Retriever from scratch following docs alone (no tribal knowledge) — verify.
- ✅ CI/CD pipeline deploys code changes with zero manual SSH steps beyond initial setup (`deploy-api.yml` + secrets verified).
- ✅ Nightly DB backups exist with verified restore procedure — backup runs + manifests verified; restore documented.
- ✅ LLM key expiry/quota exhaustion triggers an alert before it blocks chat — quota-alert.sh + cron live (monitorable once key is prepaid).
- ✅ All architecture docs reconcile with the actual Oracle VPS topology — Render references removed (docs cleanup).

---

### [Completed] Milestone 31: Security Hardening & Secrets Remediation

**Objective:** Eliminate credential exposure in version control, enforce fail-safe production defaults, harden network perimeter, and fix weak authentication checks in the admin proxy.

**Complexity:** Medium

**Dependencies:** None

**Targets:**
- ✅ Root `.env` never committed (verified: `git log --diff-filter=A -- .env` is empty). Credential rotation of leaked Supabase DB password / OpenAI key: ⬜ still required.
- ✅ `apps/web/.env.local` scrubbed from git history (commit `53c6286`, all 148 commits, branches `main` + `decompose-main-py`) via `git-filter-repo` + force-push (2026-07-31). Token verified expired on its own (2026-07-18, `exp` claim + Vercel API 403) — rotation unnecessary. Server git objects purged (`reflog expire` + `gc --prune=now`); root `.gitignore` hardened to `.env*`.
- ✅ `@model_validator(mode="after")` in `config.py` crashes FastAPI startup with `ValueError` if `ENVIRONMENT == "production"` and `ADMIN_MASTER_KEY` or `KEY_ENCRYPTION_KEY` still have their default development values (config.py:66-84).
- ✅ SSH into Oracle VM: `ADMIN_MASTER_KEY` and `KEY_ENCRYPTION_KEY` in production `.env` are **not** default values (verified on server).
- ✅ Remove port 8000 ingress rule from Oracle Cloud security group — verified: `nc` to `130.210.35.134:8000` from external host times out (filtered); API only reachable via nginx 443/80.
- ✅ `proxy.ts`: validates `admin_key` cookie against backend `GET /v1/admin/verify-key` (5-min validated cookie cache); invalid keys are cleared and redirected to `/login` (apps/web/src/proxy.ts).

**Acceptance Criteria:**
- ✅ `git log --diff-filter=A -- .env` returns empty (no `.env` file in history) — verified.
- ✅ Starting API in production mode with default secrets raises `ValueError` and exits — verified in code.
- ✅ Port scan on Oracle VM public IP shows port 8000 as filtered/closed — verified from external host.
- ✅ Admin dashboard with random cookie string redirects to `/login` — verified in code.

---

### [Completed] Milestone 32: Onboarding & Client UX Overhaul

**Objective:** Fix the broken onboarding handoff (no user created during wizard), eliminate confusing defaults in the client login form, introduce human-friendly short IDs, and polish the admin and client UX around identity management.

**Complexity:** Medium

**Dependencies:** M9 (Users model)

**Targets:**
- ✅ **Add user creation to onboarding wizard:** Insert Step 2.5 between "API Key" and "Credentials" in `onboard/page.tsx`. Auto-create a user with the tenant name as display name. Display the real `userId` (or short ID) in the final credentials card alongside tenant ID and API key.
- ✅ **Fix client login form defaults in `RagInterface.tsx`:**
  - ✅ Set `tenantId` default to `""` (empty — force entry).
  - ✅ Set `userId` default to `""` (empty — force entry).
  - ✅ Change API key placeholder from `sk_live_...` to `ret_live_...`.
  - ✅ Keep `apiUrl` default as `https://rag.prateeq.in`.
- ⬜ **Simplify tenant and user IDs:** Frontend done (relaxed `isUuid()` to accept `tn_`/`usr_` short IDs). **Backend deferred:** add short ID columns, accept short IDs in API paths, keep UUID as internal primary key — not built.
- ✅ **Show internal User ID in Users tab:** Add a "User ID" column to `tenant-users.tsx` table with a copy-to-clipboard action so admins can easily provide it to clients.
- ✅ **Hide API Base URL field:** In `ConfigPanel`, show the API URL field only when an "Advanced" toggle is enabled. Default value stays as `https://rag.prateeq.in`.

**Documents to Update:**
- ✅ `ONBOARDING_WORKFLOW.md` — reflect the new 4-step wizard with user creation.
- ✅ `ADMIN_DASHBOARD_GUIDE.md` — update `/onboard` section to describe the new user step.
- ✅ `docs/features/admin-dashboard.md` — update agent guide.
- ✅ `Prateek_website/docs/rag-lab.md` — update Config Tab section to reflect new defaults.
- ✅ `TECH_DEBT.md` — mark onboarding gap and UX issues as resolved.

**Acceptance Criteria:**
- ✅ Onboarding a new client through the admin wizard produces a Tenant ID, User ID, and API Key — all usable immediately without visiting a separate tab.
- ✅ Client connects at `prateeq.in/rag` by entering only Tenant ID, User ID, and API Key (URL is pre-filled and can be changed via Advanced toggle).
- ⬜ Short IDs (`tn_X7kM2p`, `usr_Qp3N8w`) are accepted by both admin and client apps — partial: client accepts, backend API paths still UUID-only (deferred).
- ✅ Admin Users tab displays the internal short User ID with one-click copy.

---

### [Completed] Milestone 33: Code Quality & Architecture

**Objective:** Break down the 2,250-line `main.py` monolith, eliminate type safety gaps, consolidate duplicated constants, and clean up inconsistent patterns across both the backend and frontend codebases.

**Complexity:** Large

**Dependencies:** None

**Targets:**
- ✅ **Split `main.py` into FastAPI routers:** `routers/tenant.py`, `routers/document.py`, `routers/search.py`, `routers/chat.py`, `routers/admin.py`, `routers/health.py` — all 55+ handlers extracted; `main.py` reduced to bootstrap (170 lines); shared DI wiring moved to `container.py`.
- ✅ **Add shared TypeScript types in `rag-client.ts` or a new `rag-types.ts`:** `SearchResult { chunkId, content, score, metadata }`, `DocumentMeta { documentId, filename, status, createdAt }`, `SearchResponse { results, searchMeta? }`; `any` types and `eslint-disable` comments removed from `RagInterface.tsx`.
- ✅ **Consolidate `API_BASE` constant:** duplicate definitions removed from `onboard/page.tsx` and `login/page.tsx`; imported from `lib/api.ts` exclusively.
- ✅ **Clean up `RetrieverClient` (`rag-client.ts`):** `uploadDocument` and `deleteDocument` refactored to the shared `request<T>()` pipeline; shared auth-header helper extracted.
- ✅ **Remove duplicate cookie clearing in `sidebar.tsx`:** logout handler no longer sets `document.cookie` directly — `clearKey()` in `store/auth.ts` handles it.

**Documents to Update:**
- ✅ `docs/architecture.md` — updated for router structure.
- ✅ `TECH_DEBT.md` — main.py god-file marked resolved.
- ✅ `CHANGELOG.md` — architectural changes recorded.
- ✅ `Prateek_website/docs/rag-lab.md` — client class references updated.

**Acceptance Criteria:**
- ✅ All existing unit tests pass with the new router structure (369 at the time; current suite: 407/407).
- ✅ `RagInterface.tsx` has zero `any` types and zero `eslint-disable` comments.
- ✅ `grep -r "API_BASE" apps/web/src/ | grep -v "lib/api.ts" | grep -v node_modules` returns empty.
- ✅ `uploadDocument` and `deleteDocument` in `rag-client.ts` share the same request pipeline as other methods.

---

### [Completed] Milestone 34: Production Operations & DevOps

**Objective:** Eliminate manual SSH deploys, add error tracking and uptime monitoring, fix unbounded tenant queries, and close the remaining production operations gaps identified in the analysis.

**Complexity:** Medium

**Dependencies:** M31

**Targets:**
- ✅ **GitHub Actions auto-deploy to Oracle VM:** `.github/workflows/deploy-api.yml` exists — triggers on push to `main` affecting `apps/api/` or `packages/`, SSHes into the Oracle VM (deploy key in GitHub Secrets), pulls + restarts `retriever-api`, runs post-deploy smoke tests. All secrets configured (verified: `ORACLE_HOST/USER/SSH_KEY/PORT` in GitHub secrets).
- ✅ **Configure Sentry:** `SENTRY_DSN` set in production `.env` (EU region), app restarted, test error ingested and confirmed. ⚠️ Required fix during enablement: server had older `sentry-sdk` whose OTel integration re-export changed — import now uses `sentry_sdk.integrations.opentelemetry.integration` (main.py:40).
- ⬜ **Uptime monitoring:** Configure UptimeRobot or Better Uptime to check `https://rag.prateeq.in/health/liveness` every 5 minutes — external service, unverifiable.
- ✅ **Add pagination to `useAllTenants`:** hardcoded `?limit=1000` replaced with configurable `limit` param, default 50 (`apps/web/src/hooks/use-tenants.ts`).

**Documents to Update:**
- ⬜ `DEPLOYMENT.md` — document the auto-deploy workflow and Sentry setup — workflow exists, Sentry section pending.
- ⬜ `ORACLE_DEPLOYMENT_REFERENCE.md` — update deployment procedure to reference CI/CD — verify.
- ⬜ `TECH_DEBT.md` — mark deploy and monitoring items as resolved — verify.
- ⬜ `PROJECT_STATUS.md` — update DevOps health indicators — verify.

**Acceptance Criteria:**
- ⬜ Pushing a change to `apps/api/src/main.py` triggers the deploy workflow and restarts the API on Oracle VM within 2 minutes — workflow + secrets present, end-to-end run unverified.
- ✅ A deliberate `raise Exception("test")` in a route handler appears in Sentry within 60 seconds — verified via `sentry_sdk.capture_exception()` one-off (error "Sentry wiring test from retriever-oracle-vm" ingested).
- ⬜ UptimeRobot dashboard shows green status for `rag.prateeq.in` with 5-minute check intervals — external, unverifiable.
- ✅ `useAllTenants` no longer fetches 1000 records in a single query — verified (default 50).

---

### [Completed] Milestone 35: Final Polish & Infrastructure Self-Detection

**Objective:** Add server-spec auto-detection for infrastructure services, update stale model defaults, clean up deprecated Docker Compose syntax, and improve the client chat UI for large screens.

**Complexity:** Small

**Dependencies:** None

**Targets:**
- ⬜ **Server-spec auto-detection (`config.py`):** `InfraCapabilities` class exists — reads total RAM (`psutil.virtual_memory().total`) and CPU cores (`os.cpu_count()`) at startup and **logs** viability thresholds (Redis ≥2 GB, Broker ≥2 GB, Workers ≥4 GB + 2 cores) with boot message `INFO: Server specs: 0.9 GB RAM, 1 CPU core. Running in LEAN mode (synchronous processing).` Env overrides `REDIS_ENABLED/BROKER_ENABLED/WORKERS_ENABLED` accepted but **not yet consumed** — nothing reads these flags (known gap; wiring into `container.py` tracked separately as spec-gated deployment).
- ✅ **Update Gemini default model:** `defaultModel` for Gemini provider in `providers.ts` changed from `gemini-1.5-flash` to `gemini-2.5-flash` (verified apps/web/src/lib/providers.ts:25).
- ✅ **Remove Docker infrastructure:** `docker-compose.yml`, `Dockerfile`, `workers/Dockerfile.worker`, `apps/api/docker-compose.test.yml`, `.github/workflows/docker.yml` removed (verified — no Docker files remain in repo).
- ⬜ **Chat container height:** `max-height: min(60vh, 600px)` change unverifiable — `rag.module.css` no longer present in repo (chat UI moved/removed).

**Documents to Update:**
- ⬜ `TECH_DEBT.md` — mark all items as resolved — verify.
- ⬜ `CHANGELOG.md` — record final polish changes — verify.
- ⬜ `PROJECT_STATUS.md` — final status update across all milestones — done, but contained stale claims; corrected during docs cleanup.

**Acceptance Criteria:**
- ✅ API startup log shows correct auto-detection message for Oracle VM (0.9 GB RAM, LEAN mode) — verified (`InfraCapabilities.log_boot_status()` runs at import, config.py:146-148).
- ✅ Admin dashboard provider list shows `gemini-2.5-flash` as the default for Gemini — verified.
- ✅ No Docker files remain in repo (was: "docker compose config validates" — obsolete once Docker was removed).
- ⬜ Chat pane on a 1440px screen shows more messages before scrolling (taller container) — unverifiable, file absent.

---

### [Completed] Milestone 36: SaaS Data Connectors Framework

**Objective:** Build an extensible background data connector framework (`BaseConnector`) to discover, ingest, and sync documents from external sources (Web Crawlers, Google Drive, Notion, Slack, S3).

**Targets:**
- ✅ Define `BaseConnector` abstract domain port and `ConnectorConfig` models in `src/domain/abstractions/connector.py`.
- ✅ Implement `WebCrawlerConnector` (HTML-to-markdown scraping with depth and domain bounds) and `MockCloudDriveConnector` (cloud discovery & delta sync).
- ✅ Build `ConnectorRegistry` strategy lookup.
- ✅ Admin connector CRUD & sync trigger APIs: `GET`, `POST`, `PUT`, `DELETE` `/v1/admin/tenants/{tenantId}/connectors` and `POST .../connectors/{connectorId}/sync`.
- ✅ 3/3 unit tests pass in `test_data_connectors.py`.

**M36.5 addendum (post-M36, tracked in PROJECT_STATUS):** Modular Target-Engine Embedding & Remote Storage Fallback — `targetEngine` (`laptop` | `oracle` | `auto`) query param on `POST /v1/admin/tenants/{tenantId}/documents/{documentId}/process`; real-time `PENDING → PROCESSING → INDEXED` status; remote HTTP file retrieval via `REMOTE_STORAGE_API_URL` when files are missing locally; batch processing CLI (`scripts/process-pending.sh`).

---

### [Completed] Milestone 37: GraphRAG & Knowledge Graph Indexing

**Objective:** Complement vector + keyword hybrid search with entity-relationship knowledge graph extraction and multi-hop graph retrieval.

**Targets:**
- ✅ Environment Auto-Detection (`InfraCapabilities.detect()`): Auto-tailors execution profile between low-RAM Oracle VM (PostgreSQL) and MacBook Air M4 (Dual Engine).
- ✅ Define `BaseGraphRepository` abstract domain port and models in `src/domain/abstractions/graph.py`.
- ✅ Implement `PgGraphRepository` (PostgreSQL `graph_triples` + Recursive SQL) and `Neo4jGraphRepository` (async Cypher driver with auto-fallback).
- ✅ Implement `GraphExtractor` for triple parsing during document ingestion.
- ✅ Admin Graph & Capabilities APIs: `GET /v1/admin/tenants/{tenantId}/graph/capabilities`, `POST .../graph/engine`, `GET .../graph`, `POST .../graph/query`, `DELETE .../graph/triples/{tripleId}`.
- ✅ 5/5 unit tests pass in `test_graphrag.py` (Total test suite: 412/412 tests passing).
- ⚠️ **Deferred to M49:** graph-aware retrieval was not wired into search/chat (M37's "hybrid graph+vector reasoning" objective is unmet), the `neo4j` driver is not a declared dependency (engine always falls back to PostgreSQL), and two Neo4j defects were verified during post-M37 review — see Milestone 49.

---

### [Completed] Milestone 38: Critical Security Remediation (v0.36.0, 2026-08-04)

**Objective:** Close the critical application-level security defects identified in the August 2026 security audit. This milestone gates any public SaaS sale: the current Google OAuth flow provisions sessions from unverified client-supplied email, the metadata filter builder interpolates unvalidated field names into SQL, and the local file-serve path allows cross-tenant path traversal with a default HMAC key. No feature milestone ships before this one.

**Complexity:** Medium

**Dependencies:** None

**Status:** ✅ All code targets landed in v0.36.0 (2026-08-04); full suite 425 passed, 1 skipped; `ruff check` clean. Remaining follow-up outside the milestone: guest demo key provisioning and `docs/rag-lab.md` Auth section refresh. **Deploy note:** the server must set `SECRET_KEY` (>=32 chars, random), `STORAGE_HMAC_KEY` (random), and `OIDC_AUDIENCE` (Google OAuth client ID) or startup fails — see CHANGELOG v0.36.0.

**Targets:**
- **Google OAuth verification (`src/routers/auth.py`):**
  - Enforce `aud` verification against a configured Google client ID (`OIDC_AUDIENCE`) and validate the issuer claim (`accounts.google.com`) on every ID token.
  - Remove the unverified client-supplied `email` fallback for session provisioning, or gate it strictly behind `ENVIRONMENT != "production"`.
  - Fix the existing-user branch that generates a new API key without persisting it (`auth.py:97`) — persist the generated key hash atomically.
  - Replace the hardcoded JWT signing fallback (`"retriever-jwt-secret-key-2026"`) with a required `SECRET_KEY` setting enforced by the production validator (`config.py` `validate_production_secrets`).
- **SQL-injection-safe metadata filters (`src/adapters/vector/filter_builder.py`):**
  - Validate `MetadataFilter.field` against a strict `[a-zA-Z0-9_]+` whitelist before SQL interpolation; return 422 on invalid field names.
  - Add regression tests with injection payloads (`"x' OR 1=1--"`, `"a') ; DROP TABLE--"`, etc.).
- **File-serve hardening (`src/routers/document.py`, `src/adapters/storage/local_storage.py`):**
  - Basename-only filename validation (reject `..`, absolute paths, null bytes) in `serve_local_download`.
  - Make `STORAGE_HMAC_KEY` a required non-default secret in production (extend `validate_production_secrets`); constant-time signature comparison.
- **Defense-in-depth batch:**
  - Enforce an upload size cap before reading the request body into memory (`src/routers/document.py:79`).
  - Fail startup (or warn loudly) when `RATE_LIMIT_ENABLED=False` in production.
  - Add RLS policies for `eval_datasets`, `eval_questions`, `eval_runs`, `eval_run_results`, and `graph_triples` (`src/adapters/database/setup.py`).
  - Redact tracebacks from the global exception handler (`src/main.py:99-103`).
- **Demo credential resolution:** provision a server-side guest tenant + read-only API key for the `prateeq.in/rag` live demo (or remove the demo) so the public sandbox either works or is not advertised.

**Documents to Update:**
- `PROJECT_STATUS.md` — correct the "RLS active on all customer-data tables" and "`/v1/auth/google` verifies Google JWKS tokens" claims.
- `TECH_DEBT.md` — move resolved items to the Fixed table.
- `CHANGELOG.md` — record the remediation release.
- `docs/rag-lab.md` — update the Auth & Security section to match the verified flow.

**Acceptance Criteria:**
- `POST /v1/auth/google` with a garbage token + client email returns 401 (test asserts rejection).
- Forged session JWTs signed with the default secret are rejected after `SECRET_KEY` is configured.
- `filters=[{"field": "x') OR 1=1--", ...}]` returns 422, not rows.
- `GET /v1/local-downloads/{tenantId}/../../etc/passwd` returns 403.
- Production startup fails with a clear `ValueError` when `SECRET_KEY` or `STORAGE_HMAC_KEY` is unset/default.
- Uploading > `MAX_UPLOAD_BYTES` returns 413.
- Eval/graph tables have RLS policies; exception handler returns no traceback to clients.

---

### [Planned] Milestone 39: Agentic Workflow Execution Engine

**Objective:** Extend the generative inference layer from conversational RAG to autonomous multi-step tool execution loops.

**Targets:**
- Agent tool registration registry and execution sandboxes.
- Support multi-turn function calling, tool response parsing, and dynamic step orchestration.

---

### [Planned] Milestone 40: Layout-Aware Vision OCR & Table Parsing

**Objective:** Upgrade document ingestion from PyPDF2 text extraction to layout-aware OCR and vision-model parsing for scanned PDFs, multi-column layouts, and complex tables.

**Targets:**
- Integrate layout-aware document parsers (Docling / Unstructured API) into `processing-core`.
- Automatic table markdown conversion preserving headers, rows, and relationships.
- Image description extraction via vision-language models for embedded figures and diagrams.

---

### [Planned] Milestone 41: Chunk-Level Granular Access Control (ACL) & DB RLS Hardening

**Objective:** Enforce zero-trust multi-tenancy and user/role-level authorization at the document chunk level.

**Targets:**
- Add `allowed_roles` and `allowed_users` metadata to `document_chunks` schema.
- Update vector (`pgvector`) and sparse search queries to evaluate `X-User-ID` and role claims against chunk ACL lists.
- Enforce native Postgres Row-Level Security (RLS) policies using `SET LOCAL app.current_tenant_id`.

---

### [Planned] Milestone 42: Active Real-Time LLM Safety Guardrails

**Objective:** Protect the platform against malicious prompt injections, system prompt extraction, jailbreaks, and unverified PII leaks.

**Targets:**
- Replace naive regex PII filters with active LLM Guardrail adapters (Llama Guard 3 / NeMo Guardrails).
- Pre-execution input validation pass blocking adversarial prompts before LLM dispatch.
- Post-execution output validation pass scrubbing unverified sensitive data.

---

### [Planned] Milestone 43: Online Production Hallucination Tracing

**Objective:** Transition evaluation from offline batch dataset runs to continuous online monitoring on live production API traffic.

**Targets:**
- Asynchronous online evaluator background pipeline (TruLens / Arize Phoenix integration).
- Real-time scoring of Answer Faithfulness, Context Precision, and Hallucination Index on live sample traffic.
- Alerting triggers when tenant hallucination rates exceed configurable SLA thresholds.

---

### [Planned] Milestone 44: Learned Sparse Retrieval (SPLADE) & Reranker Microservice

**Objective:** Replace basic PostgreSQL `tsvector` keyword search with learned sparse embeddings and offload cross-encoder reranking to dedicated GPU microservices.

**Targets:**
- Integration of SPLADE model for keyword expansion and semantic keyword matching.
- Offload `CrossEncoderRerankerAdapter` from FastAPI in-process execution to an external Text Embeddings Inference (TEI) container.

---

### [Planned] Milestone 45: Context Compression & Zero-Trust Field Encryption

**Objective:** Minimize LLM inference token overhead and protect sensitive enterprise data stored in vector databases.

**Targets:**
- Integrate context window compression algorithms (LongLLMLingua) to remove redundant tokens from retrieved context chunks before LLM prompt compilation.
- Implement AES-256 envelope encryption for raw document chunk content and vector metadata at rest.

---

### [Planned] Milestone 46: Dynamic Multi-Embedding Vector Schemas & Index Scaling

**Objective:** Remove rigid vector dimension constraints (`Vector(768)`) to support seamless switching across different embedding models (768, 1536, 3072 dims) without database migration failures.

**Targets:**
- Implement dynamic table partitioning/collections per embedding model dimension (`vector_records_768`, `vector_records_1536`, `vector_records_3072`).
- Build automatic embedding re-indexing worker tasks when a tenant updates its embedding provider.

---

### [Planned] Milestone 47: Multi-Agent Consensus & Critic Reflection Loops

**Objective:** Enhance precision for high-stakes enterprise decisions (finance, healthcare, legal) using multi-agent debate and validation loops.

**Targets:**
- Implement a Generator Agent vs. Critic/Auditor Agent reflection loop within `InferenceOrchestrator`.
- Mandatory citation verification and logical consistency pass before response emission.

---

### [Planned] Milestone 48: Compliance & Data Sovereignty Lifecycle (GDPR/SOC2)

**Objective:** Automate data retention, PII anonymization, and GDPR right-to-be-forgotten vector deletion.

**Targets:**
- Automated background data retention purge schedulers per tenant SLA.
- Hard delete API hooks ensuring document removal cascades across relational tables, vector stores, and semantic caches.
- Zero-footprint inline PII anonymization during document ingestion.

---

### [Planned] Milestone 49: GraphRAG Productionization & Retrieval Integration

**Objective:** Make the M37 knowledge graph actually usable in production. The M37 milestone shipped the graph extractor, repositories, and admin APIs, but the Neo4j engine is unreachable (driver never declared as a dependency, so the repository always silently falls back to PostgreSQL), graph results never influence live search/chat retrieval (M37's stated "hybrid graph+vector reasoning" goal was not wired in), and verification surfaced two latent defects in the Neo4j adapter and ingestion pipeline. This milestone closes the GraphRAG loop.

**Complexity:** Medium

**Dependencies:** M37

**Targets:**
- **Neo4j driver dependency & connectivity:** add the `neo4j` Python driver to `pyproject.toml`; remove the lazy-import silent fallback in `Neo4jGraphRepository` so the engine genuinely connects (port 7687) and startup/capabilities reporting reflects real availability — today the engine switch to `neo4j` accepts the config change but every subsequent graph call runs against PostgreSQL.
- **Fix verified Neo4j defects:**
  - `delete_document_triples` Cypher filters on `r.document_id`, but `add_triples` never writes a `document_id` property on relationships — document-level triple deletion is a silent no-op under Neo4j.
  - `GraphExtractor` failures during ingestion are swallowed silently — triples can go missing with no log or failure signal.
- **Graph-aware retrieval integration:** wire `search_triples` multi-hop results into `HybridSearchService` (both `/search` and `/chat`) as graph evidence — expand the query with connected entities/relationships, merge triple context into the prompt, and surface graph citations. Today `search_triples` is reachable only via the admin query endpoint (`POST /v1/admin/tenants/{tenantId}/graph/query`).
- **Cross-engine parity tests:** verify engine switching, triple add/query/delete parity between PostgreSQL Recursive SQL and Neo4j Cypher (MacBook dual-engine profile).

**Acceptance Criteria:**
- Engine switch to `neo4j` on a MacBook profile: `GET /v1/admin/tenants/{tenantId}/graph/capabilities` reports `neo4j_status: online` and graph operations execute against Neo4j.
- Document ingestion deletes purge all triples for that document under both engines.
- A chat/search query on a knowledge-graph tenant returns triples/connected entities as graph evidence alongside vector hits.
- Deleting a document's triples in Neo4j actually deletes rows (no silent no-op).

---

These are tracked across all milestones and are not individual deliverables:

| Concern | Owner | Verification |
|---|---|---|
| **RAG Quality** | All milestones | Ragas evaluation: faithfulness > 0.95, answer relevance > 0.90, context recall > 0.92. Evaluated on golden dataset after every M13+ change. |
| **Security** | All milestones | RLS enforcement verified on every new table. No secrets in logs. No hardcoded prompts. Architecture conformance tests block regressions. |
| **Backward Compatibility** | M11+ | SDK versioning follows semver. API version prefix (`/v1/`) maintained. Deprecation policy documented. |
| **Documentation** | All milestones | Every API endpoint documented. Architecture decisions recorded as ADRs. Deployment and integration guides maintained. |
