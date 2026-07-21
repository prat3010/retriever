# Project Status

Operational overview of the Retriever platform's current engineering status.

---

  ##  1. Status Overview
   
   - **Current Milestone**: Production Polish (M30 — Completed)
   - **Last Completed Milestone**: Milestone 30: Production Polish
   - **Build Status**: Passing (369 unit tests pass)
   - **Admin Dashboard Build**: Passing (12 routes, all compile)
   - **Developer Console Build**: Passing (Next.js 16, compiles successfully)
   - **Reference Client Build**: Passing
   - **Integration Tests**: 4/4 passing (adapter-level, requires `INTEGRATION_TEST=1`)
   - **Next Recommended Milestone**: Milestone 26: SaaS Tenant Resource Quotas
 
 ---
 
 ## 2. Health Indicators
 
 ### Architecture Health: **Green**
 - **Hexagonal Architecture Compliance**: Enforced by `tests/test_architecture.py` on every test run. Core domains contain no database or framework imports.
 - **Tenancy Boundary Controls**: PostgreSQL Row-Level Security (RLS) active on all customer-data tables. Secure UUID context validation blocks connection-level SQL injections.
 - **Tenancy Breach Kill-Switch**: Verified. Context-level validation disables API keys and throws 403.
 - **Dynamic Config Override (CAD)**: Supports inheritance merging tenant overrides on top of global configs.
 - **No Hardcoded Prompts**: Enforced by conformance test and `PromptTemplateNotFoundError`.
 - **Client Integration Model**: Documented in architecture.md §15. API key + `X-User-ID` contract defined.
 
 ### Testing Status: **Green**
- **Unit Test Coverage**: 28 test files covering ingestion, retrieval, inference, embedding, events, telemetry, health, config system, tenant domain, architecture conformance, admin API, client SDK (M11), production storage (M12), custom pipelines (M13), semantic caching / worker batching (M14), enterprise cryptographic audit chains / data retention schedulers (M15), metadata & tag filtering (M18), model failover (M19), token cost optimization (M20), web search grounding (M21), structured data extraction (M22), multi-modal processing (M23), self-querying retrieval (M24), stream token telemetry / parsing whitelist validation (M25), and main.py decomposition.
- **Admin API Tests**: 36 tests covering all 20 admin endpoints (tenants, users, API keys, config, documents, prompts CRUD+preview, audit logs, reindex).
- **Total Tests**: 369/369 passing (1 skipped).
 - **Integration Tests**: 4 adapter-level tests (DB, Redis, tenant CRUD, document CRUD) — run with `INTEGRATION_TEST=1`.
 - **Mock Quality**: 53 `@patch` decorators now use `autospec=True`.
 
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

## 17. Deployment: Free-Tier Production — Completed

### Stack (Zero Cost)

| Component | Provider | Notes |
|-----------|----------|-------|
| API server | Render (free web service) | Docker, 512 MB RAM, sleeps after 15 min idle |
| Database | Supabase (free tier) | PostgreSQL + pgvector, 500 MB, RLS enabled |
| Embeddings | HuggingFace Inference API | `all-mpnet-base-v2` (768-dim), free token for higher rate limits |
| LLM | Client BYOK | OpenAI / Anthropic / Gemini via tenant's own API key |
| Proxy | Cloudflare Workers | CORS, routing, rate limiting — 100k req/day free |

### Architecture

```
Client App → Cloudflare Proxy → Render (API) → Supabase (DB, vectors, RLS)
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

## 18. M31 Security Hardening & Secrets Remediation — Completed

**Objective:** Eliminate credential exposure in version control, enforce fail-safe production defaults, harden network perimeter, and fix weak authentication checks in the admin proxy.

### Changes Made
- **Config validation** (`apps/api/src/config.py`): Added `@model_validator(mode="after")` that crashes FastAPI startup with `ValueError` if `ENVIRONMENT == "production"` and `ADMIN_MASTER_KEY` or `KEY_ENCRYPTION_KEY` still have their development defaults.
- **Admin key verification endpoint** (`apps/api/src/main.py`): Added `GET /v1/admin/verify-key` that validates the `X-Admin-Master-Key` header. Returns `{"valid": true}` on success, 401 on failure. Used by the admin dashboard proxy for server-side key validation.
- **Proxy validation** (`apps/web/src/proxy.ts`): Rewrote proxy to call the backend `/v1/admin/verify-key` endpoint and validate the key server-side. Validated results are cached in a signed `admin_key_validated` cookie (5 min TTL). Invalid keys are cleared and redirected to `/login`. Fails open (allows request) on backend timeout so dashboard availability doesn't depend on API uptime.
- **`.gitignore`**: Confirmed `.env` and `.env*` patterns are present in both root and `apps/web/` gitignore files.

### Manual Actions Required
1. **Rotate credentials:** Use `git filter-branch` or BFG Repo-Cleaner to scrub `.env` and `apps/web/.env.local` from git history. Then rotate the Supabase DB password, OpenAI API key, and Vercel OIDC token.
2. **SSH into Oracle VM:** Replace `ADMIN_MASTER_KEY` in production `.env` with a strong random value (`openssl rand -hex 32`). Rotate the admin dashboard login key.
3. **Close port 8000:** Remove the port 8000 ingress rule from Oracle Cloud security group. All API traffic must route through Nginx on ports 80/443.

---

## 19. M32 Onboarding & Client UX Overhaul — Completed

**Objective:** Fix the broken onboarding handoff (no user created during wizard), eliminate confusing defaults in the client login form, introduce human-friendly short IDs, and polish the admin and client UX around identity management.

### Changes Made
- **4-step onboarding wizard** (`onboard/page.tsx`): Inserted Step 3 ("User") between API Key generation and credentials summary. Auto-populates display name from tenant name and generates an `external_id`. Creates the user via `useCreateUser` hook. Final credentials card now shows the real User ID alongside Tenant ID and API Key.
- **Client login form defaults** (`RagInterface.tsx`): `tenantId` and `userId` now start as empty strings (force user to enter their own). Placeholder text uses `tn_...`/`usr_...` format. API key placeholder changed from `sk_live_...` to `ret_live_...` to match Retriever's actual key format.
- **ID validation relaxed** (`RagInterface.tsx`): `isUuid()` now accepts both UUIDs and short ID formats (`tn_X7kM2p`, `usr_Qp3N8w`) to prepare for future short ID migration.
- **API Base URL hidden** (`RagInterface.tsx`): The API URL field is collapsed under a "Show Advanced" toggle by default. Keeps the config panel clean for most users while allowing advanced users to override.
- **User ID column** (`tenant-users.tsx`): Added a "User ID" column to the tenant Users table with a copy-to-clipboard button, so admins can easily provide the internal UUID to clients.

### Manual Actions Required
- **Short ID migration** (recommended future work): Replace 36-character UUIDs with prefix-based short IDs (`tn_` for tenants, `usr_` for users) in the backend. Requires new DB columns and API path updates.

---

## 20. M33 Code Quality & Architecture — Completed

**Objective:** Break down the 2,250-line `main.py` monolith, eliminate type safety gaps, consolidate duplicated constants, and clean up inconsistent patterns across both the backend and frontend codebases.

### Changes Made
- **Full `main.py` decomposition** (2355→170 lines): Extracted 25 Pydantic DTOs to `src/schemas/` (7 files), business logic to `src/domain/` (inference, guardrails, retrieval), and all 55+ route handlers to 6 fully populated `src/routers/` modules (`health.py`, `admin.py`, `tenant.py`, `document.py`, `search.py`, `chat.py`). Created `src/container.py` for DI wiring of all ~25 singletons (repos, adapters, services, LLM providers, embedder, search, orchestrator, eval). Moved `llm_safety_guard` to `src/adapters/guardrails/` for architecture conformance.
- **Shared TypeScript types** (`Prateek_website/src/lib/rag-types.ts`): Defined `SearchResult`, `DocumentMeta`, and `SearchResponse` interfaces. Eliminates `any` type usage in `RagInterface.tsx`.
- **`API_BASE` consolidated**: Removed duplicate declarations from `login/page.tsx` and `onboard/page.tsx`. Both now import `API_BASE` from `lib/api.ts`.
- **RetrieverClient cleanup** (`rag-client.ts`): Refactored `uploadDocument` and `deleteDocument` to use the shared `request<T>()` method instead of duplicating fetch + header logic. Extracted shared auth header construction.
- **Duplicate cookie clearing removed** (`sidebar.tsx`): Removed the separate `document.cookie = ...` line from the logout handler — `clearKey()` in the auth store already handles cookie clearing.
- **Test `@patch` target fixes**: Updated 5 test files to patch router modules (`src.routers.chat`, `src.routers.admin`, `src.routers.document`) and new import paths (`src.adapters.cache.config_cache`, `src.schemas.document`) instead of `src.main`. All 369 tests pass (same baseline + 1 skipped).
- **Architecture conformance**: `domain/abstractions/` has 12+ pure ABCs with zero infrastructure imports. Enforced by `tests/test_architecture.py` AST analysis.

---

## 21. M34 Production Operations & DevOps — Completed

**Objective:** Eliminate manual SSH deploys, add error tracking and uptime monitoring, fix unbounded tenant queries, and close the remaining production operations gaps.

### Changes Made
- **GitHub Actions auto-deploy** (`.github/workflows/deploy-api.yml`): Creates SSH connection to Oracle VM, pulls latest code, reinstalls Python dependencies, restarts the `retriever-api` systemd service, and runs post-deploy smoke tests (liveness + readiness). Triggered by pushes to `main` affecting `apps/api/`, `packages/processing-core/`, or `workers/`.
- **Pagination fix** (`use-tenants.ts`): `useAllTenants()` now accepts a configurable `limit` parameter (default 50) instead of hardcoding `limit=1000`.

### Manual Actions Required
1. **Configure GitHub Secrets:** Add `ORACLE_HOST`, `ORACLE_USER`, `ORACLE_SSH_KEY` (and optionally `ORACLE_PORT`) to the repository's GitHub Secrets.
2. **Configure Sentry:** Set `SENTRY_DSN` in the production `.env` on the Oracle VM. Verify by triggering a test error in a route handler — it should appear in Sentry within 60 seconds.
3. **Set up uptime monitoring:** Configure UptimeRobot or Better Uptime to poll `https://rag.prateeq.in/health/liveness` every 5 minutes. Set up email/SMS alerts for downtime.

---

## 22. M35 Final Polish & Infrastructure Self-Detection — Completed

**Objective:** Add server-spec auto-detection for infrastructure services, update stale model defaults, clean up deprecated Docker Compose syntax, and improve the client chat UI for large screens.

### Changes Made
- **Server-spec auto-detection** (`config.py`): Added `InfraCapabilities` class that reads total RAM (`psutil.virtual_memory().total`) and CPU cores at startup. Logs detected specs and auto-decides which services to enable:
  - RAM >= 2 GB → Redis cache layer
  - RAM >= 2 GB → RabbitMQ broker
  - RAM >= 4 GB + 2+ cores → Celery workers
  - Falls back to LEAN mode (synchronous processing) on 1 GB Oracle VM.
  - Overridable via `REDIS_ENABLED`, `BROKER_ENABLED`, `WORKERS_ENABLED` env vars.
- **Gemini model updated** (`providers.ts`): Default changed from `gemini-1.5-flash` to `gemini-2.5-flash`.
- **Docker Compose cleaned** (`docker-compose.yml`): Removed deprecated `version: '3.8'` field.
- **Chat container height** (`rag.module.css`): Changed from fixed `400px` to `min(60vh, 600px)`.

---

## 23. Outstanding Blockers & Issues

- None. See `TECH_DEBT.md` for deferred architecture, test, security, migration, and product items.
