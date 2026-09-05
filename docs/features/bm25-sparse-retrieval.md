# Sublinear BM25 Keyword Search & Inverted Term Index

**Milestone:** M12 (v0.12.0)  
**System Layer:** Hybrid Retrieval & Exact Keyword Matching (Platform Battery #1)  
**Architecture:** Okapi BM25 Scoring + RegEx Inverted Tokenizer + Sublinear Term Frequency Saturation + Reciprocal Rank Fusion (RRF) Integration  

---

## 1. Executive Summary

Milestone 12 establishes **Platform Battery #1: `bm25_sparse_retrieval`**, providing high-precision lexical and identifier retrieval alongside dense vector embeddings in Retriever's cognitive architecture.

While dense semantic vector embeddings excel at understanding broad conceptual queries and synonyms, they exhibit systemic blind spots with exact-token lookups:
- Precise source code symbols, function signatures, and method names (e.g. `tenant_session`, `PyObject_Call`).
- Error codes, stack trace identifiers, and UUIDs (e.g. `ORA-01033`, `550 5.7.1`).
- Domain-specific acronyms and part numbers with low corpus frequency.

Platform Battery #1 addresses these failure modes by deploying an in-process, sublinear Okapi BM25 engine operating directly over document chunks. Query terms are scored against candidate chunk frequencies, penalizing document length outliers while preventing frequent terms from saturating relevance scores. BM25 sparse results are fused with dense pgvector rankings using Reciprocal Rank Fusion ($k=60$) in `src/domain/retrieval/search_service.py`.

---

## 2. Mathematical Foundation & Scoring Model

The Okapi BM25 score of a document chunk $D$ against a tokenized query $Q = \{q_1, q_2, \dots, q_m\}$ is computed as:

$$\text{Score}(D, Q) = \sum_{i=1}^{m} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

Where:
- $f(q_i, D)$ is the raw term frequency of query token $q_i$ within document chunk $D$.
- $|D|$ is the length of document $D$ measured in token count.
- $\text{avgdl}$ is the average document length across all evaluated candidates.
- $k_1 = 1.5$ controls term frequency saturation non-linearity (higher values make the score scale more linearly with frequency).
- $b = 0.75$ controls the degree of document length normalization ($b=1$ scales completely by relative length; $b=0$ disables length penalty).

### Inverse Document Frequency (IDF) Formulation
To prevent rare terms from generating negative values in small collections, Retriever utilizes the Robertson-Spärck Jones smoothed IDF:

$$\text{IDF}(q_i) = \ln \left(1 + \frac{N - n(q_i) + 0.5}{n(q_i) + 0.5}\right)$$

Where $N$ is the total candidate document set size, and $n(q_i)$ is the document frequency of token $q_i$.

---

## 3. Component Architecture & Retrieval Flow

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   BM25 KEYWORD RETRIEVAL & RRF FUSION PIPELINE                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ User Search Query ]                                                                │
│            │                                                                           │
│            ├────────────────────────────────────────┬──────────────────────────────────┤
│            │ (Parallel Dispatch)                    │                                  │
│            ▼                                        ▼                                  │
│   ┌─────────────────────────────┐          ┌─────────────────────────────┐             │
│   │   PgVectorSearchAdapter     │          │    BM25 Tokenizer & Index   │             │
│   │   - Cosine HNSW ANN (<8ms)  │          │    - Regex Tokenization     │             │
│   │   - Top-50 Dense Candidates │          │    - Document Term Counter  │             │
│   └──────────────┬──────────────┘          └──────────────┬──────────────┘             │
│                  │                                        │                            │
│                  │                                        ▼                            │
│                  │                         ┌─────────────────────────────┐             │
│                  │                         │     bm25_rerank() Engine    │             │
│                  │                         │     - k1=1.5, b=0.75        │             │
│                  │                         │     - Top-50 Sparse Ranked  │             │
│                  │                         └──────────────┬──────────────┘             │
│                  │                                        │                            │
│                  └────────────────────┬───────────────────┘                            │
│                                       ▼                                                │
│                     ┌───────────────────────────────────┐                              │
│                     │ Reciprocal Rank Fusion (RRF k=60) │                              │
│                     │ Score = 1/(60 + r_dense) +        │                              │
│                     │         1/(60 + r_sparse)         │                              │
│                     └─────────────────┬─────────────────┘                              │
│                                       ▼                                                │
│                     ┌───────────────────────────────────┐                              │
│                     │ Merged Fused Candidate Output     │                              │
│                     │ (~3ms latency, high precision)    │                              │
│                     └───────────────────────────────────┘                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Details

- **Core Module:** `apps/api/src/domain/retrieval/bm25_reranker.py`
- **Orchestration Service:** `apps/api/src/domain/retrieval/search_service.py` (`HybridSearchService`)
- **Tokenizer:** Lowercase alphanumeric regex extraction (`[a-zA-Z0-9]+`), filtering terms shorter than 2 characters.
- **Latency Profile:** $\sim 3\text{ms}$ across candidate sets of 100 documents.
- **Memory Footprint:** In-process streaming Counters without heavyweight JVM or Elasticsearch daemon dependencies.

---

## 5. Non-Negotiable Invariants & Multi-Tenancy

1. **Strict Tenant Scoping:** BM25 candidates are filtered by `tenant_id` at the database query boundary prior to scoring.
2. **Zero Negative IDF:** The smoothed Robertson formulation guarantees $\text{IDF} \ge 0$, eliminating negative ranking inversions.
3. **Deterministic Fused Output:** When BM25 scores tie, results default to stable insertion order preserved by the relational Primary Key.
