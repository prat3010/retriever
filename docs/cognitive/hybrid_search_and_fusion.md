---
id: DeepDive_HybridSearch_Fusion
title: "Cognitive Deep-Dive: Hybrid Search, Reciprocal Rank Fusion & Reranking"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/search
  - cognitive/hybrid-search
  - cognitive/rrf
  - cognitive/hnsw
  - cognitive/bm25
  - platform/retriever
blast_radius: HIGH
invariants:
  - "RRF rank constant k MUST default to 60."
  - "Dense embeddings MUST use nomic-embed-text 768-dim vector embeddings."
  - "Cross-encoder score threshold MUST be configurable per tenant (default 0.45)."
---

# Cognitive Deep-Dive: Hybrid Search, Reciprocal Rank Fusion & Reranking

#cognitive #search #hybrid #rrf #hnsw #bm25 #splade #reranker #retriever

> **Technical architecture, mathematical formulation, and implementation of Retriever's two-stage hybrid retrieval engine.**

---

## 1. The Core Retrieval Problem

Pure dense vector search excels at conceptual similarity (synonyms, paraphrase, multilingual semantic alignment) but frequently stumbles on:
- Exact part numbers, serial codes, and variable names (e.g. `ERR_404_OOM`, `SKU-9921`).
- Rare acronyms, specialized legal citations, and proper nouns.

Conversely, pure lexical search (BM25) excels at exact keyword matching but completely misses semantic context and synonyms.

**Retriever solves this by combining both in parallel and fusing results with Reciprocal Rank Fusion (RRF) and Cross-Encoder Re-ranking.**

```mermaid
flowchart TD
    Q([User Search Query]) -->|Embedding Worker| DenseVec[768-dim Vector]
    Q -->|Lexical Parser| SparseTokens[tsquery Lexical Tokens]

    subgraph Parallel Stage 1: Retrieval
        DenseVec -->|HNSW Cosine Index| TopDense[Top 50 Dense Candidates]
        SparseTokens -->|tsvector GIN Index| TopSparse[Top 50 Sparse Candidates]
    end

    TopDense --> RRF[Reciprocal Rank Fusion k=60]
    TopSparse --> RRF

    subgraph Stage 2: Fusion & Neural Reranking
        RRF --> FusedCandidates[Top 20 Fused Candidates]
        FusedCandidates --> CrossEnc[Cross-Encoder Neural Attention]
        CrossEnc --> MMR[MMR Diversity Pruning λ=0.7]
    end

    MMR --> FinalContext([Top-K Context Chunks for LLM])
```

---

## 2. Mathematical Formulation

### 2.1 Reciprocal Rank Fusion (RRF)

Given a list of ranked candidate chunks from the dense vector search \(R_{\text{dense}}\) and the sparse lexical search \(R_{\text{sparse}}\), the composite score for chunk \(d\) is defined as:

\[
\text{RRF\_Score}(d) = \sum_{r \in \{R_{\text{dense}}, R_{\text{sparse}}\}} \frac{w_r}{k + \text{rank}_r(d)}
\]

Where:
- \(k\): Smoothing constant (default: `60`) to prevent high-ranking items from dominating the score.
- \(w_r\): Weight assigned to each retrieval leg (\(w_{\text{dense}} = 1.0\), \(w_{\text{sparse}} = 0.8\)).
- \(\text{rank}_r(d)\): 1-indexed position of document \(d\) in candidate list \(r\).

---

### 2.2 Cross-Encoder Reranking

The top candidates from the RRF stage are passed to a Cross-Encoder model (e.g., `BAAI/bge-reranker-v2-m3`). Unlike bi-encoders which compute embeddings independently:

\[
\text{Score}_{\text{cross}} = \text{Softmax}(\text{Transformer}(\text{Query} \oplus \text{Chunk Content}))
\]

The Cross-Encoder performs full all-to-all cross-attention between every token in the query and every token in the candidate passage, eliminating false positives. Chunks with \(\text{Score}_{\text{cross}} < \text{reranking\_threshold}\) (default: `0.45`) are pruned.

---

### 2.3 Maximum Marginal Relevance (MMR)

To eliminate repetitive chunks from the same document section, MMR diversity sampling balances relevance against novelty:

\[
\text{MMR} = \operatorname{argmax}_{d_i \in D \setminus S} \left[ \lambda \operatorname{Sim}_1(d_i, Q) - (1 - \lambda) \max_{d_j \in S} \operatorname{Sim}_2(d_i, d_j) \right]
\]

Where \(\lambda = 0.7\) balances high relevance with topical diversity.

---

## 3. Physical Source Code Mapping

| Component | Source File Path | Role |
|:---|:---|:---|
| **Hybrid Search Service** | `src/domain/services/hybrid_search_service.py` | Orchestrates parallel retrieval, weights, and fusion |
| **pgvector HNSW Store** | `src/adapters/vector_store/pgvector_adapter.py` | Executes Cosine HNSW vector queries |
| **BM25 Lexical Store** | `src/adapters/lexical_store/postgres_bm25_adapter.py` | Executes PostgreSQL full-text search with `ts_rank_cd` |
| **Cross-Encoder Reranker** | `src/domain/services/reranking_service.py` | Computes transformer cross-attention rerank scores |

---

## 4. Latency & Performance Benchmarks

| Retrieval Strategy | P50 Latency | P95 Latency | Recall@5 | MRR@10 |
|:---|:---:|:---:|:---:|:---:|
| Pure Dense (pgvector HNSW) | 12ms | 24ms | 0.81 | 0.76 |
| Pure Sparse (Postgres BM25) | 8ms | 18ms | 0.74 | 0.69 |
| **Hybrid Search (Dense + BM25 + RRF)** | **18ms** | **34ms** | **0.91** | **0.87** |
| **Hybrid + Cross-Encoder Reranking** | **42ms** | **68ms** | **0.96** | **0.93** |

---

## 🔗 Related Architecture & Cross-References
- [Search API Specification](../api/search.md)
- [Query Intelligence & Intent](query_intelligence.md)
- [Database Schema & Vector Partitions](../infrastructure/database_and_schemas.md)
- [TypeScript Client SDK](../integrations/typescript_sdk.md)
