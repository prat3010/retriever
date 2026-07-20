# Tech Debt & Future Work

Items identified during audits that were deferred. Fix when
they start blocking you — not before.

## Fixed

| Item | Commit |
|------|--------|
| `API_BASE` constant duplicated in 3 places (api.ts, login/page.tsx, onboard/page.tsx) | M33 |
| `isUuid` accepted short ID formats (`tn_*`, `usr_*`) with no backend support | Reverted |
| `uploadDocument` and `deleteDocument` in `rag-client.ts` bypassed shared `request<T>()` — duplicated fetch + header logic | M33 |
| `sidebar.tsx` logout handler had duplicate cookie-clearing code (already done by `clearKey()`) | M33 |
| `RagInterface.tsx` used `any` types with `eslint-disable` — no shared TypeScript interfaces for SearchResult, DocumentMeta, SearchResponse | M33 |
| `useAllTenants` fetches 1000 records at once — no pagination | M34 |
| No auto-deploy pipeline for Oracle VM — manual SSH deploys required | M34 |
| Gemini default model was `gemini-1.5-flash` (outdated) | M35 |
| Chat container `max-height: 400px` felt cramped on large screens | M35 |
| No server-spec auto-detection for Redis/RabbitMQ/Celery enablement | M35 |
| `main.py` god-file (2,250+ lines) — initial router split: health and admin routes extracted | M33 |
| Onboarding wizard didn't create a user — clients got incomplete credentials (no User ID) | M32 |
| Client login form had production data as defaults (pre-filled tenantId/userId, wrong placeholder) | M32 |
| Users tab didn't show internal User ID for admin copy-to-clipboard | M32 |
| Secrets committed to repo (`.env` with Supabase/OpenAI creds, `apps/web/.env.local` with Vercel OIDC token) | M31 |
| `ADMIN_MASTER_KEY` and `KEY_ENCRYPTION_KEY` have no production guard — crash if defaults used in production | M31 |
| `proxy.ts` only checks if `admin_key` exists, not if it's valid — any non-empty string bypasses redirect | M31 |
| Port 8000 open to public on Oracle VM (bypasses Nginx SSL) | M31 |
| `verify_admin_key` returns 422 instead of 401 | `a6f49a0` |
| `verify_scopes` silently succeeds when used without `Security()` | `a6f49a0` |
| `redact_secrets` truthy check → `is not None` | `a6f49a0` |
| No UUID validation on `X-User-ID` header | `a6f49a0` |
| Streaming `finish_reason` double-yield dead code | `a6f49a0` |
| `backref` → `back_populates` consistency | M10 cleanup |
| `"query:execute"` dead scope removed | M10 cleanup |
| Column width IF EXISTS guards → bare `alter_column` | M10 cleanup |
| `os.getenv()` in domain → injected env_secrets | M10 cleanup |
| Breach kill-switch bypasses `IdentityProvider` port | M10 cleanup |
| No `autospec=True` on mocks (53 patches updated) | `f760f68` |
| Missed error-path tests (7 added) | `f760f68` |
| Shared mutable state in tests (admin_api + ingestion) | `f760f68` |
| Duplicate `index=True` on `ChatSessionDb.user_id` / `ChatMessageDb.user_id` | `f760f68` |
| `SET LOCAL` uses bindparam instead of f-string (PG doesn't support `$N` params in SET) | `f760f68` |
| `greenlet` dependency missing (SQLAlchemy async requirement) | `12c301a` |
| Missing `await` on `generate_presigned_url()` — admin download silently broken | M24 polish |
| 3 migration drifts: `inference_logs.notes`, `semantic_cache` table, `audit_logs` hashes | M24 polish |
| `MagicMock` → `AsyncMock` in presigned URL tests | M24 polish |
| 10 redundant inline imports in `main.py` (`json`×4, `re`, `uuid` — already at module level) | M24 polish |
| Missing module-level imports: `logging`, `datetime.UTC` | M24 polish |
| `upload_document` (73 lines) refactored — extracted `_check_idempotency`/`_cache_idempotency` | M24 polish |
| `rate_limiter.py:acquire` (75 lines) refactored — extracted Lua script constant + result parser | M24 polish |
| Missing return type annotations: `lifespan`, `event_stream`, `admin_download_document_file` | M24 polish |
| `_apply_input_guardrails` (59 lines) split into `_apply_pii_guard` + `_apply_llm_safety_guard` | M24 polish |
| `build_filter_clause` 10-branch if/elif chain replaced with `_OP_TO_SQL` operator dict (60→~35 lines) | M24 polish |
| Duplicate row mappers in `search_similar`/`search_keywords` replaced with shared `rows_to_search_results` | M24 polish |
| `StreamingResponse` + `sqlalchemy.select` moved from inline to module-level imports | M24 polish |
| No local OCR (Tesseract) — pytesseract fallback added | C-4 Sprint 2 |
| First-page-only PDF vision — multi-page vision loop | C-4 Sprint 2 |
| Token budget alert thresholds — `BudgetSettings` + `NotificationProvider` | E-6 Sprint 3 cleanup |
| Vision config not tenant-aware / platform key fallback | M25 cleanup |
| Streaming token telemetry early break (OpenAI & Anthropic) | M25 cleanup |
| SQL injection in PostgreSQL connection manager `tenant_session` | M25 cleanup |
| Lack of automatic batching in `embed_with_retry` | M25 cleanup |
| Plaintext parsing loophole for binary document uploads | M25 cleanup |

## Architecture

### `main.py` god-file — Partial Split (M33)
**File:** `apps/api/src/main.py`

Remaining routes (~2,200 lines) still need to be extracted into `routers/tenant.py`, `routers/document.py`, `routers/search.py`, `routers/chat.py`. The pattern is established with `routers/health.py` and `routers/admin.py`.

### ~~`DocumentRepository` port~~ (Fixed)
**File:** `apps/api/src/main.py:577-722`

Document CRUD now uses `SqlDocumentRepository` via `DocumentRepository` port
in `domain/abstractions/ingestion.py`, wired into `main.py`.

### ~~`security.py` bypasses `IdentityProvider` port during breach~~ (Fixed in `(this commit)`)
**File:** `apps/api/src/adapters/api/security.py:96-99`

`verify_tenant_isolation` executes `update(ApiKeyDb)` directly instead
of calling `identity_provider.revoke_api_key()`. Changes to key
revocation logic (logging, notifications) added to the provider are
silently missed.

Fix: inject the provider and call it instead.

### ~~`verify_scopes` silently succeeds when used without `Security()`~~ (Fixed in `a6f49a0`)
**File:** `apps/api/src/adapters/api/security.py:115`

If someone writes `Depends(verify_scopes)` instead of
`Security(verify_scopes, scopes=[...])`, scope checks are skipped with
no error. Add a guard:

```python
if not security_scopes.scopes:
    raise HTTPException(500, "verify_scopes used without scopes")
```

### ~~`verify_admin_key` returns 422 instead of 401 when header is missing~~ (Fixed in `a6f49a0`)
**File:** `apps/api/src/adapters/api/security.py:125`

`Header(...)` with ellipsis makes it required — FastAPI returns 422
before the function body runs. Change to `Header(None)` + explicit
`if not x_admin_master_key: raise ...`.

### ~~`os.getenv()` in domain layer~~ (Fixed in `(this commit)`)
**File:** `apps/api/src/domain/config/config_service.py:87`

`ConfigurationService._resolve_env_variables` reads environment
variables from the process. Hexagonal architecture says domain should
be unaware of its execution environment. Inject secrets during
construction instead.

## Test Coverage

### Source files with zero test coverage
| File | Risk |
|------|------|
| `adapters/telemetry/middleware.py` | Observability gaps |
| `adapters/database/setup.py` | Migration/RBAC setup untested |
| All `workers/` files (354 lines) | Async pipeline untested |

### Source files with new test coverage added during M24 polish round
| File | Tests |
|------|-------|
| `adapters/cache/config_cache.py` | 11 |
| `adapters/vector/vector_repository.py` | 4 |
| `adapters/vector/keyword_repository.py` | 4 |
| `adapters/storage/local_storage.py` | 7 |
| `adapters/cognitive/reranker_adapter.py` | 7 |
| `adapters/telemetry/setup.py` | 6 |

## Observability

### No inference telemetry logged for admin requests
When an admin key is used on chat endpoints, `get_current_user_id`
returns a `None` user_id. But inference logs still record the
interaction. Add admin-specific tags or skip logging for admin
impersonation.

### `UserContext.user_id` always empty string for API key auth
**File:** `apps/api/src/adapters/database/identity_repository.py:60`

`validate_token` always returns `user_id=""`. Document and search
endpoints have no user-scoped audit trail. Either populate from the
key metadata or accept the gap.

## Security

### ~~`verify_scopes` scope `"query:execute"` is never checked~~ (Fixed in `(this commit)`)
**File:** `apps/api/src/adapters/database/identity_repository.py:56`

Client keys are granted `"query:execute"` but no endpoint checks it
(the search endpoint uses `"document:read"`). Remove the dead scope
or enforce it.

### ~~No UUID validation on `X-User-ID` header~~ (Fixed in `a6f49a0`)
**File:** `apps/api/src/adapters/api/security.py:46-61`

Malformed UUID → `uuid.UUID(user_id)` raises `ValueError` → 500.
Add a try/except or validate with a regex before passing downstream.

## Migration / Schema

### Orphan columns in DB (not mapped by ORM)
These columns exist from the initial migration but models were
refactored to remove them. Harmless but untidy.

| Table | Orphan Columns |
|-------|----------------|
| `tenants` | `isolation_level`, `updated_at` |
| `tenant_configs` | `created_at`, `updated_at` |
| `api_keys` | `scopes`, `updated_at` |

Either drop them (if no code reads them) or add them back to the
model. If dropped, preserve data by copying to app-level fields.

### ~~`backref` vs `back_populates` inconsistency~~ (Fixed in `(this commit)`)
**File:** `apps/api/src/adapters/database/models.py:42`

`TenantDb.sessions` uses legacy `backref="tenant"`. Every other
relationship uses the newer `back_populates`. Fix for consistency.

### No `server_default` on many columns
Multiple columns have Python-level defaults but no DB-level
`server_default`. Raw SQL inserts bypassing the ORM get NULL.
Not urgent unless you write raw SQL queries against the DB.

## Product / scale

### ~~Column width IF EXISTS guards~~ (Fixed in `(this commit)`)
`tenants.name`, `api_keys.name`, `api_keys.prefix`, and
`api_keys.key_hash` were widened from 100/16/64 to 255/50/255 in the
model but the migration (`3e9a1b2c4d5f`) only alters them if they're
still at the old width. Once all environments are migrated, remove
the IF EXISTS guards.

### ~~Streaming `finish_reason` double-yield (dead code)~~ (Fixed in `a6f49a0`)
**File:** `apps/api/src/adapters/cognitive/openai_adapter.py:109`

Code yields `{"finish_reason": "stop"}` after the stream loop breaks
on the actual finish reason. Currently never consumed (orchestrator
breaks on the first finish_reason). Either remove it or wire it as a
fallback.

### ~~`redact_secrets` uses truthy check instead of `is not None`~~ (Fixed in `a6f49a0`)
**File:** `apps/api/src/domain/abstractions/config.py:64,66`

`if key:` should be `if key is not None:`. Empty string redaction
gap. Fix when a provider with empty-string API key is added.

## Product / Deferred (M20 & M21)

### Per-message `token_count` on `ChatMessage`
**Files:** `apps/api/src/domain/abstractions/inference.py`, `apps/api/src/adapters/database/models.py`  

`ChatMessage` and `ChatMessageDb` have no `token_count` field. Adding it would enable per-message token accounting in the dashboard. Skipped because `InferenceLog` already tracks total cost — add when a feature needs per-message token display.

### Brave Search adapter
**File:** (none — doesn't exist yet)  

Only `TavilySearchAdapter` is implemented. Brave Search would be useful as a redundancy or cost-saving alternative. Add when Tavily API key is absent or rate limits become a blocker.

### Per-tenant web search API keys
**Files:** `apps/api/src/config.py`, `apps/api/src/adapters/cognitive/tavily_adapter.py`  

Web search API key is platform-level (`TAVILY_API_KEY` env var). No per-tenant override exists. Add when tenants need to bring their own web search credentials.

### Embedding/chunking web results
**File:** `apps/api/src/domain/retrieval/search_service.py`  

Web results are injected as raw text (`[Web: Title](url)\n{content}`) without chunking or embedding. This works for shallow fallback but longer web content could exhaust the context window. Add proper chunking + embedding when web results regularly exceed 2k tokens.

### ~~Token budget alert thresholds~~ (Fixed in E-6)
**Files:** `apps/api/src/domain/abstractions/config.py`

No `monthly_token_budget` or `budget_alert_threshold` config fields exist. The Prometheus `COST_SPEND` counter is emitted but not hooked to alerts. Add when a tenant needs spend caps (related to M25).

*Fixed: `BudgetSettings` + `NotificationProvider` port + `LoggingNotificationAdapter` added. In-memory daily/monthly accumulation with threshold crossing alerts in `orchestrator._check_budget()`.*

### Admin dashboard cost charts
**File:** (none — doesn't exist yet)  

`InferenceLog.cost_usd` is recorded but not surfaced in the dashboard. Add cost-per-tenant charts when the admin UX needs billing visibility.

### Web search result citation validation
**File:** `apps/api/src/domain/retrieval/search_service.py`  

Web results use `document_id="__web__"` and fake `chunk_id`s, so `CitationValidator` won't match `[Source: web_...]` citations. The LLM may still reference them but citations won't be verified. Fix by adding web results to the valid IDs set, or by skipping citation check for `__web__` documents.

## Product/Deferred (M22)

### No JSON Schema validation
**File:** `apps/api/src/main.py`  

Extraction endpoint returns the LLM output as-is after `json.loads()`. No server-side JSON Schema validation is performed — the schema is only used as a prompt hint. Add `jsonschema` or `fastapi` built-in validation when extraction reliability needs to be guaranteed.

### No pagination on get_document_chunks
**File:** `apps/api/src/adapters/database/document_repository.py`  

`get_document_chunks` loads all chunks in one query. For documents with 10k+ chunks this could be slow. Add pagination or streaming when documents exceed 500 chunks.

### Anthropic has no native JSON mode
**File:** `apps/api/src/adapters/cognitive/anthropic_adapter.py`  

Anthropic doesn't expose a `response_format={"type": "json_object"}` equivalent. The schema hint in the system prompt is best-effort. Switch to tool-calling (`tool_choice` with a single function) when Anthropic's JSON reliability becomes an issue. Claude 3.5+ models support `anthropic-json` mode via the `text` content block with a `thinking` config — revisit when the SDK stabilizes.

### No extraction streaming
**File:** `apps/api/src/main.py`  

Extraction endpoint returns a blocking JSON response. Add SSE streaming for large document extraction if latency becomes a concern.

## Product/Deferred (M23)

### ~~No local OCR (Tesseract)~~ (Fixed in C-4)
**File:** `workers/src/tasks/__init__.py`

Vision extraction uses OpenAI vision API only — no local Tesseract OCR. This works for all image types but has per-call cost and latency. Add `pytesseract` + `TesseractOCR` system binary when throughput or cost requires offline processing.

*Fixed: `_ocr_with_tesseract()` chained before vision API, `pytesseract>=0.3.10` dep added.*

### ~~First-page-only PDF vision~~ (Fixed in C-4)
**File:** `workers/src/tasks/__init__.py` (in `_describe_with_vision`)

For zero-text PDFs, only the first page is described. Long scanned documents will miss later pages. Iterate all pages when multi-page scanned PDFs become a common workload.

*Fixed: removed `break` after first page — all pages are now described and concatenated.*

### No Anthropic vision in worker
**File:** `workers/src/tasks/__init__.py`  

Worker `_describe_with_vision` hard-codes OpenAI. Add Anthropic Claude vision path (`claude-3-5-sonnet`) when the provider config switches away from OpenAI.

### ~~Worker vision config not tenant-aware~~ (Fixed)
**File:** `workers/src/tasks/__init__.py`  

`_describe_with_vision` reads `vision_model` from the document's tenant config but uses `OPENAI_API_KEY` env var. Add per-tenant API key routing when multi-tenant vision use cases emerge.

*Fixed: added _get_decrypted_key helper to resolve tenant-specific keys in tasks.*
