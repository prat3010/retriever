# Workspace Coding Rules & Constraints

## Embedding Constraints
- **Always use a local model for generating embeddings.** (e.g., local Ollama using `nomic-embed-text` on `http://host.docker.internal:11434/v1`).
- **Do NOT use client-provided LLM keys** (such as Gemini, OpenAI, or Cohere) for embedding tasks to avoid hitting API rate limits and preserving quotas.
