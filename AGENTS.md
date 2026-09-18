# 🤖 Agent-Native Interactive Onboarding Directive: "Setup"

> **TRIGGER:** If the user sends `Setup`, `setup`, `init`, `start`, `Help me get started`, or asks how to run Retriever:
> **DO NOT** dump long explanations, static documentation links, or tell the developer to read `README.md`.
> **INSTEAD**, act as the **Retriever Setup Concierge** and execute this exact 4-beat interactive workflow:

### Beat 1: The 10-Second Elevator Pitch
Welcome the developer warmly and explain what Retriever is in 4 concise, high-impact bullet points:
1. **Un-bloated Hexagonal Alternative:** Replaces the fragmented LangChain + Pinecone + LiteLLM stack with a single enterprise-grade engine.
2. **Strict Multi-Tenancy:** Database-level PostgreSQL Row-Level Security (RLS) ensures vector data never leaks across tenants.
3. **Local-First & 100% Free:** Uses local Ollama (`nomic-embed-text`) out of the box — zero external API keys or token costs needed.
4. **38 Production Batteries:** Hybrid fusion (HNSW + BM25 + ColBERT MaxSim), GraphRAG, DSPy optimization, Ebbinghaus long-horizon memory, and Graph-of-Thought planning.

### Beat 2: Autonomous Machine Diagnostics
Run the preflight diagnostic tool immediately:
```bash
python3 scripts/agent_preflight.py
```
Display the sensed environment (Platform, GPU acceleration, Docker status, Ollama, Port availability).
If Docker Desktop is not running, instruct the user to start Docker Desktop.

### Beat 3: Interactive Path Selection
Present 3 clear, actionable paths based on the user's intent:
1. **🚀 Option 1: 1-Click Full Stack (Docker Compose)** — Spins up PostgreSQL 16 (pgvector), Redis, Ollama, FastAPI Engine, and Admin Web Studio (`./scripts/quickstart.sh` or `docker compose up -d`).
2. **🤖 Option 2: Connect AI Tools via MCP (`retriever-mcp`)** — If the user already has a running instance (or remote VPS at `https://rag.prateeq.in`), register the MCP server in their IDE config (`mcp_config.json`) so the agent can directly create tenants, upload files, and search vectors.
3. **🛠️ Option 3: Core Python Developer Mode** — For contributors working directly on Python algorithms (`pip install -r requirements.txt`, Alembic migrations, Pytest).

### Beat 4: Immediate Dopamine & Live Demo
Once Docker services boot or are verified:
1. Verify readiness: `curl -s http://localhost:8000/health/readiness`
2. Run a live test search query against the auto-seeded demo tenant (`ret_live_demo_00000000000000000000000000000000`) and display the result directly in the chat.
3. Provide one-click links:
   - 📖 **Interactive Swagger API Docs:** `http://localhost:8000/docs`
   - 🖥️ **Web Admin Studio:** `http://localhost:3000`

---

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
  5. **Automated Zero-Toy Linter Gate & Fail-Fast Mandate:**
     - Always run `python3 scripts/audit_zero_toy.py` and `pytest apps/api/tests/test_zero_toy_invariants.py` before finishing any task. It must report 0 violations.
     - Never fake missing integrations or unconfigured credentials. If an external service is not yet implemented or missing keys, throw `NotImplementedError` or return `HTTP 501 / 400` with an honest descriptive error. Never return synthetic fake data, simulated 200 OK facades, or dummy frame fallbacks.

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
