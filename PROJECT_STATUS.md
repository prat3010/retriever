# Project Status

Operational overview of the Retriever platform's current engineering status.

---

## 1. Status Overview

- **Current Milestone**: Milestone 10: Admin Dashboard
- **Last Completed Milestone**: Milestone 9: Client Hierarchy & Admin API
- **Build Status**: Passing (94/94 unit tests pass)
- **Admin Dashboard Build**: Passing (all pages compile)
- **Reference Client Build**: Passing
- **Next Recommended Milestone**: M10 enhancements or M11 (Client SDK)

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
- **Unit Test Coverage**: 13 test files covering ingestion, retrieval, inference, embedding, events, telemetry, health, config system, tenant domain, architecture conformance, and admin API.
- **Admin API Tests**: 16 tests covering all 11 admin endpoints (tenants, users, API keys, config).
- **Total Tests**: 94/94 passing tests.

### Documentation Health: **Green**
- **Blueprints**: Master Architecture, Core specifications, System Design outlines, and Admin Dashboard guide are complete.
- **Playbook**: Strict enforcement rules for database design, testing, RLS limits, and imports are documented.
- **ADRs**: Decisions for PostgreSQL, pgvector, FastAPI, Redis, RabbitMQ, Next.js, and SSE are recorded in `docs/decisions/`.
- **Admin Dashboard**: Full agent guide at `docs/features/admin-dashboard.md`.

---

## 3. M10 Admin Dashboard — Current State

### Pages (6 routes)
| Route | Description |
|---|---|
| `/login` | Admin master key authentication |
| `/` | Dashboard home with stats overview |
| `/onboard` | 3-step client onboarding wizard |
| `/tenants` | Tenant list with deactivate |
| `/tenants/[id]` | Tenant detail (4 tabs: overview, users, API keys, config) |
| `/tenants/[id]/playground` | API endpoint test console |

### Infrastructure
- Tailwind v4 + shadcn/ui (13 components)
- TanStack Query with caching + mutations
- Zustand auth store (sessionStorage)
- Middleware auth guard
- Error boundary wrapper
- sonner toast notifications

### Reference Client
- Standalone Next.js app at `apps/client-reference/`
- Demonstrates `X-API-Key` + `X-User-ID` integration pattern
- Tabs: Config, Chat (SSE streaming), Search, Documents

### Outstanding
See `TECH_DEBT.md` and `ROADMAP.md` for planned enhancements.

---

## 4. Outstanding Blockers & Issues

- None. See `TECH_DEBT.md` for deferred architecture, test, security, migration, and product items.
