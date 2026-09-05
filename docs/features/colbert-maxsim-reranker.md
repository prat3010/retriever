# ColBERT MaxSim Late-Interaction Token-Level Reranker

**Milestone:** M80 (v0.65.0)  
**System Layer:** Deep Contextual Reranking & Multi-Vector Late Interaction (Platform Battery #3)  
**Architecture:** PyTorch / HuggingFace Token Encoders + Token-Level Multi-Vector Projections + MaxSim Matrix Aggregator + Latency Optimization  

---

## 1. Executive Summary

Milestone 80 establishes **Platform Battery #3: `colbert_maxsim_reranker`**, providing fine-grained token-level late-interaction reranking in Retriever's cognitive pipeline.

Traditional single-vector dense retrieval compresses an entire 500-token document chunk into a single fixed-length embedding vector (e.g. 768 floats). This lossy pooling operation causes "semantic dilution," where subtle clauses, specific conditions, and critical negations are averaged away. Cross-encoders solve this but are computationally prohibitive, running full self-attention across the concatenated query and document for every candidate ($O(K \cdot (L_q + L_d)^2)$).

ColBERT (Contextualized Late Interaction over BERT) bridges this divide:
1. **Multi-Vector Representations:** Every token in the query and document receives its own low-dimensional embedding vector (e.g. $d=128$).
2. **Late Interaction via MaxSim:** Evaluates relevance by finding the maximum dot-product similarity for each query token across all document tokens, then summing these maxima.
3. **Sub-15ms Latency:** Avoids quadratic cross-attention during retrieval, computing relevance via optimized matrix multiplication on pre-encoded or lightweight token matrices.

---

## 2. Mathematical Foundation & MaxSim Operator

Given a query representation matrix $Q \in \mathbb{R}^{|Q| \times d}$ and a document candidate representation matrix $D \in \mathbb{R}^{|D| \times d}$ where individual token vectors are $L_2$-normalized:

$$\text{MaxSim}(Q, D) = \sum_{i=1}^{|Q|} \max_{j=1}^{|D|} \left( Q_i \cdot D_j^\top \right)$$

```text
       Query Tokens (Q)
         [q1, q2, q3]
              │
              ▼  (Matrix Dot Product)
     ┌──────────────────┐
     │  q1·d1  q1·d2... │ ──► max across doc tokens ──► max_1
     │  q2·d1  q2·d2... │ ──► max across doc tokens ──► max_2  ──► SUM = Final Score
     │  q3·d1  q3·d2... │ ──► max across doc tokens ──► max_3
     └──────────────────┘
       Document Tokens (D)
```

Each query token soft-aligns to the single most relevant token in the document. This preserves exact token matching semantics (like BM25) while maintaining deep contextual awareness (like BERT).

---

## 3. System Architecture & Two-Stage Cascade

In Retriever, the ColBERT MaxSim reranker operates as the second stage in a two-tier retrieval cascade:

```text
  [ User Query ]
        │
        ▼
  [ Stage 1: Fast ANN Candidate Generation (<10ms) ]
  - pgvector HNSW dense search + BM25 sparse search
  - Returns Top-50 candidate document chunks
        │
        ▼
  [ Stage 2: ColBERT Token-Level MaxSim Reranking (~14ms) ]
  - Tokenizes top candidates and computes token embeddings
  - Executes batch PyTorch MaxSim tensor contraction
  - Re-orders candidates with fine-grained contextual scores
        │
        ▼
  [ Top-5 High-Fidelity Chunks Passed to LLM Context ]
```

---

## 4. Implementation Details

- **Adapters:** `apps/api/src/adapters/cognitive/local_reranker_adapter.py` and `tei_reranker_adapter.py`
- **Supported Backends:** Local PyTorch CUDA/MPS runtime or remote Text Embeddings Inference (TEI) microservice.
- **Precision:** FP32 or FP16 tensor acceleration.
- **Candidate Pool Size:** Evaluates top 50 candidates from Stage 1.
- **Health Check Endpoint:** `GET /v1/search/rerank`

---

## 5. Non-Negotiable Invariants

1. **Normalized Embeddings:** All token vectors must be $L_2$-normalized prior to matrix multiplication so dot products correspond strictly to cosine similarities $[-1.0, 1.0]$.
2. **Punctuation Masking:** Query punctuation tokens (e.g. `?`, `!`, `,`) are masked out during MaxSim aggregation to prevent irrelevant syntax from dominating semantic alignment scores.
3. **Hard Latency Timeout:** Reranking carries a strict 45ms timeout; if exceeded, the pipeline gracefully falls back to Stage 1 RRF candidate rankings without failing the user request.
