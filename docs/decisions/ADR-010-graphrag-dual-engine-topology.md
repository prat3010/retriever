# ADR-010: GraphRAG Dual-Engine Topology (Neo4j Cypher & PostgreSQL Fallback)

## Status
Accepted

## Context
Dense vector search excels at matching semantic intent but struggles with multi-hop associative queries (e.g., *"Which suppliers of Company X are subject to European sanction regulations?"*). GraphRAG addresses this by extracting knowledge graph triples `(subject, predicate, object)` and executing multi-hop graph traversals.

## Problem
Operating a dedicated graph database like Neo4j Aura introduces external cloud dependencies and recurring operational overhead, which may not be feasible or desired for lean self-hosted VPS deployments.

## Decision
Implement a **Dual-Engine GraphRAG Architecture**:
1. **Primary Enterprise Engine:** `Neo4jGraphRepository` executing authentic Cypher multi-hop queries (`MATCH (a)-[r]->(b) ...`) when Neo4j credentials are provided.
2. **Lean Self-Hosted Engine:** `PgGraphRepository` executing recursive Common Table Expressions (CTEs) on a relational `graph_triples` table in PostgreSQL with pgvector entity embeddings.
3. Both adapters implement the identical `GraphRepositoryProtocol` interface, enabling zero-downtime switching via configuration.

## Consequences
* **Deployment Flexibility:** Users can run high-scale Neo4j clusters or lightweight PostgreSQL-only graphs with zero code changes.
* **Unified Domain Contract:** Downstream cognitive routers interact with knowledge graph triples through a single interface.
* **Operational Constraint:** Complex multi-hop graph community clustering algorithms (e.g. Leiden / Louvain) require higher compute in PostgreSQL compared to native graph engines.

## Future Review Criteria
* Re-evaluate graph traversal latency if recursive PostgreSQL CTEs exceed 200ms on 5-hop queries.
