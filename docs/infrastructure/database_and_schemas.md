---
id: DeepDive_Database_Schemas_pgvector
title: "Infrastructure Deep-Dive: PostgreSQL 16, pgvector HNSW Indexing & RLS Multi-Tenancy"
tier: 8_persistence
platform: retriever
tags:
  - infra/database
  - postgresql
  - pgvector
  - security/rls
  - platform/retriever
blast_radius: CRITICAL
security_auth: SERVICE_ROLE
invariants:
  - "PostgreSQL RLS MUST be enabled on all 24 multi-tenant tables."
  - "HNSW vector index MUST use cosine metric (vector_cosine_ops) with m=16, ef_construction=64."
---

# Infrastructure Deep-Dive: PostgreSQL 16, pgvector HNSW Indexing & RLS Multi-Tenancy

#infra #database #postgres #pgvector #hnsw #rls #multitenancy #retriever

> **Authoritative specification for database architecture, 24 relational tables, pgvector HNSW partitioning, Row-Level Security (RLS), and Alembic migrations.**

---

## 1. Relational Entity-Relationship Diagram

```mermaid
erDiagram
    TENANTS ||--o{ USERS : owns
    TENANTS ||--o{ DOCUMENTS : stores
    TENANTS ||--o{ CHAT_SESSIONS : hosts
    TENANTS ||--o{ API_KEYS : issues
    TENANTS ||--o{ INVOICES : bills
    
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : contains
    DOCUMENT_CHUNKS ||--o{ PGVECTOR_EMBEDDINGS : has
    DOCUMENT_CHUNKS ||--o{ GRAPH_TRIPLES : sources
    
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains
    CHAT_MESSAGES ||--o{ INFERENCE_LOGS : records
    CHAT_MESSAGES ||--o{ CHAT_FEEDBACK : receives
```

---

## 2. pgvector HNSW Index Configuration

```sql
-- Partitioned Vector Embeddings Table
CREATE TABLE IF NOT EXISTS pgvector_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    dimensions INT NOT NULL DEFAULT 768,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- High-Performance HNSW Cosine Distance Index
CREATE INDEX IF NOT EXISTS idx_pgvector_hnsw_cosine 
ON pgvector_embeddings 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

---

## 🔗 Related Architecture & Cross-References
- [Caching & Performance](caching_and_performance.md)
- [Storage & Zero-Trust Envelope Encryption](storage_and_encryption.md)
