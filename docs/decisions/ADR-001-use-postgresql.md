# ADR-001: Use PostgreSQL as Core Relational & Metadata Database

## Status
Accepted

## Context
The Retriever platform requires a highly structured, scalable, and secure data storage engine to manage tenant registries, document metadata, prompt templates, user chat sessions, and audit logging ledger logs. Data isolation is a critical security requirement, meaning we must enforce strict partitioning between customer bounds.

## Problem
We need a production-grade relational database engine that supports:
1. Strict schema structures with relational integrity constraints.
2. Advanced row-level security boundaries to enforce tenant isolation at the database level.
3. Extensibility to support vector indexing libraries (e.g. pgvector) to avoid operating separate metadata and vector databases.
4. Rich full-text search capabilities (BM25 keyword search) to execute parallel sparse search queries.
5. High-performance indexing and query scaling patterns (e.g., PgBouncer pooling, read replicas, and partitioning).

## Decision
Utilize **PostgreSQL (v15+)** as the unified platform relational database engine.

## Alternatives Considered
* **MySQL / MariaDB:** While highly scalable, MySQL lacks robust native Row-Level Security (RLS) policies equivalent to PostgreSQL's `USING` security filter models. In addition, its extension ecosystem for vector similarity search is less mature than PostgreSQL's `pgvector`.
* **NoSQL (MongoDB / DynamoDB):** Document databases lack strong relational constraints and ACID transactions, which are essential for maintaining correct document-chunk parent-child hierarchies and transaction logs. Security boundaries are also harder to audit compared to SQL RLS.
* **Separating Relational and Vector Databases (e.g., MySQL + Pinecone):** This introduces the "two-database problem" (syncing state and transaction coordinates across distinct network providers), which increases operational complexity and data consistency risks.

## Consequences
* **Single Store:** Vector data and relational data reside in the same PostgreSQL cluster (using the `pgvector` extension), resolving state synchronization issues.
* **Tenant Isolation:** Enforced at the database layer using PostgreSQL Row-Level Security (RLS) policies on all tenant tables.
* **ACID Transactions:** Document parsing, chunk decomposition, and indexing transactions occur atomically.
* **Tooling:** Leverages mature ecosystem components (e.g., SQLAlchemy/SQLModel for Python, PgBouncer for pooling, and standard backup/failover patterns).
* **Operational Constraint:** Requires database tuning (memory allocations, work_mem) to handle concurrent vector searches alongside transactional relational writes.

## Future Review Criteria
* Re-evaluate database performance if a single tenant exceeds 10,000,000 document chunks, assessing if partition limits degrade HNSW index build times.
* Review PostgreSQL connection pool saturation if concurrent client connections exceed PgBouncer capacities.
