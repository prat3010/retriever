# Project Status

Operational overview of the Retriever platform's current engineering status.

---

## 1. Status Overview

- **Current Milestone**: Milestone 10: Admin Dashboard
- **Last Completed Milestone**: Milestone 9: Client Hierarchy & Admin API
- **Build Status**: Passing (111/111 unit tests pass)
- **Admin Dashboard Build**: Passing (9 routes, all compile)
- **Reference Client Build**: Passing
- **Next Recommended Milestone**: M11 (Client SDK)

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
- **Unit Test Coverage**: 14 test files covering ingestion, retrieval, inference, embedding, events, telemetry, health, config system, tenant domain, architecture conformance, and admin API.
- **Admin API Tests**: 33 tests covering all 19 admin endpoints (tenants, users, API keys, config, documents, prompts CRUD+preview, audit logs).
- **Total Tests**: 111/111 passing tests.

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
- 111/111 API tests passing (was 94)
- Ruff clean, web build clean

---

## 4. Outstanding Blockers & Issues

- None. See `TECH_DEBT.md` for deferred architecture, test, security, migration, and product items.
