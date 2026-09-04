# ADR-009: Local-First Embedding Model Strategy (nomic-embed-text)

## Status
Accepted

## Context
Embedding generation is an essential, high-volume prerequisite for document ingestion, chunking, and vector search. Early prototypes relied on third-party cloud APIs (such as OpenAI `text-embedding-3-small` or Cohere `embed-english-v3.0`). In multi-tenant environments, relying on client-supplied LLM keys or external cloud APIs introduces rate limits (HTTP 429), significant recurring costs, and severe data egress concerns for enterprise documents.

## Problem
We need an embedding infrastructure that:
1. Operates with zero per-token cost on high-volume document ingestion.
2. Eliminates upstream API rate limiting and token quota depletion.
3. Protects sensitive tenant documents by keeping vector generation strictly on local hardware (VPS or developer machine).
4. Produces state-of-the-art semantic retrieval performance on MTEB benchmarks.

## Decision
Mandate **`nomic-embed-text` running locally via Ollama** (`768`-dimensional dense embeddings) as the primary platform embedding standard:
1. For server workloads: Runs on the Oracle Cloud VPS hardware via local Ollama instance (`http://localhost:11434`).
2. For local developer workloads: Runs on developer machines via Apple Silicon Metal acceleration.
3. **Strict Invariant:** External commercial LLM keys (Gemini, OpenAI, Anthropic) are strictly forbidden from being used for vector embedding generation.

## Consequences
* **Zero Marginal Cost:** Ingesting 100,000 document chunks incurs $0.00 in cloud embedding fees.
* **Resilience:** Ingestion pipelines never fail due to external API outages or rate limit exhausts.
* **Privacy:** Document chunk bytes never leave the local environment during vectorization.
* **Operational Constraint:** Requires ensuring the local Ollama daemon is running with sufficient host memory allocation (~600MB VRAM/RAM for `nomic-embed-text`).

## Future Review Criteria
* Evaluate if higher parameter open-source embedding models (e.g. `bge-m3` or `gte-Qwen2-7B-instruct`) should be adopted when VPS RAM is upgraded.
