# Project Status

Operational overview of the Retriever platform's current engineering status.

---

  ##  1. Status Overview
   
   - **Current Milestone**: SaaS Data Connectors Framework (M36 — Completed)
   - **Last Completed Milestone**: SaaS Data Connectors Framework (M36 — BaseConnector domain port, WebCrawlerConnector & MockCloudDriveConnector, admin CRUD, & document sync ingestion)
   - **Build Status**: Passing (407 unit tests pass)
   - **Admin Dashboard Build**: Passing (12 routes, all compile)
   - **Developer Console Build**: Passing (Next.js 16, compiles successfully)
   - **Reference Client Build**: Passing
   - **Integration Tests**: 4/4 passing (adapter-level, requires `INTEGRATION_TEST=1`)
   - **Next Recommended Milestone**: Milestone 37 / GraphRAG & Knowledge Graph Indexing
 
 ---
 
 ## 2. Health Indicators
 
 ### Architecture Health: **Green**
 - **Hexagonal Architecture Compliance**: Enforced by `tests/test_architecture.py` on every test run. Core domains contain no database or framework imports.
 - **Tenancy Boundary Controls**: PostgreSQL Row-Level Security (RLS) active on all customer-data tables. Secure UUID context validation blocks connection-level SQL injections.
 - **Google OAuth & Auto-Onboarding**: `/v1/auth/google` verifies Google JWKS tokens, auto-provisions Tenant & User records, issues API keys (`ret_live_...`), and returns signed JWT sessions.
 - **Dynamic SaaS Pricing Engine**: `GET /v1/config/pricing` serves public INR & USD plans; `PUT /v1/admin/config/pricing` updates pricing in PostgreSQL `configurations` table.
 - **Tenancy Breach Kill-Switch**: Verified. Context-level validation disables API keys and throws 403.
 - **Dynamic Config Override (CAD)**: Supports inheritance merging tenant overrides on top of global configs.
 - **No Hardcoded Prompts**: Enforced by conformance test and `PromptTemplateNotFoundError`.
 - **Client Integration Model**: Documented in architecture.md §15. API key + `X-User-ID` contract defined.
 
 ### Testing Status: **Green**
- **Unit Test Coverage**: 36 test files covering ingestion, retrieval, inference, embedding, events, telemetry, health, config system, tenant domain, architecture conformance, admin API, client SDK (M11), production storage (M12), custom pipelines (M13), semantic caching / worker batching (M14), enterprise cryptographic audit chains / data retention schedulers (M15), Google OAuth / auto-tenant provisioning (`test_google_auth.py`), SaaS pricing config endpoints (`test_pricing.py`), metadata & tag filtering (M18), model failover (M19), token cost optimization (M20), web search grounding (M21), structured data extraction (M22), multi-modal processing (M23), self-querying retrieval (M24), stream token telemetry / parsing whitelist validation (M25), SaaS tenant resource quotas (`test_tenant_quotas.py`, M26), multi-workspace collections (`test_workspace_collections.py`, M27), interactive chunking auditor (`test_chunking_auditor.py`, M28), A/B testing platform (`test_ab_testing.py`, M29), SaaS data connectors framework (`test_data_connectors.py`, M36), Baidu RapidOCR (PP-OCRv4), local Apple Silicon cross-encoder reranking, parent-child RAG context expansion, and contextual document summary prefixes.
- **Admin API Tests**: 48 tests covering all 32 admin endpoints (tenants, users, API keys, config, experiments CRUD+metrics, connectors CRUD+sync, documents, prompts CRUD+preview, audit logs, reindex).
- **Total Tests**: 407/407 passing (1 skipped).
- **Integration Tests**: 4 adapter-level tests (DB, Redis, tenant CRUD, document CRUD) — run with `INTEGRATION_TEST=1`.
- **Mock Quality**: 53 `@patch` decorators now use `autospec=True`.
- **Observability**: Inference logs now tagged with caller `role` (admin/client) and `key_id` for full attribution. Admin requests no longer have `user_id=NULL` blind spot. `TOKEN_CONSUMPTION` and `COST_SPEND` Prometheus counters carry `role` label.
 
 ### Documentation Health: **Green**
 - **Blueprints**: Master Architecture, Core specifications, System Design outlines, and Admin Dashboard guide are complete.
- **Feature Docs**: Core platform spec at `docs/features/core-platform.md`, Client SDK guide at `docs/features/client-sdk.md`.
- **Playbook**: Strict enforcement rules for database design, testing, RLS limits, and imports are documented.
- **ADRs**: Decisions for PostgreSQL, pgvector, FastAPI, Redis, RabbitMQ, Next.js, and SSE are recorded in `docs/decisions/`.

---

## 3. M10 Admin Dashboard — Completed

### Pages (9 routes)
| Route | Description |
|---|---|
| `/login` | Admin master key authentication |
| `/` | Dashboard home with stats overview |
| `/onboard` | 3-step client onboarding wizard |
| `/tenants` | Tenant list with search + pagination |
| `/tenants/[id]` | Tenant detail (7 tabs: overview, documents, users, API keys, prompts, sandbox, config) |
| `/tenants/[id]/playground` | API endpoint test console |
| `/settings` | Global config editor (AI, embedding, retrieval, rate limits) |
| `/audit-log` | Audit trail viewer with tenant/action filters |

### Backend
- Admin-scoped documents list endpoint
- Prompt templates CRUD + preview (no LLM call)
- Paginated tenant list (`search`, `limit`, `offset` → `{items, total}`)
- Audit log repository + list endpoint + write hooks at key mutation points
- `bypass_rls` parameter on `PromptTemplateRegistry` (consistent with admin pattern)
- `httpx` upgrade for Starlette deprecation fix
- `DocumentRepository` port extracted (`domain/abstractions/ingestion.py`), `SqlDocumentRepository` impl, 5 inline SQLAlchemy blocks removed from `main.py`

### Frontend
- Tailwind v4 + shadcn/ui (17 components)
- TanStack Query with caching + mutations
- Zustand auth store (sessionStorage) + cookie middleware
- Theme toggle (dark/light, next-themes)
- ErrorBoundary wrapper + sonner toast + date formatters
- Topbar accepts action button children

### Tabs (tenant detail)
- Overview, Documents, Users, API Keys, Prompts, Sandbox (RAG chat), Config

### Reference Client
- Standalone Next.js app at `apps/client-reference/`
- `RetrieverClient` class — listDocuments, search, chat (SSE), uploadDocument
- Tabs: Config, Chat (SSE streaming), Search, Documents

### Quality
- 118/118 API tests passing (was 94)
- Ruff clean, web build clean
- 53 `@patch` decorators with `autospec=True`
- Shared mutable state removed from test modules
- 4 integration tests green against real Postgres/Redis

### Security fixes (M10 cleanup)
- `verify_admin_key`: missing header returns 401 (was 422)
- `verify_scopes`: guard prevents silent bypass with `Depends()`
- `X-User-ID`: UUID format validation, 422 on malformed input
- `redact_secrets`: `is not None` instead of truthy check
- `streaming_finish_reason`: removed dead-code double-yield

---

## 4. M11 Client SDK & API Surface — Completed

### API Surface
- Implemented sortable, URL-safe Base64 pagination cursors resolving tie-breakers by database UUID.
- Added `GET /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages` chat history backwards-scrolling paginated endpoint.
- Updated `GET /v1/admin/tenants` and `GET /v1/tenants/{tenantId}/documents` to support cursor-based responses alongside legacy compatibility fallbacks.
- Re-architected Redis Lua sliding-window rate limiter to return exact capacity metrics (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers).
- Enforced 24-hour Redis idempotency caches on upload requests to prevent celery processing duplicates.
- Exporter script outputting updated specs to `docs/openapi.json`.

### Client SDK
- Built and published `@prat3010/retriever-client-js` TypeScript SDK compiles cleanly in Node/Browser environments.
- Native fetch wrapper injecting auth keys, headers, and SSE generators.

---

## 5. M12 Production Storage — Completed

### Document Storage
- Developed standard `S3Storage` adapter in [s3_storage.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/adapters/storage/s3_storage.py) using boto3.
- Wired dynamic storage switches (`STORAGE_PROVIDER` = `"s3"` vs `"local"`) seamlessly into `main.py`.
- Updated Celery background worker tasks to download S3 files to local temp paths on-demand and clean up after text-extraction is complete.

### Security Hardening
- Implemented `ConfigEncrypter` cryptography utility in `processing-core` utilizing AES-256-GCM.
- Applied transparent encryption/decryption on provider API keys at database boundary in `SqlConfigRegistry` and decryption inside worker tasks.
- Enabled dynamic async connection pooling config (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, etc.) inside `connection.py`.
- Extended `/health/readiness` readiness checks to probe active S3/MinIO connections.
- Added admin document download pre-signed S3 URL generator endpoints.

---

## 6. M13 Multi-Industry Configurability — Completed

### Pluggable Pipeline Components
- Developed token-aware recursive character splitter and semantic embeddings similarity splitter in [chunker.py](file:///Users/prateeksharma/Developer/retriever/packages/processing-core/src/processing_core/chunker.py).
- Implemented hybrid metadata extraction (regex filters + structured LLM schema extractor) on worker queues, saving data in document chunk records.
- Implemented input guardrails (local regex PII scrubber + customizable safety templates prompt injection blocks) returning 400 Bad Request on unsafe prompts.
- Added support for post-processed verified citations formatted to match the tenant's `citation_template` string (handles both streaming and static completions).

### Configuration Presets
- Packaged configuration templates for `legal`, `hr`, `medical`, and `finance` inside [presets.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/domain/config/presets.py).
- Created `POST /v1/admin/tenants/{tenantId}/config/apply-preset` to deep-merge configurations.

---

## 7. M14 Performance & Scale — Completed

### Decoupled Semantic Query Cache
- Implemented pure domain port `SemanticCacheProvider` in [retrieval.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/domain/abstractions/retrieval.py) and concrete database adapter `PgSemanticCacheAdapter` in [semantic_cache.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/adapters/database/semantic_cache.py) to preserve Hexagonal Architecture import constraints.
- Declared the HNSW vector-indexed, RLS-active `semantic_cache` database table mapping.
- Intercepted query embedding paths in `HybridSearchService` to returnCached results immediately on similarity threshold hits ($> 0.99$ cosine similarity).

### Batched Transactions
- Refactored chunk database inserts in background celery tasks in [__init__.py](file:///Users/prateeksharma/Developer/retriever/workers/src/tasks/__init__.py) to use batched parameter bindings, executing multi-inserts in single bulk operations.

### API Lifespan Warmup & Streaming Controls
- Warmed up async connection pool engines eagerly during FastAPI startup lifespan blocks in [main.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/main.py).
- Intercepted `asyncio.CancelledError` inside event stream generation blocks to immediately release and release thread handles when client SSE connections disconnect.

---

## 8. M15 Enterprise Readiness — Completed

### Cryptographic Append-Only Audit Logs
- Extended `AuditLogDb` schema mapping in [models.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/adapters/database/models.py) to incorporate cryptographic headers (`entry_hash` and `previous_hash`).
- Upgraded `SqlAuditLogRepository` to calculate SHA-256 blocks for incoming logs based on prior entry hashes, creating a tamper-evident audit history chain.
- Added `verify_audit_chain` utility to trace and verify block chain validation.

### OIDC Token Signatures Verification
- Implemented RSA signature verification, issuer, and audience validation in [security.py](file:///Users/prateeksharma/Developer/retriever/apps/api/src/adapters/api/security.py) using `pyjwt`.
- Leveraged external provider OIDC JWKS public key directories with local async fetching and caching to avoid round-trip signature check bottlenecks.

### Tenant Data Retention Scheduler
- Added `data_retention_ttl_days` schema bounds to SecuritySettings.
- Implemented periodic Celery cleanup worker in [__init__.py](file:///Users/prateeksharma/Developer/retriever/workers/src/tasks/__init__.py) executing system-wide database cleanses on expired documents (with cascade deletes to vector fragments) and idle chat history.

### Granular Scope Validation
- Extended `verify_scopes` middleware checks to analyze request parameters (such as path extensions or body filters), validating collection-scoped (`collection:<name>:read`) and file-typed (`document_type:<ext>:write`) rules.

---

## 9. Frontend Preparation Sprint — Completed

### Secure Client-Side Gateway (Cloudflare Worker Proxy)
- Created a deployable Cloudflare Worker package (`packages/client-proxy-worker`) to proxy client requests securely.
- Injects sensitive `X-API-Key` from Cloudflare secrets and routes queries dynamically based on decoded JWT claims (mapping `sub` -> `X-User-ID` and `tenant_id` context).
- Natively supports CORS preflights and streaming responses (SSE).

### Dynamic Custom Prompt Profiles
- Updated `ChatMessageRequest` API schema and `InferenceOrchestrator` flow (`main.py` + `orchestrator.py`) to support `system_prompt_name`.
- Allows client frontends to dynamically swap system prompt profiles (e.g. `default` vs. `exam_mode`) at request time.

### Documentation & Guides
- Wrote `docs/frontend-kickstart/client-proxy-guide.md` covering key security, deployment setup, and client-side streaming code examples (with RAG UX best practices).
- Created `docs/frontend-kickstart/agent-startup-prompt.md` to bootstrap any new frontend developer agent environment.
- Regenerated the main OpenAPI spec `docs/openapi.json` to include the updated schema fields.

---

## 10. Google Gemini & Anthropic Claude Integration Sprint — Completed

### Google Gemini Default Configuration
- Migrated default model configuration to target Google Gemini (`gemini-1.5-flash` for chat, `text-embedding-004` for vectors) using the OpenAI-compatible endpoint route.
- Standardised vector column dimensions from `1536` to `768` for pgvector.
- Added automatic dimension slicing to the OpenAI embedding adapters (in API services and processing-core workers) to compress `text-embedding-3-` embeddings to `768` dimensions on-the-fly, preserving cross-provider schema compatibility.

### Native Anthropic Claude Integration
- Created `AnthropicLLMAdapter` complying with `LlmProvider` to extract system prompts and handle Claude Messages API outputs.
- Implemented `RoutingLLMProvider` as a composite delegator to switch between OpenAI and Anthropic adapters dynamically based on the configuration's `provider_name` property.
- Fixed mock vector dimensions and added new adapter/router mock tests to the pytest suite.

---

## 11. M16 User Feedback & Quality Loops — Completed

### Relational Feedback Tracking
- Implemented `chat_message_feedback` database schema with ForeignKey constraints mapping to messages and tenants (supporting cascade delete).
- Enabled Row-Level Security (RLS) automatically during setup to guarantee B2B client isolation.

### Feedback Repository & REST API
- Created `SqlFeedbackRepository` adapter compiling thumbs up/down count ratios and tracking recent comments.
- Added client route `POST /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages/{messageId}/feedback` and admin route `GET /v1/admin/tenants/{tenantId}/feedback/analytics`.

---

## 12. M17 Secure Document Distribution — Completed

### Presigned URL Abstraction
- Declared `generate_presigned_url` abstract method on the `DocumentStorage` interface.
- Updated `S3Storage` adapter to generate expiring AWS S3/MinIO/Cloudflare R2 links.
- Implemented temporary HMAC-SHA256 signature generation and validation inside the `LocalStorage` adapter to test expiring downloads locally.

### Document Distribution API
- Added client route `GET /v1/tenants/{tenantId}/documents/{documentId}/download-url` to retrieve secure presigned download paths.
- Added verification endpoint `GET /v1/local-downloads/{tenantId}/{filename}` to securely validate HMAC tokens and serve files from the local filesystem during testing.

---

## 13. M22 Structured Data Extraction — Completed

### Extraction Endpoint
- Created `POST /v1/tenants/{tenantId}/documents/{documentId}/extract` accepting a JSON Schema and returning structured JSON from document content.
- Added `ExtractRequest` and `ExtractResponse` DTOs with proper field validation.

### Adapter Wiring
- Wired `json_schema` field on `InferenceRequest` into the OpenAI adapter as `response_format={"type": "json_object"}`.
- Wired `json_schema` into the Anthropic adapter as a schema hint appended to the system prompt.

### Domain Model
- Added `get_document_chunks` abstract method to `DocumentRepository` port with `SqlDocumentRepository` implementation.
- `DocumentChunk` domain model confirmed and used by the extraction pipeline.

### Testing
- Created `test_extraction.py` with 10 tests covering model validation, adapter wiring (response_format, system prompt injection), endpoint DTOs, and error paths.

### Documentation
- Updated ROADMAP.md, PROJECT_STATUS.md, CHANGELOG.md, and TECH_DEBT.md.

---

## 14. M23 Multi-Modal Processing — Completed

### ChatMessage Vision Support
- Added `images: list[dict]` field to `ChatMessage` domain model — empty by default, backward-compatible.
- OpenAI adapter: converts `images` to OpenAI content blocks (`text` + `image_url`) in both `generate()` and `generate_stream()`.
- Anthropic adapter: converts `images` to Anthropic content blocks (`text` + `image` with base64 source) in `_compile_messages()`.

### Config
- Added `vision_model: str = "gpt-4o"` to `AIProviderConfig`.
- Added `VISION_MODEL` env var to `Settings`.

### Worker Pipeline
- `mime_type` now passed from upload endpoint to Celery `process_document` task.
- New `_describe_with_vision()` function in worker calls OpenAI vision API for images and zero-text PDFs (describes first page).
- Added `Pillow>=10.0.0` and `openai>=1.0.0` to worker dependencies.

### Testing
- Created `test_vision.py` with 11 tests covering model, both adapters, config, and worker function signature.

### Documentation
- Updated ROADMAP.md, PROJECT_STATUS.md, CHANGELOG.md, and TECH_DEBT.md.

---

## 15. M24 Self-Querying Retrieval — Completed

### LLM Metadata Extraction (Ingestion)
- Default LLM metadata extraction in worker (`workers/src/tasks/__init__.py`) — runs when no extractors configured AND API key available.
- Extracts `doc_type`, `date_reference`, `topics`, `author_reference` into each chunk's `meta_data`.

### Self-Query Adapter (Search)
- `SelfQueryProvider` ABC + `enable_self_query` on `SearchQuery` + `FeatureFlags`.
- `LLMSelfQueryAdapter` in `adapters/cognitive/self_query_adapter.py` — parses NL queries into `MetadataFilter` lists.
- Wired into `HybridSearchService` as pipeline step 0: parsed filters merge with explicit filters (not override).
- 9 tests covering adapter parsing, search integration, flag gating, filter merging, graceful degradation.

### Polish Round 2 (Code Quality)
- Removed 10 redundant inline imports in `main.py` (dead code from modules already at top level).
- Extracted `_check_idempotency`/`_cache_idempotency` in `upload_document` (73→~40 lines).
- Extracted `_SLIDING_WINDOW_SCRIPT` + `_parse_rate_limit_result` in `rate_limiter.py` (`acquire` 75→17 lines).
- Added `AsyncGenerator` return type annotations to `lifespan`, `event_stream`, `admin_download_document_file`.
- 286 tests passing.

### Test coverage (6 new test files)
- `test_cache_adapter.py` (11 tests): `RedisTenantConfigCache` — hit/miss/error paths for all 5 public methods.
- `test_vector_repository.py` (4 tests): `PgVectorSearchAdapter.search_similar` — happy path, empty results, filters, tags.
- `test_keyword_repository.py` (4 tests): `PgKeywordSearchAdapter.search_keywords` — happy path, empty results, filters, query passthrough.
- `test_local_storage.py` (7 tests): `LocalStorage` — save, delete, presigned URL with real temp dir.
- `test_reranker.py` (7 tests): `CohereRerankerAdapter` — empty candidates, basic rerank, threshold filtering, score remapping, model override.
- `test_telemetry_setup.py` (6 tests): `get_tracer`/`get_metrics`/`get_rate_limiter` singletons + `init_telemetry` wiring.

### Bugfixes
- Added missing `await` on `local_storage.generate_presigned_url()` at `main.py:708`.
- 3 migration drifts: `inference_logs.notes`, `semantic_cache` table, `audit_logs.entry_hash`/`previous_hash`.

---

## 16. Milestone 25: Developer Console & Local Ingestion — Completed

### Local Ingestion Pipeline Overhaul
- Configured local **Ollama** embeddings (`nomic-embed-text` at `http://host.docker.internal:11434/v1`) inside `ingest_self.py`.
- Re-indexed entire codebase (220 files, 2,241 vector chunks) into Postgres isolated by logical RLS under the system tenant.

### API Key Validation Endpoint
- Implemented `/v1/config/validate-key` endpoint inside `main.py` allowing clients to run lightweight check pings against cognitive models.
- Enforced a secure billing strategy: the API key resolver checks the new `allow_platform_key` flag on the tenant's features. If unset or `False`, requests without client keys are rejected, preventing auto-billing leaks.

### Next.js Developer Console App
- Bootstrapped `apps/developer-console` using Next.js 16 and `@prat3010/retriever-client-js`.
- Implemented a premium dark-mode glassmorphic theme in pure vanilla CSS.
- Added sidebar navigation for indexed documents, SSE chat token streaming, key validation settings, and citation click modals.

---

## 17. Milestone 26: SaaS Tenant Resource Quotas — Completed

### Hard/Soft Quota Engine & Abstractions
- **Quota Settings**: Added `TenantQuotaSettings` schema (`max_documents`, `max_storage_bytes`, `max_monthly_tokens`, `max_daily_requests`, `soft_limit_percentage`) to tenant configuration.
- **Domain Abstraction**: Created `QuotaRepository` abstract port and `SqlQuotaRepository` database adapter to query real-time document count, storage byte sum, monthly tokens, and daily request volume.
- **Quota Enforcement**: Created `QuotaService` domain component enforcing hard and soft quota limits.

### Status Hooks & Response Headers
- **Exception Handler**: Added FastAPI handler for `QuotaExceededError` returning HTTP status 402 (Payment Required) or 429 (Too Many Requests / Quota Exceeded) with headers (`Quota-Exceeded-Resource`, `Quota-Limit`, `Quota-Usage`).
- **Soft Limit Warnings**: Appended `X-Quota-Warning` header when storage usage or document count exceeds configured soft limit percentage during upload.
- **Unit Testing**: 7/7 unit tests passing in `tests/test_tenant_quotas.py`.

---

## 18. Milestone 27: Multi-Workspace Collections — Completed

### Database & Schema Partitioning
- **Database Schema**: Added `collection_id` (UUID, nullable=True, indexed) column to `documents`, `document_chunks`, and `vector_records` tables with compound index `(tenant_id, collection_id)`.
- **Domain & DTO Integration**: Added `collection_id` field to `Document`, `DocumentChunk`, `SearchQuery`, `SearchRequest`, `ChatMessageRequest`, and `DocumentResponse` schemas.

### Scoped Ingestion & Hybrid Search
- **Workspace Scoped Ingestion**: Document upload (`POST /v1/tenants/{tenantId}/documents`) accepts optional `collectionId` query parameter, inheriting `collection_id` down to chunks and vector embeddings.
- **Workspace Scoped Search & Chat**: Dense vector (`pgvector`) and sparse keyword (`tsvector`) search queries support workspace collection isolation via `build_filter_clause`. Chat inference (`POST /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages`) forwards `collectionId` to retrieval engine.
- **Unit Testing**: 6/6 unit tests passing in `tests/test_workspace_collections.py`.

---

## 19. Milestone 28: Interactive Chunking Auditor — Completed

### Dry-Run Sandbox Preview API
- **Admin Endpoint**: Added `POST /v1/admin/tenants/{tenantId}/documents/chunk-preview` allowing administrative users to audit chunking splits before database/vector persistence.
- **Multi-Strategy Support**: Implemented `ChunkerFactory` supporting `sliding` (token sliding window), `semantic` (paragraph & structural units), and `hierarchical` (parent-child dual granularity) algorithms.
- **Character Offset Metrics**: Calculates character start/end index offsets (`startCharIdx`, `endCharIdx`), character lengths, token counts, and parent-child metadata for visual UI highlighting.
- **Unit Testing**: 5/5 unit tests passing in `tests/test_chunking_auditor.py`.

---

## 20. Milestone 29: A/B Testing Platform — Completed

### Experiment Lifecycle & Admin CRUD
- **Admin Management Endpoints**: Added `GET`, `POST`, `PUT`, `DELETE` `/v1/admin/tenants/{tenantId}/experiments` allowing administrative users to define and manage experiment variants.
- **Status Lifecycle Control**: Added `POST /v1/admin/tenants/{tenantId}/experiments/{experimentId}/status` with support for `draft`, `active`, `paused`, and `completed` states.

### Dynamic Variant Allocation & Telemetry
- **Deterministic Variant Bucket Allocation**: Updated `assign_variant` and `apply_overrides` to dynamically assign active experiment variants in both `chat` and `search` routers.
- **Per-Variant Analytics Metrics**: Added `GET /v1/admin/tenants/{tenantId}/experiments/{experimentId}/metrics` aggregating total requests, token volume, average latency, and p95 latency from `inference_logs`.
- **Unit Testing**: 3/3 unit tests passing in `tests/test_ab_testing.py`.

---

## 21. Milestone 36: SaaS Data Connectors Framework — Completed

### Extensible BaseConnector Architecture
- **Domain Abstractions & Port**: Defined `BaseConnector` ABC and `ConnectorConfig` domain models in `src/domain/abstractions/connector.py`.
- **Strategy Implementations**: Implemented `WebCrawlerConnector` (HTML scraping & text conversion) and `MockCloudDriveConnector` (cloud discovery & delta sync simulation).
- **Connector Strategy Registry**: Built `ConnectorRegistry` in `src/domain/connectors/registry.py`.

### Admin APIs & Document Ingestion
- **Admin CRUD Endpoints**: Added `GET`, `POST`, `PUT`, `DELETE` `/v1/admin/tenants/{tenantId}/connectors` to create and configure external data sources.
- **Sync Trigger & Vector Ingestion**: Added `POST /v1/admin/tenants/{tenantId}/connectors/{connectorId}/sync` which fetches discovered documents and ingests them into vector storage via `ingest_file_sync`.
- **Unit Testing**: 3/3 unit tests passing in `tests/test_data_connectors.py`.

---

## 22. Production Deployment (Oracle VPS + Supabase) — Completed

### Stack (Zero Cost)

| Component | Provider | Notes |
|-----------|----------|-------|
| API server | Oracle Cloud free tier (`VM.Standard.E2.1.Micro`) | systemd + nginx + Let's Encrypt SSL, ~0.9 GB RAM, Ollama sidecar |
| Database | Supabase (free tier) | PostgreSQL + pgvector, 500 MB, RLS enabled |
| Embeddings | HuggingFace Inference API | `all-mpnet-base-v2` (768-dim), free token for higher rate limits |
| LLM | Client BYOK | OpenAI / Anthropic / Gemini via tenant's own API key |
| Proxy | Cloudflare Workers | CORS, routing, rate limiting — 100k req/day free |

### Architecture

```
Client App → Cloudflare Proxy → Oracle VPS (API) → Supabase (DB, vectors, RLS)
                                                → HuggingFace (embeddings)
                                                → Tenant's LLM provider
```

### Changes Made

- **`apps/api/src/adapters/cognitive/hf_embedding_adapter.py`** — New adapter using HuggingFace Inference API (`sentence-transformers/all-mpnet-base-v2`), retries on 503s, no Redis/Celery dependency.
- **`apps/api/src/adapters/ingestion/sync_ingestion_service.py`** — Synchronous document ingestion pipeline (parse → chunk → embed → store), no Celery required.
- **`apps/api/src/main.py`** — Swapped OpenAI embedder for HF; added `POST /v1/admin/tenants/{tenantId}/documents/ingest` (sync); made Celery import conditional; made Redis non-fatal.
- **`apps/api/src/adapters/cache/config_cache.py`** — Lazy Redis connection (no crash if Redis is down).
- **`apps/api/src/adapters/telemetry/setup.py`** — Updated Redis reference.
- **`packages/client-proxy-worker/`** — Deployed to Cloudflare Workers at `retriever-client-proxy.retriever.workers.dev`.

### Details

- Embedding model: `sentence-transformers/all-mpnet-base-v2` via HuggingFace Inference API (free, 768-dim).
- No Celery/RabbitMQ/Redis — processing happens inline in the API request.
- Embedding via HuggingFace Inference API (free tier, ~1000 req/min with token).
- LLM per-tenant: each tenant provides their own API key (OpenAI, Anthropic, Gemini).
- Migrations: all tables created via `Base.metadata.create_all` (Supabase), then `alembic stamp head` to mark current.
- Health check: `/health/liveness` (simple) and `/health/readiness` (DB + Redis + S3 checks).

---

## 23. M31 Security Hardening & Secrets Remediation — Completed

**Objective:** Eliminate credential exposure in version control, enforce fail-safe production defaults, harden network perimeter, and fix weak authentication checks in the admin proxy.

### Changes Made
- **Config validation** (`apps/api/src/config.py`): Added `@model_validator(mode="after")` that crashes FastAPI startup with `ValueError` if `ENVIRONMENT == "production"` and `ADMIN_MASTER_KEY` or `KEY_ENCRYPTION_KEY` still have their development defaults.
- **Admin key verification endpoint** (`apps/api/src/main.py`): Added `GET /v1/admin/verify-key` that validates the `X-Admin-Master-Key` header. Returns `{"valid": true}` on success, 401 on failure. Used by the admin dashboard proxy for server-side key validation.
- **Proxy validation** (`apps/web/src/proxy.ts`): Rewrote proxy to call the backend `/v1/admin/verify-key` endpoint and validate the key server-side. Validated results are cached in a signed `admin_key_validated` cookie (5 min TTL). Invalid keys are cleared and redirected to `/login`. Fails open (allows request) on backend timeout so dashboard availability doesn't depend on API uptime.
- **`.gitignore`**: Confirmed `.env` and `.env*` patterns are present in both root and `apps/web/` gitignore files.

### Manual Actions Required
1. **Rotate credentials — ✅ DONE (2026-07-31):** `apps/web/.env.local` scrubbed from git history (commit `53c6286`, all 148 commits, both branches) via `git-filter-repo` + force-push. Vercel OIDC token verified **already expired** (JWT `exp` 2026-07-18, API returns 403) — rotation not required. Server object store purged, root `.gitignore` hardened to `.env*`. Root `.env` was never committed (verified — clean history).
2. **ADMIN_MASTER_KEY on Oracle VM — ✅ DONE:** verified non-default on server (2026-07-31).
3. **Close port 8000 — ✅ DONE:** verified filtered/closed from external host; API reachable only via nginx 443/80.

---

## 24. M32 Onboarding & Client UX Overhaul — Completed

**Objective:** Fix the broken onboarding handoff (no user created during wizard), eliminate confusing defaults in the client login form, introduce human-friendly short IDs, and polish the admin and client UX around identity management.

### Changes Made
- **4-step onboarding wizard** (`onboard/page.tsx`): Inserted Step 3 ("User") between API Key generation and credentials summary. Auto-populates display name from tenant name and generates an `external_id`. Creates the user via `useCreateUser` hook. Final credentials card now shows the real User ID alongside Tenant ID and API Key.
- **Client login form defaults** (`RagInterface.tsx`): `tenantId` and `userId` now start as empty strings (force user to enter their own). Placeholder text uses `tn_...`/`usr_...` format. API key placeholder changed from `sk_live_...` to `ret_live_...` to match Retriever's actual key format.
- **ID validation relaxed** (`RagInterface.tsx`): `isUuid()` now accepts both UUIDs and short ID formats (`tn_X7kM2p`, `usr_Qp3N8w`) to prepare for future short ID migration.
- **API Base URL hidden** (`RagInterface.tsx`): The API URL field is collapsed under a "Show Advanced" toggle by default. Keeps the config panel clean for most users while allowing advanced users to override.
- **User ID column** (`tenant-users.tsx`): Added a "User ID" column to the tenant Users table with a copy-to-clipboard button, so admins can easily provide the internal UUID to clients.

### Manual Actions Required
- **Short ID migration — ⬜ DEFERRED (backend)**: Replace 36-character UUIDs with prefix-based short IDs (`tn_` for tenants, `usr_` for users) in the backend. Requires new DB columns and API path updates. Frontend side complete (`isUuid()` accepts short IDs); backend API paths are still UUID-only. Milestone status: **complete except backend short-ID columns**.

---

## 25. M33 Code Quality & Architecture — Completed

**Objective:** Break down the 2,250-line `main.py` monolith, eliminate type safety gaps, consolidate duplicated constants, and clean up inconsistent patterns across both the backend and frontend codebases.

### Phase 1 — Initial Decomposition
- **Full `main.py` decomposition** (2355→170 lines): Extracted 25 Pydantic DTOs to `src/schemas/` (7 files), business logic to `src/domain/` (inference, guardrails, retrieval), and all 55+ route handlers to 6 fully populated `src/routers/` modules (`health.py`, `admin.py`, `tenant.py`, `document.py`, `search.py`, `chat.py`). Created `src/container.py` for DI wiring of all ~25 singletons (repos, adapters, services, LLM providers, embedder, search, orchestrator, eval). Moved `llm_safety_guard` to `src/adapters/guardrails/` for architecture conformance.
- **Shared TypeScript types** (`Prateek_website/src/lib/rag-types.ts`): Defined `SearchResult`, `DocumentMeta`, and `SearchResponse` interfaces. Eliminates `any` type usage in `RagInterface.tsx`.
- **`API_BASE` consolidated**: Removed duplicate declarations from `login/page.tsx` and `onboard/page.tsx`. Both now import `API_BASE` from `lib/api.ts`.
- **RetrieverClient cleanup** (`rag-client.ts`): Refactored `uploadDocument` and `deleteDocument` to use the shared `request<T>()` method instead of duplicating fetch + header logic. Extracted shared auth header construction.
- **Duplicate cookie clearing removed** (`sidebar.tsx`): Removed the separate `document.cookie = ...` line from the logout handler — `clearKey()` in the auth store already handles cookie clearing.
- **Test `@patch` target fixes**: Updated 5 test files to patch router modules (`src.routers.chat`, `src.routers.admin`, `src.routers.document`) and new import paths (`src.adapters.cache.config_cache`, `src.schemas.document`) instead of `src.main`. All 369 tests pass (same baseline + 1 skipped).
- **Architecture conformance**: `domain/abstractions/` has 12+ pure ABCs with zero infrastructure imports. Enforced by `tests/test_architecture.py` AST analysis.

### Phase 2 — Refinements (0.27.0)
- **Class-based container**: Module-level singletons refactored into `Container` class with `_build()`, `reset()`, and `override()` for testability. Full backward compat via module-level aliases.
- **`AdminRepository` port**: Extracted `get_platform_stats` and `reset_platform` (230+ lines of inline SQLAlchemy) from admin router into `SqlAdminRepository` adapter. Fixed response model (int vs str for `tenantsDeleted`).
- **`get_message` on `ChatSessionRepository`**: New port method with `SqlChatSessionRepository` implementation — replaces inline `tenant_session` query in chat router feedback endpoint.
- **Event bus wiring**: `EventPublisher` port wired into container — `RabbitMQEventPublisher` when broker available, `NoOpEventPublisher` fallback. Architecture conformance test added.
- **Router adapter leak fixes**: Removed all inline adapter imports from `admin.py`, `document.py`, `chat.py` (tenant_session, ChatMessageDb, ingest_file_sync, etc.). All dependencies flow through container. 4/4 architecture conformance tests pass.
- **Routers `serve_local_download`/`root` moved**: `serve_local_download` to `document.py`, `root` to `health.py`. `main.py` now purely bootstrap (133 lines).
- **Ruff fixes**: 7/7 issues resolved. UP038 syntax updated.
- **Test count**: 372/372 passing (1 skipped) at the time; current suite: 407/407 passing.

---

## 26. M34 Production Operations & DevOps — Completed

**Objective:** Eliminate manual SSH deploys, add error tracking and uptime monitoring, fix unbounded tenant queries, and close the remaining production operations gaps.

### Changes Made
- **GitHub Actions auto-deploy** (`.github/workflows/deploy-api.yml`): Creates SSH connection to Oracle VM, pulls latest code, reinstalls Python dependencies, restarts the `retriever-api` systemd service, and runs post-deploy smoke tests (liveness + readiness). Triggered by pushes to `main` affecting `apps/api/`, `packages/processing-core/`, or `workers/`.
- **Pagination fix** (`use-tenants.ts`): `useAllTenants()` now accepts a configurable `limit` parameter (default 50) instead of hardcoding `limit=1000`.

### Manual Actions Required
1. **Configure GitHub Secrets — ✅ DONE:** `ORACLE_HOST`, `ORACLE_USER`, `ORACLE_SSH_KEY`, `ORACLE_PORT` all present in GitHub secrets (verified 2026-07-31).
2. **Configure Sentry — ✅ DONE:** `SENTRY_DSN` set (EU region) and verified via one-off `capture_exception` (error "Sentry wiring test from retriever-oracle-vm" ingested 2026-07-31). Required a one-line fix in `main.py:40` — OTel integration import path changed in newer sentry-sdk (`.integration` module).
3. **Set up uptime monitoring — ⬜ UNVERIFIABLE:** Configure UptimeRobot or Better Uptime to poll `https://rag.prateeq.in/health/liveness` every 5 minutes (endpoint verified reachable, 200). External service — check the provider dashboard.

---

## 27. M35 Final Polish & Infrastructure Self-Detection — Completed

**Objective:** Add server-spec auto-detection for infrastructure services, update stale model defaults, clean up deprecated Docker Compose syntax, and improve the client chat UI for large screens.

### Changes Made
- **Server-spec auto-detection** (`config.py`): Added `InfraCapabilities` class that reads total RAM (`psutil.virtual_memory().total`) and CPU cores at startup. Computes and **logs** viability thresholds (Redis ≥ 2 GB, RabbitMQ ≥ 2 GB, Celery workers ≥ 4 GB + 2+ cores) and the resulting mode (LEAN vs FULL):
  - ⚠️ **Known gap:** `REDIS_ENABLED`/`BROKER_ENABLED`/`WORKERS_ENABLED` env overrides are accepted by `Settings` but **not yet consumed anywhere** — no adapter or container wiring reads them. Detection is log-only today; runtime degradation is connection-failure-driven (lazy imports, `NoOpEventPublisher` fallback). Wiring into `container.py` is tracked as spec-gated deployment work.
- **Gemini model updated** (`providers.ts`): Default changed from `gemini-1.5-flash` to `gemini-2.5-flash` (verified).
- **Docker infrastructure removed**: `docker-compose.yml`, `Dockerfile`, `workers/Dockerfile.worker`, `apps/api/docker-compose.test.yml`, and `.github/workflows/docker.yml` deleted — repo is Docker-free (verified). *(Correction: earlier note about removing the deprecated `version: '3.8'` field referred to a file that no longer exists.)*
- **Chat container height** (`rag.module.css`): Changed from fixed `400px` to `min(60vh, 600px)` — ⚠️ unverifiable, file no longer present in repo.

---

## 28. M36.5 (addendum) Modular Target-Engine Embedding & Remote Storage Fallback — Completed

**Objective:** Implement target-engine routing (Laptop vs Oracle VM) for document embedding, add real-time `PROCESSING` status visual feedback in the Admin Dashboard, implement remote HTTP file fallback for cross-environment access, and provide a bulk CLI tool.

### Changes Made
- **Target Engine Routing & Fallback** (`apps/api/src/routers/admin.py`):
  - Added `targetEngine` (`laptop` | `oracle` | `auto`) query parameter to `POST /v1/admin/tenants/{tenantId}/documents/{documentId}/process`.
  - Added real-time status transitions: `PENDING` → `PROCESSING` → `INDEXED`.
  - Implemented remote HTTP file retrieval from `{REMOTE_STORAGE_API_URL}/v1/admin/tenants/{tenantId}/documents/{documentId}/file` using `ADMIN_MASTER_KEY` when physical files are missing from local disk.
- **Admin Dashboard UI** (`apps/web/src/components/tenant-documents.tsx` & `use-documents.ts`):
  - Updated document table to render ⚡ **Laptop** (Local Ollama) and ☁️ **Cloud** (Oracle VM) embedding target buttons on `PENDING` files.
  - Added `PROCESSING` state badge with animated loader spinner.
- **Batch Processing Tool** (`scripts/process-pending.sh` & `apps/api/src/scripts/process_pending.py`):
  - Created executable script to batch process all `PENDING` documents across all tenants in one command.
- **Config & Tech Debt Update** (`config.py` & `TECH_DEBT.md`):
  - Added `REMOTE_STORAGE_API_URL` setting.
  - Recorded Cloudflare R2 cloud storage setup under Product/Deferred items.

---

## 29. Outstanding Blockers & Issues

Pending items (verified against live Oracle VM `130.210.35.134`, 2026-07-31):

| Item | Milestone | Status |
|---|---|---|
| Scrub `apps/web/.env.local` from git history + Vercel OIDC token | M31 | ✅ Done (git-filter-repo, 2026-07-31; token verified expired — rotation unnecessary) |
| Set `SENTRY_DSN` on Oracle VM + verify error capture | M34 | ✅ Done (EU region, test error ingested; one-line OTel import fix in main.py) |
| UptimeRobot/Better Uptime monitor on `rag.prateeq.in/health/liveness` | M34 | ⬜ Needs UptimeRobot account (optional) |
| Backend short ID columns + API path acceptance (`tn_`/`usr_`) | M32 | ⬜ Deferred |
| Wire `REDIS_ENABLED`/`BROKER_ENABLED`/`WORKERS_ENABLED` into `container.py` (spec-gated deployment) | M35 | ⬜ Known gap |
| LLM key quota alerting | M30 | ✅ Done (quota-alert.sh + cron; free-tier key = non-monitorable until prepaid) |
| Nightly DB backup cron | M30 | ✅ Done (backup-db.sh, 02:30 UTC, verified 20 tables) |
| Nginx hardening (rate limiting, HSTS/CSP) | M30 | ✅ Done (verified live) |
| fail2ban for SSH | M30 | ✅ Done (active, sshd jail) |
| Staging environment | M30 | ✅ Done (documented process in DEPLOYMENT.md) |
| Root cause addendum (initial deploy chat outage) | M30 | ✅ Done (DEPLOYMENT.md) |

Resolved during verification/fixes (2026-07-31): `ADMIN_MASTER_KEY`/`KEY_ENCRYPTION_KEY` rotated (non-default), port 8000 filtered externally, `/metrics` + `/health/liveness` reachable via https (200), GitHub deploy secrets configured, nginx + `retriever-api` healthy, Ollama sidecar running, nginx rate limiting + security headers live, fail2ban active, nightly backups + quota alerting scheduled.

Deferred architecture, test, security, migration, and product items: see `TECH_DEBT.md`.

