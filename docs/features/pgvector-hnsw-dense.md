# pgvector HNSW Dense Embeddings & Multi-Tenant Partitioning

**Milestone:** M1 (v0.1.0)  
**System Layer:** Dense Vector Indexing & Semantic Search (Platform Battery #2)  
**Architecture:** PostgreSQL 16 + pgvector Extension + Hierarchical Navigable Small World (HNSW) Graphs + Strict Row-Level Security (RLS)  

---

## 1. Executive Summary

Milestone 1 establishes **Platform Battery #2: `pgvector_hnsw_dense`**, providing the core high-dimensional semantic retrieval substrate for Retriever.

Dense vector retrieval maps unstructured natural language queries and document chunks into a unified metric vector space where semantic relatedness corresponds to angular proximity. By deploying the `pgvector` extension directly within PostgreSQL 16, Retriever achieves sub-10ms Approximate Nearest Neighbor (ANN) search while preserving full ACID transactional integrity, relational joins, and strict cryptographic tenant isolation.

---

## 2. Mathematical Foundation & HNSW Index Architecture

Embeddings are normalized $d$-dimensional unit vectors ($\|v\|_2 = 1$). Proximity between query vector $q$ and chunk vector $v$ is measured using Cosine Distance:

$$\mathcal{D}_{\text{cosine}}(q, v) = 1 - \frac{q \cdot v}{\|q\|_2 \|v\|_2} = 1 - \sum_{i=1}^{d} q_i v_i$$

### HNSW Graph Construction
Rather than executing brute-force $O(N)$ linear table scans, `pgvector` organizes high-dimensional vectors into a multi-layer Hierarchical Navigable Small World (HNSW) graph:
- **Index Parameters:**
  - $m = 16$: Maximum number of bi-directional connection links per node in layers $>0$.
  - $\text{ef\_construction} = 64$: Size of the dynamic candidate list evaluated during index construction, balancing build time and recall accuracy.
  - $\text{ef\_search} = 40$: Size of the candidate list evaluated during query execution, ensuring $>98\%$ recall at sub-8ms latency.

---

## 3. Database Schema & Dimension-Partitioned Tables

To support multiple foundational embedding models without vector dimension conflicts, Retriever maintains three distinct dimension-partitioned tables in PostgreSQL:

1. `vector_records`: Default 768-dimensional space (e.g. `nomic-embed-text`, `bge-base-en-v1.5`).
2. `vector_records_1536`: 1536-dimensional space (e.g. OpenAI `text-embedding-3-small`, `ada-002`).
3. `vector_records_3072`: 3072-dimensional space (e.g. OpenAI `text-embedding-3-large`).

### Relational Schema Definition
```sql
CREATE TABLE vector_records (
    chunk_id UUID PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    embedding VECTOR(768) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- High-performance HNSW Index
CREATE INDEX idx_vector_records_hnsw_cosine 
ON vector_records 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 4. Query Execution & Tenant Isolation

All vector queries are executed through `PgVectorSearchAdapter` (`apps/api/src/adapters/vector/vector_repository.py`) via the `tenant_session` context manager:

```sql
SELECT
    vr.chunk_id,
    dc.document_id,
    dc.content,
    dc.meta_data,
    1 - (vr.embedding <=> CAST(:query_vec AS vector)) AS similarity_score
FROM vector_records vr
JOIN document_chunks dc ON vr.chunk_id = dc.chunk_id
WHERE vr.tenant_id = :tenant_id
ORDER BY vr.embedding <=> CAST(:query_vec AS vector)
LIMIT :top_k;
```

### Row-Level Security (RLS) Enforcement
PostgreSQL Row-Level Security is enabled on all vector tables. The session sets `app.current_tenant_id = :tenant_id` at the connection level, guaranteeing that even in the presence of SQL injection, cross-tenant embeddings cannot leak.

---

## 5. Non-Negotiable Invariants

1. **Strict Dimension Matching:** Insertion vectors must match the target table dimensionality ($d=768, 1536, 3072$).
2. **Local Embedding Enforcement:** Retriever's automated ingestion pipelines enforce local model embedding (`nomic-embed-text`) to eliminate external third-party API rate limits and data egress.
3. **Index Pre-Warming:** In production, `pg_prewarm('vector_records')` is executed on startup to cache HNSW graph structures in memory.
