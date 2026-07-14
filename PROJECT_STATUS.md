# Project Status

Operational overview of the Retriever platform's current engineering status.

---

## 1. Status Overview

- **Current Milestone**: Milestone 14: Performance & Scale (Planned)
- **Last Completed Milestone**: Milestone 13: Multi-Industry Configurability
- **Build Status**: Passing (136/136 unit tests pass)
- **Admin Dashboard Build**: Passing (9 routes, all compile)
- **Reference Client Build**: Passing
- **Integration Tests**: 4/4 passing (adapter-level, requires `INTEGRATION_TEST=1`)
- **Next Recommended Milestone**: M14 (Performance & Scale)

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
- **Unit Test Coverage**: 17 test files covering ingestion, retrieval, inference, embedding, events, telemetry, health, config system, tenant domain, architecture conformance, admin API, client SDK (Milestone 11), production storage (Milestone 12), and custom splitting/metadata/guardrails pipelines (Milestone 13).
- **Admin API Tests**: 33 tests covering all 19 admin endpoints (tenants, users, API keys, config, documents, prompts CRUD+preview, audit logs).
- **Total Tests**: 136/136 passing (111 unit + 7 error-path tests added in tech debt sprint + 5 API surface/SDK tests in Milestone 11 + 6 storage/encryption tests in Milestone 12 + 7 pipeline configurability tests in Milestone 13).
- **Integration Tests**: 4 adapter-level tests (DB, Redis, tenant CRUD, document CRUD) — run with `INTEGRATION_TEST=1`.
- **Mock Quality**: 53 `@patch` decorators now use `autospec=True`.

### Documentation Health: **Green**
- **Blueprints**: Master Architecture, Core specifications, System Design outlines, and Admin Dashboard guide are complete.
- **Playbook**: Strict enforcement rules for database design, testing, RLS limits, and imports are documented.
- **ADRs**: Decisions for PostgreSQL, pgvector, FastAPI, Redis, RabbitMQ, Next.js, and SSE are recorded in `docs/decisions/`.
- **Admin Dashboard**: Full agent guide at `docs/features/admin-dashboard.md`.

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

## 7. Outstanding Blockers & Issues

- None. See `TECH_DEBT.md` for deferred architecture, test, security, migration, and product items.
