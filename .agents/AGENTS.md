# Workspace Coding Rules & Constraints

## Architectural Constraints (Hexagonal & Multi-Tenancy)
- **Hexagonal Boundary Rule:** Code under `src/domain/` MUST ONLY import abstract interfaces from `src/domain/abstractions/` or standard Python libraries. **NEVER** import infrastructure adapters (`src/adapters/`), API routers (`src/routers/`), database frameworks (`sqlalchemy`), or external API SDKs directly in domain files.
- **Multi-Tenancy Isolation Rule:** Every database entity, query method, and backend API MUST strictly scope operations by `tenant_id`. Frontend components MUST NOT hardcode fallback tenant UUIDs or silently default unauthenticated requests to guest UUIDs.

## Embedding Constraints
- **Always use a local model for generating embeddings.** (e.g., local Ollama using `nomic-embed-text` on `http://host.docker.internal:11434/v1`).
- **Do NOT use client-provided LLM keys** (such as Gemini, OpenAI, or Cohere) for embedding tasks to avoid hitting API rate limits and preserving quotas.

## Code Style & Formatting Rules
- **Always run `ruff check --fix` on modified Python files** before making commits or finishing tasks to ensure imports and formatting conform to project CI standards.
