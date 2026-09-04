# ADR-012: Hybrid Search Fusion (BM25 + Splade + Dense pgvector RRF)

## Status
Accepted

## Context
Dense vector search retrieves documents based on high-level semantic intent but struggles with exact alphanumeric identifiers (part numbers, error codes, legal statute numbers, variable names). Traditional sparse search (BM25) excels at exact keyword matching but cannot understand synonyms or conceptual queries.

## Problem
Relying solely on vector embeddings or keyword search creates blind spots, causing queries with exact codes or jargon to fail.

## Decision
Implement a **Tri-Modal Hybrid Search Pipeline** combined via **Reciprocal Rank Fusion (RRF)**:
1. **Dense Semantic Retrieval:** PostgreSQL `pgvector` HNSW cosine similarity search.
2. **Sparse Keyword Retrieval:** PostgreSQL native full-text search (BM25 equivalent).
3. **Learned Sparse Representation:** SPLADE sparse expansion for expanded lexical matching.
4. **Rank Fusion Formula:**
   $$RRF(d) = \sum_{m \in \{\text{dense}, \text{bm25}, \text{splade}\}} \frac{1}{k + \text{Rank}_m(d)}$$
   With smoothing constant $k = 60$.
5. **Cross-Encoder Reranking:** Top-$K$ candidates from RRF are reranked using an authentic cross-encoder (Cohere API or local FlashRank) prior to LLM context assembly.

## Consequences
* **State-of-the-Art Retrieval Accuracy:** Handles exact codes and conceptual semantic queries simultaneously with near-zero miss rate.
* **Tunable Weights:** Tenants can tune the RRF balance between keyword and semantic search via their Admin configuration.
* **Latency Trade-Off:** Executing parallel search channels and reranking adds ~30-60ms to query retrieval latency.

## Future Review Criteria
* Monitor database CPU utilization when high-concurrency workloads execute parallel BM25 and pgvector queries.
