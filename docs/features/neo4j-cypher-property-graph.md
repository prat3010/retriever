# Neo4j Cypher Labeled Property Graph Engine & Recursive CTE Fallback

**Milestone:** M37 / M44 (v0.35.0)  
**System Layer:** Labeled Property Graph (LPG) Indexing & Multi-Hop Traversal (Platform Battery #7)  
**Architecture:** Neo4j Bolt Protocol Driver + Cypher Pattern Matching Engine + In-Database PostgreSQL Recursive CTE Fallback  

---

## 1. Executive Summary

Milestones 37 and 44 establish **Platform Battery #7: `neo4j_cypher_graph`**, providing native multi-hop graph traversal and labeled relationship mapping for Retriever.

Pure vector similarity operates on unlinked chunks, unable to answer relational queries such as:
- *"Which API endpoints depend on the authentication session verifier, and what database tables do they modify?"*
- *"Find all third-party vendors with access to tenant data and trace their upstream compliance certifications."*

Platform Battery #7 deploys a dual-engine graph architecture:
1. **Primary Engine:** High-performance Neo4j instance connected via the binary Bolt protocol, executing Cypher queries over nodes and directed edges with sub-5ms traversal latency.
2. **Fallback Engine:** Zero-dependency PostgreSQL Recursive Common Table Expression (CTE) engine that executes multi-hop graph traversals directly inside PostgreSQL if Neo4j is offline or unavailable.

---

## 2. Dual-Engine Architecture & Seamless Fallback

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DUAL-ENGINE GRAPH RETRIEVAL TOPOLOGY                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Graph Traversal Request (src_node, max_hops=5) ]                                   │
│                        │                                                               │
│                        ▼                                                               │
│          ┌───────────────────────────┐                                                 │
│          │ GraphRepository Dispatcher│                                                 │
│          └─────────────┬─────────────┘                                                 │
│                        │                                                               │
│            ┌───────────┴───────────┐                                                   │
│            ▼ (Neo4j Healthy)       ▼ (Neo4j Unavailable / Timeout)                    │
│   ┌─────────────────────┐ ┌────────────────────────────────────────────────────────┐   │
│   │ Neo4j Bolt Driver   │ │ PostgreSQL Recursive CTE Fallback                      │   │
│   │ - Cypher MATCH      │ │ - WITH RECURSIVE graph_hops AS (                       │   │
│   │ - Pointer-hopping   │ │     SELECT target, relation, 1 as depth ...            │   │
│   │ - Sub-5ms traversal │ │     UNION ALL SELECT ... WHERE depth < :max_hops)      │   │
│   └──────────┬──────────┘ └───────────────────────────┬────────────────────────────┘   │
│              │                                        │                                │
│              └───────────────────┬────────────────────┘                                │
│                                  ▼                                                     │
│                ┌───────────────────────────────────┐                                   │
│                │ Unified GraphTraversalResult      │                                   │
│                │ - Nodes, Edges, Paths & Hops      │                                   │
│                └───────────────────────────────────┘                                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Cypher Traversal & PostgreSQL CTE Equivalence

### Native Cypher Query (Neo4j)
```cypher
MATCH path = (start:Entity {id: $source_id, tenant_id: $tenant_id})-[r:RELATES_TO*1..5]->(target:Entity)
RETURN nodes(path) AS entities, relationships(path) AS relations;
```

### Automatic PostgreSQL Recursive CTE Fallback
```sql
WITH RECURSIVE traverse AS (
    -- Anchor member: direct neighbors
    SELECT 
        ge.source_id, ge.target_id, ge.relation_type, 1 AS depth,
        ARRAY[ge.source_id, ge.target_id] AS path
    FROM graph_edges ge
    WHERE ge.source_id = :source_id AND ge.tenant_id = :tenant_id

    UNION ALL

    -- Recursive member: expand paths
    SELECT 
        ge.source_id, ge.target_id, ge.relation_type, t.depth + 1,
        t.path || ge.target_id
    FROM graph_edges ge
    JOIN traverse t ON ge.source_id = t.target_id
    WHERE t.depth < :max_hops 
      AND NOT ge.target_id = ANY(t.path) -- Cycle prevention
      AND ge.tenant_id = :tenant_id
)
SELECT * FROM traverse;
```

---

## 4. Implementation Details

- **Repository:** `apps/api/src/adapters/database/graph_repository.py` (`DualGraphRepository`)
- **Domain Abstraction:** `src/domain/abstractions/graph.py`
- **Supported Max Hops:** Up to 5 traversals.
- **Latency Profile:** $<5\text{ms}$ on Neo4j; $<12\text{ms}$ on PostgreSQL Recursive CTE.
- **Health Check Endpoint:** `GET /v1/admin/tenants/{tenantId}/graph/capabilities`

---

## 5. Non-Negotiable Invariants

1. **Cycle Prevention:** Traversal queries MUST enforce path cycle detection (`NOT ge.target_id = ANY(t.path)`) to eliminate infinite loops on circular graphs.
2. **Tenant Boundary Enforcement:** Every edge and node query must filter strictly by `tenant_id`. Graph edges across different tenants are never traversed.
3. **Transparent Failover:** When Neo4j fails to respond within 500ms, the adapter switches to the PostgreSQL CTE engine transparently with zero error thrown to the user.
