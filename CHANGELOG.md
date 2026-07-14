# Changelog

All notable changes to the Retriever platform will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-07-14
### Added
- **Hexagonal Semantic Cache**: Created abstract cache provider ports in domain layer and PgSemanticCacheAdapter database repository adapter in infrastructure layer.
- **SQL Batch Writes**: Rewrote background worker ingestion tasks to insert document chunks utilizing database parameter list bindings.
- **Eager Database Warmup**: Implemented eager SELECT 1 connections warmup during FastAPI startup.
- **SSE Connection Disconnect Cleanup**: Handled asyncio client cancellations within streaming loops to immediately release open thread handles.

## [0.8.0] - 2026-07-14
### Added
- **Multi-Strategy Text Splitters**: Integrated recursive character sliding splits and semantic topic-aware sentence chunking.
- **Dynamic Ingestion Extractors**: Integrated local regex extractors and structured LLM JSON extractors on workers.
- **Runtime Prompt Guardrails**: Implemented local PII regex scrubber and LLM prompt injection validator.
- **Format-Aware Citation Replacer**: Implemented post-processed swappers formatting verified citations matching customizable templates (handles streaming & static completions).
- **Admin Configuration Presets**: Defined templates for `legal`, `hr`, `medical`, and `finance` presets.

## [0.7.0] - 2026-07-14
### Added
- **S3 Storage Adapter**: Created standard `S3Storage` adapter using boto3, allowing documents to be stored in cloud object storage (AWS S3, MinIO, Cloudflare R2).
- **At-Rest Config Credentials Encryption**: Implemented AES-256-GCM encryption on tenant AI/embedding API keys in database JSONB configurations, utilizing a server Key Encryption Key (KEK).
- **Dynamic Database Connection Pooling**: Enabled configurable async engine pooling settings (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, etc.).
- **S3 Connectivity Health Probe**: Added bucket reachability verification checks inside FastAPI readiness probes.
- **Admin Document Download Endpoint**: Created pre-signed URL download generators and local file streaming endpoints.

## [0.6.0] - 2026-07-14
### Added
- **Cursor-Based Pagination**: Created base64 JSON cursors encoding timestamps and UUIDs. Added cursor paginated queries to list tenants, list documents, and list session messages.
- **X-RateLimit Response Headers**: Modified sliding-window Redis Lua script and FastAPI dependencies to inject `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers dynamically.
- **Upload Idempotency Keys**: Implemented 24-hour Redis response caches on `POST /v1/tenants/{id}/documents` to prevent duplicate files and parsing worker triggers.
- **TypeScript Client SDK**: Created `@prat3010/retriever-client-js` packages in monorepo, supporting buffer/blob uploads, hybrid search, paginated listings, and SSE streaming iterators.
- **OpenAPI Schema Exporter**: Created a script `scripts/generate_openapi.py` to dump Swagger schemas to `docs/openapi.json`.

## [0.5.1] - 2026-07-14
### Added
- **Integration Test Scaffold**: `docker-compose.test.yml` (postgres+pgvector:5433, redis:6380, rabbitmq:5673), 4 adapter-level tests covering DB/Redis connectivity, tenant CRUD, and document CRUD against real services. Requires `INTEGRATION_TEST=1` env var.
- **7 Error-Path Tests**: readiness 503, doc GET/DELETE 404, missing file 422, config missing auth 401, invalid payload 422, streaming chat SSE.
- **`autospec=True`**: Added to 53 `@patch` decorators across 10 test files (excludes `AsyncMock` and `audit_logger.list`).
- **greenlet dependency**: Required by SQLAlchemy async engine.

### Fixed
- **Duplicate index in models.py**: `ChatSessionDb.user_id` and `ChatMessageDb.user_id` had both `index=True` on Column AND explicit `Index()` in `__table_args__`, causing `DuplicateTableError` on `initialize_database()`. Removed `index=True` from both columns.
- **SET LOCAL with parameterized query**: PostgreSQL's `SET` doesn't support `$N` parameters — switched from bindparam to f-string in `connection.py:41`.
- **Shared mutable state in tests**: `tenant_id`/`key_id` moved to fixtures in `test_admin_api.py`; `clean_temp_files` fixture replaces module-level `clean_storage` in `test_ingestion.py`.

### Changed
- Integration tests now test repository adapters directly (not via HTTP) to avoid anyio/Starlette event-loop conflicts.
- CI runs pytest with `-m "not integration"` to skip integration tests.

## [0.5.0] - 2026-07-14
### Added
- **DocumentRepository Port**: Extracted `DocumentRepository` port in `domain/abstractions/ingestion.py` with 5 methods (list_documents, get_document, find_by_hash, create_document, soft_delete).
- **SqlDocumentRepository Adapter**: Implemented in `adapters/database/document_repository.py`, wired into `main.py` replacing 5 inline SQLAlchemy blocks. Removed unused imports.

### Fixed
- **Ingestion Tests**: Migrated 7 tests from mocking `src.main.tenant_session` (removed) to mocking `document_repository` methods — all 111 tests passing again.

### Changed
- Cleaned up unused imports in `main.py`, `security.py`, and test files. Ruff clean.

## [0.4.0] - 2026-07-12
### Added
- **Layout-Aware PDF Parser**: Integrated `pdfplumber` adapter extracting layout-preserved text segments from documents.
- **Token-Aware Chunker**: Added `tiktoken` (cl100k_base tokenizer) sliding window chunker with overlapping limit protections.
- **Ingestion Database Models**: Added SQL tables for `documents` and `document_chunks` with Row-Level Security (RLS) policies.
- **Local Storage Provider**: Implemented filesystem local storage saving raw assets in tenant-specific folders.
- **Asynchronous Celery Workers**: Configured RabbitMQ background queue processing document chunking tasks.
- **Ingestion API Endpoints**: Exposed endpoints for document upload, listing, status verification, and deletion.

### Fixed
- **Hexagonal Architecture Segregation**: Moved security validation out of the domain layer to the API adapter namespace.
- **RBAC API Scopes**: Integrated token-scoped checks (`document:read`, `document:write`) for tenant routes.
- **Alembic Database Migrations**: Configured asynchronous migrations setup with a baseline schema.
- **Stateful Health Probes**: Upgraded readiness endpoint to query active Postgres and Redis connections.

---

## [0.3.0] - 2026-07-12
### Added
- **Configuration Domain**: Defined models for global/tenant scopes, feature flags, AI/embedding/storage providers, and retrieval limits.
- **SQL Configuration Registry**: Built the repository adapter saving serialized JSONB payloads, tracking versions, and supporting soft deletion.
- **Configuration Service**: Implemented dynamic tenant inheritance (tenant overrides merging over global baseline configurations) and environment fallback resolution.
- **API Configuration Controls**: Added endpoints to get and put global configurations (`/v1/config/global`) and tenant overrides (`/v1/tenants/{tenantId}/config`), redacting sensitive credentials.
- **L1 Redis Cache Mapping**: Configured configuration cache with helper parameters backing hot reloads, cache warming, and fallback routing.
- **RLS Configurations Policies**: Applied row-level security isolation on the `configurations` table.

---

## [0.2.0] - 2026-07-12
### Added
- **Identity Port**: Added `IdentityProvider` port defining API key verification logic.
- **Tenant Port**: Added `TenantRegistry` port managing dynamic configuration (CAD) payloads.
- **Relational Models**: Setup database models for `tenants`, `tenant_configs`, `api_keys`, and `audit_logs`.
- **RLS Policy Installer**: Created database setup helper enforcing `ALTER TABLE ENABLE ROW LEVEL SECURITY` on customer tables.
- **RLS Connection Manager**: Built the async connection manager wrapping SQL session bindings to set `app.current_tenant_id` and `app.bypass_rls`.
- **Redis Config Caching**: Enabled in-memory caching for tenant settings with write-through invalidation and a 1-hour TTL.
- **Breach Kill-Switch**: Implemented validation checks that deactivate credentials in the database immediately and raise a `TenantIsolationViolationError` upon a tenant context breach.
- **API Endpoints**: Exposed tenant registration (`POST /v1/tenants`), config parameters (`PUT/GET /v1/tenants/{tenantId}/config`), and token generation (`POST /v1/tenants/{tenantId}/api-keys`).

### Fixed
- Changed parameter references in security dependencies to match FastAPI route paths, fixing route validation (422) failures.
- Resolved Pydantic deprecation warnings by migrating model configurations from class `Config` to `model_config = ConfigDict(...)`.

---

## [0.1.0] - 2026-07-12
### Added
- **Monorepo Layout**: Initialized project workspaces (`apps/api`, `apps/web`, `workers`, `packages`).
- **Gateway Server**: Configured FastAPI API gateway with type-safe environments and health check probes.
- **Dashboard UI**: Set up Next.js playground dashboard layout styled with Outfit/Inter typography and HSL color parameters.
- **Linting & Formatting**: Configured Ruff for Python static checks, and ESLint + Prettier for JavaScript workspaces.
- **Background worker**: Set up Celery asynchronous worker daemon scaffolding.
- **Orchestration**: Configured `docker-compose.yml` supporting pgvector, Redis, and RabbitMQ container nodes.
- **CI/CD Workflow**: Created GitHub Actions configuration file.

### Fixed
- Fixed Node.js installation action in the CI/CD workflow, replacing the invalid `setup-version` tag with `setup-node`.
- Fixed `uv` package installation commands inside Python container configurations.
