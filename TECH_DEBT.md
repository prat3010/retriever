# Tech Debt & Future Work

Items identified during audits that were deferred. Fix when
they start blocking you — not before.

## Fixed in M10 cleanup

| Item | Commit |
|------|--------|
| `verify_admin_key` returns 422 instead of 401 | `a6f49a0` |
| `verify_scopes` silently succeeds when used without `Security()` | `a6f49a0` |
| `redact_secrets` truthy check → `is not None` | `a6f49a0` |
| No UUID validation on `X-User-ID` header | `a6f49a0` |
| Streaming `finish_reason` double-yield dead code | `a6f49a0` |

## Architecture

### `DocumentRepository` port
**File:** `apps/api/src/main.py:577-722`

Document CRUD uses raw SQLAlchemy in route handlers. There's no
`DocumentRepository` port in `apps/api/src/domain/abstractions/`. This
makes the document layer untestable without a real DB and prevents
swapping storage backends.

Add: `domain/abstractions/ingestion.py` port, `adapters/database/document_repository.py`
impl, wire into `main.py`.

### `security.py` bypasses `IdentityProvider` port during breach
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

### `os.getenv()` in domain layer
**File:** `apps/api/src/domain/config/config_service.py:87`

`ConfigurationService._resolve_env_variables` reads environment
variables from the process. Hexagonal architecture says domain should
be unaware of its execution environment. Inject secrets during
construction instead.

## Test Coverage

### No `autospec=True` on any mock
**Files:** all `tests/` files

Every `@patch` and `MagicMock`/`AsyncMock` lacks `autospec=True`.
Mocks silently diverge from the real API. Dependency upgrades break
in production, not in tests. Add `autospec=True` to every mock.

### 15+ source files with zero test coverage
| File | Risk |
|------|------|
| `adapters/cognitive/reranker_adapter.py` | Reranker failures undetected |
| `adapters/cognitive/openai_adapter.py` (stream path) | Streaming bugs ship |
| `adapters/storage/local_storage.py` | File I/O errors undetected |
| `adapters/cache/config_cache.py` | Cache logic untested |
| `adapters/telemetry/middleware.py` | Observability gaps |
| `adapters/telemetry/setup.py` | Init failures undetected |
| `adapters/database/setup.py` | Migration/RBAC setup untested |
| `domain/inference/orchestrator.py` (stream path) | Streaming bugs ship |
| All `workers/` files (354 lines) | Async pipeline untested |
| All `packages/processing-core/` files | Core chunking/parsing untested |

### Missed error-path tests
- `GET/POST/PUT /v1/admin/...` with invalid admin key (401)
- `GET/PUT /v1/tenants/{id}/config` missing auth
- `GET/DELETE /v1/tenants/{id}/documents/{id}` not found (404)
- `POST /v1/tenants/{id}/documents` empty file upload
- Readiness endpoint when DB/Redis down (503)
- All stream=True chat paths
- All scope-based 403 rejections
- Input validation 422 errors

### Shared mutable state in tests
**File:** `tests/test_admin_api.py:24-25`

Module-level `tenant_id = uuid.uuid4()` means tests share state.
Breaks under `pytest-xdist`. Move to per-test fixtures.

**File:** `tests/test_ingestion.py:241`

Real filesystem I/O in tests (`./sample_test.txt`). Interrupted run
leaks files. Delete: mock the filesystem instead.

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

### `verify_scopes` scope `"query:execute"` is never checked
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

### `backref` vs `back_populates` inconsistency
**File:** `apps/api/src/adapters/database/models.py:42`

`TenantDb.sessions` uses legacy `backref="tenant"`. Every other
relationship uses the newer `back_populates`. Fix for consistency.

### No `server_default` on many columns
Multiple columns have Python-level defaults but no DB-level
`server_default`. Raw SQL inserts bypassing the ORM get NULL.
Not urgent unless you write raw SQL queries against the DB.

## Product / scale

### Column width limits may bite
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
