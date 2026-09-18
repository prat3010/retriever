# Claude Code Instructions for Retriever

## 🤖 1-Word AI Onboarding: "Setup"
When the user types `Setup`, `setup`, `init`, `start`, or asks how to get started:
DO NOT output long markdown explanations or tell the user to read README.md.
Follow this 4-beat interactive concierge flow:

1. **Welcome & Pitch:** Explain Retriever (enterprise RAG engine replacing LangChain/Pinecone, Postgres RLS multi-tenancy, free local Ollama embeddings, 38 batteries).
2. **Run Preflight Diagnostic:**
   ```bash
   python3 scripts/agent_preflight.py
   ```
   Report findings (Docker, GPU, ports, Ollama). If Docker Desktop is not running, guide the user to launch it.
3. **Intent Selection:** Offer:
   - Option 1: 1-Click Docker Launch (`./scripts/quickstart.sh`)
   - Option 2: MCP Server Configuration (`packages/retriever-mcp`)
   - Option 3: Python Developer Environment (`pip install -r requirements.txt`)
4. **Live Verification:** Poll `http://localhost:8000/health/readiness`, execute a test query, and provide URLs for Swagger Docs (`http://localhost:8000/docs`) and Web Studio (`http://localhost:3000`).

## Architecture & Code Guidelines
- **Hexagonal Boundaries:** `src/domain/` must NEVER import from `src/adapters/`, `src/routers/`, or third-party database libraries.
- **Multi-Tenancy:** All queries must include `tenant_id`.
- **Embeddings:** Strictly use local Ollama (`nomic-embed-text`) on `http://host.docker.internal:11434/v1`.
- **Quality Gates:** Before submitting changes, run `ruff check --fix` and `python3 scripts/audit_zero_toy.py`.
