# GitHub Copilot Instructions for Retriever

## 🤖 1-Word AI Onboarding: "Setup"
If the developer asks to set up, initialize, or run Retriever (or types `Setup`):
DO NOT dump lengthy manual instructions or reference long documentation pages.
Execute the 4-Beat Retriever Setup Concierge:

1. **Beat 1: Welcome & Pitch**
   Explain Retriever's value proposition:
   - Enterprise cognitive RAG engine replacing LangChain + Pinecone + LiteLLM.
   - Strict database-level PostgreSQL RLS multi-tenancy.
   - Zero API costs with local Ollama (`nomic-embed-text`) embeddings.
   - 38 production cognitive batteries (GraphRAG, DSPy, ColBERT MaxSim, Graph-of-Thought).

2. **Beat 2: Preflight Diagnostic**
   Execute:
   ```bash
   python3 scripts/agent_preflight.py
   ```
   Show host hardware, Docker status, Ollama status, and port availability.

3. **Beat 3: Path Selection**
   Offer 3 paths:
   - 1-Click Docker Launch (`./scripts/quickstart.sh` or `docker compose up -d`)
   - Configure MCP tools (`packages/retriever-mcp`)
   - Core Python Dev Setup (`pip install -r requirements.txt`)

4. **Beat 4: Live Verification & Dopamine**
   Verify `http://localhost:8000/health/readiness`, run a sample query against the demo workspace, and link to Swagger Docs (`http://localhost:8000/docs`) and Web Studio (`http://localhost:3000`).

## Architecture Conventions
- Respect Hexagonal Architecture: domain layer in `src/domain/` has zero external dependencies.
- Multi-tenancy isolation by `tenant_id` is mandatory everywhere.
- Run `ruff check --fix` and `python3 scripts/audit_zero_toy.py` to ensure code compliance.
