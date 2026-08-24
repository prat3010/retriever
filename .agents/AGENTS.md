# Workspace Coding Rules & Constraints

## Architectural Constraints (Hexagonal & Multi-Tenancy)
- **Enforced Codebase Patterns:** Always follow the learned architectural conventions documented in `.agents/rules/patterns.md`.
- **Hexagonal Boundary Rule:** Code under `src/domain/` MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python libraries. **NEVER** import infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), database frameworks (`sqlalchemy`), or external API SDKs directly in domain files.
- **Multi-Tenancy Isolation Rule:** Every database entity, query method, and backend API MUST strictly scope operations by `tenant_id`. Frontend components MUST NOT hardcode fallback tenant UUIDs or silently default unauthenticated requests to guest UUIDs.

## Embedding Constraints
- **Always use a local model for generating embeddings.** (e.g., local Ollama using `nomic-embed-text` on `http://host.docker.internal:11434/v1`).
- **Do NOT use client-provided LLM keys** (such as Gemini, OpenAI, or Cohere) for embedding tasks to avoid hitting API rate limits and preserving quotas.

## Code Style & Formatting Rules
- **Always run `ruff check --fix` on modified Python files** before making commits or finishing tasks to ensure imports and formatting conform to project CI standards.

## Agent Architecture Pre-Flight & Graph Intelligence
- **Architecture Knowledge Graph Pre-Flight:** Before creating, editing, or modifying ANY database table, API route router, domain service, or infrastructure adapter, the agent MUST run:
  ```bash
  python3 scripts/query_architecture.py --target <entity_or_api>
  ```
  to inspect the full blast radius, upstream callers, downstream dependencies, and linked PRDs.
- **Mandatory Documentation & Markdown Audit:** Whenever ANY code change is executed (even minor bug fixes, parameter tweaks, or refactors), the agent MUST check and update all relevant project documentation (`ROADMAP.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`, `docs/`, etc.) to ensure roadmap statuses, feature lists, API specifications, and architecture descriptions stay 100% synchronized with the codebase before completing the task.

