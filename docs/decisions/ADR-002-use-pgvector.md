# ADR-002: Use pgvector as Primary Vector Search and Storage

## Status
Accepted

## Context
Retriever requires storing and searching millions of high-dimensional vector embeddings generated for document text chunks. These vector indexes must be queried alongside metadata filters (e.g. `tenant_id`, `tags`, `created_at`) under strict latency budgets (search < 150ms).

## Problem
Selecting a vector database requires balancing operational complexity, cost, consistency, and search latency. 
Separating relational data from vectors introduces transaction boundaries and consistency issues:
1. Deleting a document requires removing metadata from a SQL DB and deleting vectors from a separate vector store.
2. Interrupted writes leave orphan vectors, corrupting similarity searches.
3. Hybrid query execution requires querying two distinct databases and merging results, adding latency.

## Decision
Utilize the **pgvector** extension inside PostgreSQL as the primary vector search database.

## Alternatives Considered
* **Dedicated Vector Databases (Qdrant, Milvus, Pinecone):** These offer excellent search latencies and advanced partitioning features, but introduce the "two-database problem" (syncing state and credentials, higher cost, and network latency during hybrid retrieval joins).
* **Elasticsearch / Opensearch:** Provides both full-text search and vector search capabilities, but increases operational overhead and memory resource costs compared to running pgvector in our primary PostgreSQL instance.

## Consequences
* **Transactional Consistency:** Relational metadata updates and vector inserts occur in a single ACID transaction block. If chunking fails, vector records are rolled back automatically.
* **Multi-Dimension Partitioning (`vector_records_1024`, `vector_records_1536`, `vector_records_3072`):** Rather than locking the platform to a single embedding dimension, Retriever uses dimension-partitioned vector tables (`vector_records` for 768d, `vector_records_1024` for BGE-M3 / Snowflake, `vector_records_1536` for OpenAI small, `vector_records_3072` for OpenAI large). Each table has its own dedicated HNSW cosine index and RLS policy, enabling concurrent multi-model support on a single PostgreSQL instance.
* **Simplified Hybrid Retrieval:** Vectors are stored as a column (`vector` type) on the corresponding partitioned table, allowing hybrid queries (vector similarity search + BM25 keyword matching) to be executed in a single query path with metadata filters.
* **RLS Integration:** Row-Level Security policies automatically apply to vector queries via the `tenant_id` context across all partitioned vector tables.
* **Index Configuration:** Requires configuring HNSW (Hierarchical Navigable Small World) indexes (`m = 16, ef_construction = 200`) on PostgreSQL columns to ensure low-latency retrieval.
* **Memory Limits:** The PostgreSQL host must allocate sufficient RAM to cache HNSW indexes to prevent slow disk reads.

## Future Review Criteria
* Re-evaluate pgvector performance under extreme scale (>10M vectors per dimension table).
* Monitor index build latency. If HNSW index rebuilding delays ingestion, consider routing enterprise tenants with massive datasets to isolated Qdrant clusters.
