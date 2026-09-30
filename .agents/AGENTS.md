# 🤖 Agent-Native Interactive Onboarding Directive: "Setup"

> **TRIGGER:** If the user sends `Setup`, `setup`, `init`, `start`, `Help me get started`, or asks how to run Retriever:
> **DO NOT** dump long explanations, static documentation links, or tell the developer to read `README.md`.
> **INSTEAD**, act as the **Retriever Setup Concierge** and execute this exact 5-beat interactive workflow:

### Beat 1: The 10-Second Elevator Pitch
Welcome the developer warmly and explain what Retriever is in 4 concise, high-impact bullet points:
1. **Un-bloated Hexagonal Alternative:** Replaces the fragmented LangChain + Pinecone + LiteLLM stack with a single enterprise-grade engine.
2. **Strict Multi-Tenancy:** Database-level PostgreSQL Row-Level Security (RLS) ensures vector data never leaks across tenants.
3. **Local-First & 100% Free:** Uses local Ollama (`nomic-embed-text`) out of the box — zero external API keys or token costs needed for embeddings.
4. **Core Production Subsystems:** Hybrid fusion (HNSW + BM25 + ColBERT MaxSim), layout-aware OCR, and PostgreSQL Row-Level Security.

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
- **Hexagonal Boundary Rule:** Code under `src/domain/` MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python libraries. **NEVER** import infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), database frameworks (`sqlalchemy`), or external API SDKs directly in domain files.
- **Multi-Tenancy Isolation Rule:** Every database entity, query method, and backend API MUST strictly scope operations by `tenant_id` using PostgreSQL Row-Level Security (RLS).
- **Decoupled Engine Core:** The core engine of `retriever` must remain standalone and generic. Never hardcode consumer domain URLs or marketing formulas into the backend.

## Embedding & LLM Constraints
- **Local-First Embeddings:** Always default to local Ollama (`nomic-embed-text`) for generating embeddings to avoid external token costs and rate limits.
- **Configurable LLM Inference:** Chat completion supports local Ollama or cloud providers (OpenAI, Gemini, Groq, Anthropic) configured via environment variables.

## Code Quality & Testing
- **Formatting:** Always run `ruff check --fix` on modified Python files before finishing tasks.
- **Test Verification:** Ensure `pytest apps/api/tests/` passes without regressions.
- **Pragmatic Simplicity:** Prioritize core platform reliability, clean boundaries, and genuine functionality over speculative layers or simulated features.
