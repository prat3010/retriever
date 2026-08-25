---
id: DeepDive_GraphRAG_Topology
title: "Cognitive Deep-Dive: GraphRAG Knowledge Graph & Dynamic Topology"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/graphrag
  - cognitive/knowledge-graph
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Graph entity extraction MUST enforce strict typed ontology (e.g. PERSON, ORG, TECH, CONCEPT)."
  - "Multi-hop graph traversal MUST support 1 to 5 hops with cycle detection."
---

# Cognitive Deep-Dive: GraphRAG Knowledge Graph & Dynamic Topology

#cognitive #graphrag #knowledgegraph #triples #cypher #retriever

> **Technical architecture, entity-relation triple extraction, and multi-hop graph traversal in Retriever's dual-engine GraphRAG subsystem.**

---

## 1. Dual-Engine GraphRAG Architecture

Retriever supports a flexible dual-engine architecture for knowledge graph persistence and querying:
1. **Relational PostgreSQL Engine (`graph_triples` table):** Zero-overhead RDF-style triples with recursive CTE SQL queries for 1–3 hop neighbor traversals.
2. **Dedicated Neo4j Engine (Cypher):** High-performance labeled property graph for deep 3–5 hop path finding and community summarization.

```mermaid
flowchart LR
    Doc[Ingested Document Chunks] --> LLM[Entity & Triple Extraction LLM]
    LLM --> Triples[(Subject, Predicate, Object) Triples]
    
    Triples --> Store{Persistence Engine}
    Store -->|Default| PG[PostgreSQL graph_triples Table]
    Store -->|Enterprise| Neo4j[Neo4j Cypher Graph Database]
    
    UserQuery([Complex Multi-Entity Query]) --> GraphRetriever[GraphRAG Subsystem]
    GraphRetriever --> Traverse[1-3 Hop Breadth-First Expansion]
    Traverse --> Subgraph[Extracted Subgraph & Dynamic SVG Topology]
    Subgraph --> Context[Inject into LLM Prompt Context]
```

---

## 2. Dynamic SVG Topology Map Generation

Retriever transforms extracted entity graphs into interactive SVG visual topology maps rendered directly in the Client Studio UI (`TopologyMap.tsx`), enabling users to inspect conceptual connections across documents.

---

## 🔗 Related Architecture & Cross-References
- [Master Admin Gateway Specification](../api/admin.md)
- [Hybrid Search & Fusion](hybrid_search_and_fusion.md)
- [Database Schemas & Tables](../infrastructure/database_and_schemas.md)
