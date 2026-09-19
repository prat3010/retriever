# GitHub Copilot Instructions for Retriever

## 🤖 1-Word AI Onboarding: "Setup"
If the developer asks to set up, initialize, or run Retriever (or types `Setup`):
DO NOT dump lengthy manual instructions or reference long documentation pages.
Execute the 5-Beat Retriever Setup Concierge:

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
   Show host hardware, Docker status, Ollama status, port availability, and configured keys.

3. **Beat 3: Frictionless Key & Model Setup (Zero-Manual-Edits)**
   Ask the user:
   > "Retriever uses local Ollama for embeddings ($0 cost, 100% free). For chat answer generation, you can choose:
   > 1. **🆓 100% Free & Local ($0):** Run locally with Ollama (`llama3.2` or `qwen2.5`). Zero API keys required.
   > 2. **⚡ Cloud LLM (OpenAI, Gemini, Anthropic, Groq, Mistral):** For state-of-the-art cloud inference.
   >
   > 👉 **If you have a key, just paste it here in the chat** or reply **'local'** for $0 local Ollama.
   > **I will automatically configure .env and wire everything up for you — zero manual file editing needed!**"

   - If user provides key: Run `python3 scripts/agent_preflight.py --set-key <key>`
   - If user says 'local' or skips: Run `python3 scripts/agent_preflight.py --init-env`

4. **Beat 4: 1-Click Launch**
   Execute:
   ```bash
   ./scripts/quickstart.sh
   ```
   *(or `docker compose up -d`)*

5. **Beat 5: Live Verification & Dopamine**
   Verify `http://localhost:8000/health/readiness`, run a sample test query against the demo workspace, and link to Swagger Docs (`http://localhost:8000/docs`), Web Studio (`http://localhost:3000`), and Chat REPL (`python3 scripts/chat_repl.py`).

## Architecture Conventions
- Respect Hexagonal Architecture: domain layer in `src/domain/` has zero external dependencies.
- Multi-tenancy isolation by `tenant_id` is mandatory everywhere.
- Run `ruff check --fix` and `python3 scripts/audit_zero_toy.py` to ensure code compliance.
