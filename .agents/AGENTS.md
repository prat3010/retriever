# 🤖 Agent-Native Interactive Onboarding Directive: "Setup"

> **TRIGGER:** If the user sends `Setup`, `setup`, `init`, `start`, `Help me get started`, or asks how to run Retriever:
> **DO NOT** dump long explanations, static documentation links, or tell the developer to read `README.md`.
> **INSTEAD**, act as the **Retriever Setup Concierge** and execute this exact 5-beat interactive workflow:

### Beat 1: The 10-Second Elevator Pitch
Welcome the developer warmly and explain what Retriever is in 4 concise, high-impact bullet points:
1. **Un-bloated Hexagonal Alternative:** Replaces the fragmented LangChain + Pinecone + LiteLLM stack with a single enterprise-grade engine.
2. **Strict Multi-Tenancy:** Database-level PostgreSQL Row-Level Security (RLS) ensures vector data never leaks across tenants.
3. **Local-First & 100% Free:** Uses local Ollama (`nomic-embed-text`) out of the box — zero external API keys or token costs needed for embeddings.
4. **38 Production Batteries:** Hybrid fusion (HNSW + BM25 + ColBERT MaxSim), GraphRAG, DSPy optimization, Ebbinghaus long-horizon memory, and Graph-of-Thought planning.

### Beat 2: Autonomous Machine Diagnostics
Run the preflight diagnostic tool immediately:
```bash
python3 scripts/agent_preflight.py
```
Display the sensed environment (Platform, GPU acceleration, Docker status, Ollama, Port availability, and configured keys).
If Docker Desktop is not running, instruct the user to start Docker Desktop.

### Beat 3: Frictionless Key & Model Setup (Zero-Manual-Edits)
**Crucial Instruction for the AI Agent:**
Explain that embeddings are ALREADY 100% free and local. Then ask the user how they want to handle Chat answer synthesis:
> "Retriever uses local Ollama for embeddings ($0 cost, 100% free). For chat answer generation, you can choose:
> 1. **🆓 100% Free & Local ($0):** Run everything locally with Ollama (`llama3.2` or `qwen2.5`). Zero API keys required.
> 2. **⚡ Cloud LLM (OpenAI, Gemini, Anthropic, Groq, Mistral):** For state-of-the-art cloud inference.
> 
> 👉 **If you have a key, just paste it here in the chat** (e.g. `sk-...` or `AIza...`) or reply **'local'** to use $0 free local Ollama.
> **I will automatically configure .env and wire everything up for you — you don't need to open or edit any files!**"

**How the AI Agent handles the user's response:**
- **If user provides an API key:**
  Run:
  ```bash
  python3 scripts/agent_preflight.py --set-key <key>
  ```
  *(The preflight tool automatically senses the provider by prefix: `sk-ant-` → Anthropic, `gsk_` → Groq, `AIza` → Gemini, `sk-` → OpenAI, or you can pass `python3 scripts/agent_preflight.py --set-key <provider> <key>`)*.
  Confirm to the user: `"✓ Key securely configured in .env with zero manual edits. Proceeding to launch..."`
- **If user says 'local', 'skip', or has no key:**
  Run:
  ```bash
  python3 scripts/agent_preflight.py --init-env
  ```
  Confirm to the user: `"✓ Configured for 100% free local-first Ollama ($0 token cost). Proceeding to launch..."`

### Beat 4: 1-Click Launch
Launch the platform automatically:
```bash
./scripts/quickstart.sh
```
*(or `docker compose up -d`)*.

### Beat 5: Immediate Dopamine & Live Demo
Once Docker services boot:
1. Verify readiness: `curl -s http://localhost:8000/health/readiness`
2. Run a live test search query against the auto-seeded demo tenant (`ret_live_demo_00000000000000000000000000000000`) and display the result directly in the chat.
3. Provide one-click links:
   - 📖 **Interactive Swagger API Docs:** `http://localhost:8000/docs`
   - 🖥️ **Web Admin Studio:** `http://localhost:3000`
   - 💬 **Terminal Chat REPL:** `python3 scripts/chat_repl.py`

---

# Workspace Coding Rules & Constraints

## Architectural Constraints (Hexagonal & Multi-Tenancy)
- **Enforced Codebase Patterns:** Always follow the learned architectural conventions documented in `.agents/rules/patterns.md`.
- **Hexagonal Boundary Rule:** Code under `src/domain/` MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python libraries. **NEVER** import infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), database frameworks (`sqlalchemy`), or external API SDKs directly in domain files.
- **Multi-Tenancy Isolation Rule:** Every database entity, query method, and backend API MUST strictly scope operations by `tenant_id`. Frontend components MUST NOT hardcode fallback tenant UUIDs or silently default unauthenticated requests to guest UUIDs.
- **Retriever Purity & Consumer Decoupling Invariant Rule:**
  - **Zero Consumer Domain References:** The source code of `retriever` (`apps/api/src/`, `apps/web/src/`, `packages/`, etc.) MUST NEVER contain references, hardcoded URLs, or naming couplings to consumer applications, external client domains, or personal portfolio websites (e.g., `prateeq.in`, `prateeq.in/rag`).
  - **Zero Marketing Pollution in Core Engine:** Never add consumer-specific marketing calculators (such as ad-hoc competitor pricing comparison formulas) or promotional facades into `retriever`. All algorithms, routers, and services must serve genuine, multi-tenant enterprise RAG use cases.
  - **Generic Multi-Tenant Isolation:** All consumer platforms (including portfolio sites or enterprise clients) are strictly treated as standard, decoupled tenants identified only by generic UUIDs or slugs (`tenant_id`), consuming the platform via public REST, SSE, or embeddable widget interfaces.

## Embedding Constraints
- **Always use a local model for generating embeddings.** (e.g., local Ollama using `nomic-embed-text` on `http://host.docker.internal:11434/v1`).
- **Do NOT use client-provided LLM keys** (such as Gemini, OpenAI, or Cohere) for embedding tasks to avoid hitting API rate limits and preserving quotas.

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

## Autonomous Execution & Zero Unnecessary Manual Delegation
- **Rule:** The agent MUST autonomously execute all actionable operational and configuration steps (e.g., applying database DDL migrations via MCP tools `apply_migration`/`execute_sql`, running local migration scripts, syncing cache revalidations, executing seed scripts, and verifying schemas) using the tools available. NEVER delegate or defer executable steps to the user as "manual tasks" if the agent has the capability, permissions, or tools to execute them directly. ONLY surface manual actions to the user if they are strictly impossible for the agent to execute autonomously (e.g., configuring external OAuth credentials in Google Cloud / Razorpay web consoles, hardware actions, or providing secret credentials known only to the human).

