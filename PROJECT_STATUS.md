# Project Status

Operational overview of the Retriever platform's current engineering status.

---

## 1. Status Overview

- **Current Milestone**: Milestone 23: Multi-Modal Processing (Completed)
- **Last Completed Milestone**: Milestone 23: Multi-Modal Processing
- **Build Status**: Passing (238+ unit tests pass)
- **Admin Dashboard Build**: Passing (9 routes, all compile)
- **Reference Client Build**: Passing
- **Integration Tests**: 4/4 passing (adapter-level, requires `INTEGRATION_TEST=1`)
- **Next Recommended Milestone**: Milestone 24: Self-Querying Retrieval

---

## 2. Health Indicators

### Architecture Health: **Green**
- **Hexagonal Architecture Compliance**: Enforced by `tests/test_architecture.py` on every test run. Core domains contain no database or framework imports.
- **Tenancy Boundary Controls**: PostgreSQL Row-Level Security (RLS) active on all customer-data tables.
- **Tenancy Breach Kill-Switch**: Verified. Context-level validation disables API keys and throws 403.
- **Dynamic Config Override (CAD)**: Supports inheritance merging tenant overrides on top of global configs.
- **No Hardcoded Prompts**: Enforced by conformance test and `PromptTemplateNotFoundError`.
- **Client Integration Model**: Documented in architecture.md §15. API key + `X-User-ID` contract defined.

### Testing Status: **Green**
- **Unit Test Coverage**: 26 test files covering ingestion, retrieval, inference, embedding, events, telemetry, health, config system, tenant domain, architecture conformance, admin API, client SDK (M11), production storage (M12), custom pipelines (M13), semantic caching / worker batching (M14), enterprise cryptographic audit chains / data retention schedulers (M15), metadata & tag filtering (M18), model failover (M19), token cost optimization (M20), web search grounding (M21), structured data extraction (M22), and multi-modal processing (M23).
- **Admin API Tests**: 33 tests covering all 19 admin endpoints (tenants, users, API keys, config, documents, prompts CRUD+preview, audit logs).
- **Total Tests**: 238/238 passing.
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
- `httpx` → `httpx2` migration (Starlette deprecation fix)
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

## 15. Outstanding Blockers & Issues

- None. See `TECH_DEBT.md` for deferred architecture, test, security, migration, and product items.
