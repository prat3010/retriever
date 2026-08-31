# Workspace Coding Rules & Constraints

## Architectural Constraints (Hexagonal & Multi-Tenancy)
- **Enforced Codebase Patterns:** Always follow the learned architectural conventions documented in `.agents/rules/patterns.md`.
- **Hexagonal Boundary Rule:** Code under `src/domain/` MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python libraries. **NEVER** import infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), database frameworks (`sqlalchemy`), or external API SDKs directly in domain files.
- **Multi-Tenancy Isolation Rule:** Every database entity, query method, and backend API MUST strictly scope operations by `tenant_id`. Frontend components MUST NOT hardcode fallback tenant UUIDs or silently default unauthenticated requests to guest UUIDs.

## Embedding Constraints
- **Always use a local model for generating embeddings.** (e.g., local Ollama using `nomic-embed-text` on `http://host.docker.internal:11434/v1`).
- **Do NOT use client-provided LLM keys** (such as Gemini, OpenAI, or Cohere) for embedding tasks to avoid hitting API rate limits and preserving quotas.

## Multi-Tenant & Scoping Integration Rules
- **Scoping Tenant Dogfooding Rule:** The Scoping engine on `prateeq.in` operates as a real standard tenant (`prateeq_scoping`). System prompts and knowledge documents are configured through standard tenant document ingestion and prompt settings without custom backend backdoor routing.
- **Client Auto-Onboarding & 7-Day Trial:** When a new commercial client signs in via Google OAuth on the website, Retriever's tenant provisioning API provisions a 7-day trial tenant (`tn_client_<uuid>`). The baseline SOW/scope details uploaded during onboarding are marked with `is_system = true` (or `is_deletable = false`), rendering them permanent and immutable in the client's document library.
- **Audit-First Contract Rule:** Any feature exposed for consumption by the frontend (such as `widget.js`, embed scripts, SSE streaming, document uploads, or GraphRAG traversals) must be fully tested, verified, and conforming to Hexagonal domain boundaries in `retriever` before frontend integration.

## Production-First & Zero-Toy Utility Invariant Rule (No Mocks, No Gimmicks)
- **Rule:** All backend algorithms, adapters, cognitive workflows, and administrative endpoints MUST be genuine, production-grade implementations with verified enterprise utility.
- **Strict Invariants:**
  1. **Zero Algorithmic Shortcuts or Fakes:** Do NOT implement naive regex heuristics and mislabel them as SOTA ML algorithms (e.g. calling simple regex "LongLLMLingua" or keyword matching "Llama Guard 3"). If an algorithm is specified, implement the authentic model/math or provide a transparent, explicitly labeled fallback.
  2. **Zero Mock Data Returns:** All endpoints must query real database models, execute genuine vector operations, and emit verified telemetry. Never return static synthetic mock data in production routers.
  3. **Pragmatic Production Value:** Prioritize core platform reliability (safe blue/green releases, atomic symlinks, rollback gates, concurrent load testing benchmarks, and unsupervised GraphRAG clustering) over cosmetic features.
  4. **Strict Conformance:** Every endpoint and adapter must be verified by automated Pytest suites with genuine database and memory integration.

## Code Style & Formatting Rules
- **Always run `ruff check --fix` on modified Python files** before making commits or finishing tasks to ensure imports and formatting conform to project CI standards.

## Agent Architecture Pre-Flight & Graph Intelligence
- **Architecture Knowledge Graph Pre-Flight:** Before creating, editing, or modifying ANY database table, API route router, domain service, or infrastructure adapter, the agent MUST run:
  ```bash
  python3 scripts/query_architecture.py --target <entity_or_api>
  ```
  to inspect the full blast radius, upstream callers, downstream dependencies, and linked PRDs.
## Deployment and Infrastructure Topology
- **Retriever Cognitive Engine (FastAPI Backend):** Deployed on Oracle Cloud VPS (`130.210.35.134` Ubuntu 24.04), mapped to `https://rag.prateeq.in`. Runs FastAPI, pgvector storage, and local Ollama embeddings (`nomic-embed-text`).
- **Retriever Admin Dashboard:** Deployed at **[`https://admin.rag.prateeq.in`](https://admin.rag.prateeq.in)** (`retriever/apps/web`). Used for tenant onboarding (`/onboard`), API key issuance, document vector ingestion, and system prompt configuration.
- **Web Application & Control Plane:** Deployed on Vercel at `https://prateeq.in`. Hosts the portfolio, `/scoping` engine, `/dashboard` client portal, and `/rag` product landing pages.

