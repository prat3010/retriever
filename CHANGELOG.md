# Changelog

All notable changes to the Retriever platform will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.18.0] - 2026-07-16
### Added
- **Developer Console (M25)**: Bootstrapped Next.js 16 workspace playground under `apps/developer-console/`. Integrates `@prat3010/retriever-client-js` SDK, SSE chat streaming, workspace sidebar navigation, and cited code snippet click modal view.
- **Key Validation Endpoint**: Added `POST /v1/config/validate-key` to verify active cognitive provider API keys.
- **Billing Security Guard**: Added `allow_platform_key` flag to `FeatureFlags` in tenant configurations. If `False`, blocks automatic env secret resolution for client queries, securing your billing credentials.
- **Local Ingestion Pipeline**: Overhauled `ingest_self.py` to generate vector records for the codebase using local Ollama (`nomic-embed-text` at port `11434`).

## [0.17.0] - 2026-07-15
### Added
- **Self-Querying Retrieval (M24)**: Default LLM metadata extraction during ingestion (doc_type, date_reference, topics, author_reference). `SelfQueryProvider` ABC + `enable_self_query` on `SearchQuery`. `LLMSelfQueryAdapter` parses NL queries into `MetadataFilter` lists via LLM. Wired into `HybridSearchService` as pipeline step 0 (parsed filters merge with explicit filters). 9 new tests.
- **Admin download URL bugfix**: Added missing `await` on `generate_presigned_url()` call at main.py:708 — admin file downloads were silently broken.
- **Migration drift fixes**: 3 Alembic migrations for `inference_logs.notes`, `semantic_cache` table, `audit_logs.entry_hash`/`previous_hash`.
- **Test hygiene**: `MagicMock`→`AsyncMock` in presigned URL tests; `asyncio.run()`→`await` in event tests.

### Changed
- **Long function refactoring**: `initialize_database` split into 6 async helpers (setup.py). `generate`/`generate_stream` share 5 extracted helpers in orchestrator.py (net -82 lines). `_apply_web_search_fallback` extracted from `search()`.
- **Polish pass**: Removed 10 redundant inline imports in `main.py` (`json`×4, `re`, `uuid` already at module level). Moved `logging`, `datetime` to module-level imports. Extracted `_check_idempotency`/`_cache_idempotency` helpers in `upload_document` (73→~40 lines). Extracted `_SLIDING_WINDOW_SCRIPT` constant + `_parse_rate_limit_result` helper in `rate_limiter.py` (`acquire` 75→17 lines). Added `AsyncGenerator` return types to `lifespan`, `event_stream`, `admin_download_document_file`.
- **Polish round 2**: Split `_apply_input_guardrails` into `_apply_pii_guard` + `_apply_llm_safety_guard` (59→~25 lines). Replaced `build_filter_clause` 10-branch if/elif chain with `_OP_TO_SQL` operator dict (60→~35 lines). Extracted shared `rows_to_search_results` from `search_similar`/`search_keywords` into `filter_builder.py`. Moved `StreamingResponse` + `select` to module-level imports.
- **Test coverage**: Added `test_cache_adapter.py` (11 tests), `test_vector_repository.py` (4 tests), `test_keyword_repository.py` (4 tests) — covering `RedisTenantConfigCache`, `PgVectorSearchAdapter`, and `PgKeywordSearchAdapter`.
- **Test coverage round 2**: Added `test_local_storage.py` (7 tests), `test_reranker.py` (7 tests), `test_telemetry_setup.py` (6 tests) — covering `LocalStorage`, `CohereRerankerAdapter`, and `get_tracer`/`get_metrics`/`get_rate_limiter`/`init_telemetry`. 286 tests passing.

## [0.16.0] - 2026-07-15
### Added
- **Multi-Modal Processing (M23)**: `ChatMessage.images` field for vision prompts. OpenAI and Anthropic adapters convert images to content blocks. `_describe_with_vision()` worker function describes images and zero-text PDFs via OpenAI vision API. `mime_type` passed through upload→Celery pipeline. `AIProviderConfig.vision_model` config. 11 new tests.

## [0.15.0] - 2026-07-15
### Added
- **Structured Data Extraction (M22)**: New `POST /v1/tenants/{tenantId}/documents/{documentId}/extract` endpoint accepts a JSON Schema and returns structured JSON extracted from document content. `get_document_chunks` method on `DocumentRepository` port + `SqlDocumentRepository` adapter.
- **json_schema wiring**: `InferenceRequest.json_schema` now active — OpenAI adapter sets `response_format={"type": "json_object"}`, Anthropic adapter appends schema hint to system prompt. 10 new tests.

## [0.14.0] - 2026-07-15
### Added
- **Web Search Grounding (M21)**: `WebSearchProvider` port + `TavilySearchAdapter` for live web fallback when local search scores fall below `web_search_threshold` (default 0.65). Wired into `HybridSearchService.search()` and both search/chat endpoints. 12 new tests.
- **TAVILY_API_KEY** env var in settings.
- **Tech debt ledger**: `TECH_DEBT.md` updated with deferred items from M20/M21.

## [0.13.0] - 2026-07-15
### Added
- **Token Cost Optimization (M20)**: `ModelPricing` schema + `DEFAULT_PRICING` on `AIProviderConfig`. `cost_usd` field on `Usage`, `InferenceLog`, `InferenceLogDb` + Alembic migration. `calculate_cost()` utility. Orchestrator emits `TOKEN_CONSUMPTION` and `COST_SPEND` Prometheus counters. 14 new tests.
- **Conversation Summarizer**: Long histories (>15 turns) are compressed via LLM summary before prompt building. Configurable via `summarize_after_turns`. Fails safe.
- **Anthropic streaming usage**: Captures token counts from `message_delta` events (was missing before).

## [0.12.0] - 2026-07-15
### Added
- **Smart Model Failover (M19)**: `ProviderUnavailableError` exception. `fallback_provider`, `fallback_model`, `retry_attempts`, `retry_delay_ms` on `AIProviderConfig`. Both adapters catch retryable SDK errors (5xx, timeout, connection, rate limit) and raise `ProviderUnavailableError`. `RoutingLLMProvider` retries with exponential backoff then falls back. `_actual_provider` tracked in `InferenceLog.notes`. 16 new tests.
- **Narrowed retryable errors**: `APIStatusError` → `InternalServerError` on both adapters so auth errors (401) propagate correctly.

## [0.11.0] - 2026-07-15
### Added
- **Typed Metadata Filter Operators**: Added `MetadataFilter` Pydantic model with 10 operators (`eq`, `neq`, `in`, `gt`, `gte`, `lt`, `lte`, `exists`, `contains`, `regex`) for both chunk-level metadata and document-level tag filtering.
- **Document Tags**: Added `tags TEXT[]` column to `documents` table with GIN index. Filtering via `JOIN documents ... d.tags @> ARRAY[:tags]` in vector and keyword search queries.
- **Rich Chunk Metadata Queries**: Added JSONB operators (`->>` for scalar, `?|` for array, `@>` for containment, `?` for key-existence, `~*` for regex) with proper SQL parameterization.
- **Shared Filter Clause Builder**: Extracted `build_filter_clause()` in `adapters/vector/filter_builder.py`, deduplicating previously copy-pasted filter logic from both search adapters.
- **GIN Index on meta_data**: Added `ix_document_chunks_meta_data` GIN index for index-scan performance on JSONB queries.
- **Filters and Tags in Chat Requests**: Added `filters` and `tags` fields to `ChatMessageRequest`, wired through the chat endpoint's grounding search.
- **JS SDK Filter Support**: Updated `@prat3010/retriever-client-js` with `MetadataFilter` type and `filters`/`tags` params on `search()`, `chat()`, `chatStream()`.
- **18 New Tests**: Covering all filter operators, tag filtering, combined filters, and domain model defaults.
- **173/173 tests passing** (was 155).

## [0.10.0] - 2026-07-14
### Added
- **Cryptographic Immutable Audit Logs**: Configured hash-linked append-only chains to ensure SOC 2 database logs protection.
- **OIDC/SSO Validation Layer**: Supported external token validation (RSA signature checking with cached JWKS public keys).
- **Tenant Data Retention Sweeper**: Implemented Celery scheduler to automatically purge expired documents and chat histories.
- **Granular Collection RBAC Scopes**: Supported resource-bound scopes (`collection:<name>:read`, `document_type:<ext>:write`) in endpoints security dependencies.

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
