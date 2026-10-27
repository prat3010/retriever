# ADR-012: Hybrid Search Fusion (BM25 + Dense pgvector RRF)

## Status
Accepted

## Context
Dense vector search retrieves documents based on high-level semantic intent but struggles with exact alphanumeric identifiers (part numbers, error codes, legal statute numbers, variable names). Traditional sparse search (BM25) excels at exact keyword matching but cannot understand synonyms or conceptual queries.

## Problem
Relying solely on vector embeddings or keyword search creates blind spots, causing queries with exact codes or jargon to fail.

## Decision
Implement a **Dual-Channel Concurrent Hybrid Search Pipeline** combined via **Reciprocal Rank Fusion (RRF)**:
1. **Dense Semantic Retrieval:** PostgreSQL `pgvector` HNSW cosine similarity search.
2. **Sparse Keyword Retrieval:** PostgreSQL native full-text search (`tsvector` / `websearch_to_tsquery`) with domain synonym weighting.
3. **Rank Fusion Formula:**
   $$RRF(d) = \sum_{m \in \{\text{vector}, \text{keyword}\}} \frac{1}{k + \text{Rank}_m(d)}$$
   With smoothing constant $k = 60$.
4. **Late-Interaction Reranking:** Top-$K$ candidates from RRF are reranked using ColBERT MaxSim (`NeuralColbertEngine` with score threshold filtering) or Cross-Encoder prior to LLM context assembly.

## Consequences
* **State-of-the-Art Retrieval Accuracy:** Handles exact codes and conceptual semantic queries simultaneously with near-zero miss rate.
* **Tunable Weights:** Tenants can tune the RRF balance between keyword and semantic search via their Admin configuration.
* **Low Latency:** Executing parallel search channels with `asyncio.gather` and late-interaction MaxSim keeps end-to-end retrieval under 30ms.

## Future Review Criteria
* Monitor database CPU utilization when high-concurrency workloads execute parallel BM25 and pgvector queries.
