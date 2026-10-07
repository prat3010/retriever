# Systems Architecture Whitepapers: Multi-Tenancy & Hexagonal Boundaries

Author: Prateek Sharma (Forward Deployed AI Engineer)
Publication Tier: Enterprise Technical Documentation & Architectural Standards
Topics: Multi-Tenancy RLS, Hexagonal Architecture, AST Knowledge Graphs

---

## Whitepaper 1: Database-Level Row-Level Security (RLS) vs Application-Level Tenant Filtering

### The Threat Model of Application-Level Multi-Tenancy
Most multi-tenant SaaS applications rely on application-level filtering, commonly implemented as:
```python
# FRAGILE: Application-level tenant filtering
query = session.query(Document).filter(
    Document.tenant_id == current_user.tenant_id,
    Document.id == requested_doc_id
)
```
While simple, this pattern introduces severe enterprise security liabilities:
1. **Developer Oversight:** A single junior developer omission or complex SQL join omitting `tenant_id` immediately leaks cross-tenant records.
2. **ORM & Subquery Leaks:** Subqueries, aggregations, and raw SQL queries can bypass global query filters.
3. **Internal Tooling Exposure:** Support scripts, batch migrations, and ad-hoc analytics running with read credentials lack row-level protection.

### The PostgreSQL Row-Level Security (RLS) Guarantee
By migrating multi-tenancy enforcement down into the database kernel, PostgreSQL guarantees that no query—regardless of how it was constructed in Python, TypeScript, or Go—can read or write a record belonging to another tenant.

| Architectural Dimension | Application-Level Filtering | Database-Level RLS (Retriever Standard) |
| :--- | :--- | :--- |
| **Enforcement Point** | Application web framework / ORM | PostgreSQL Database Engine Kernel |
| **Leakage Vulnerability** | High (accidental omission in JOIN or subquery) | Mathematically Zero (enforced at row read) |
| **Raw SQL Safety** | Unprotected (raw queries bypass ORM hooks) | 100% Protected (RLS intercepts raw SQL) |
| **Developer Cognitive Load**| High (must verify `WHERE tenant_id` on every query)| Zero (tenant session is set once per request) |
| **Performance Overhead** | None | Negligible (<2% CPU overhead with indexed keys) |

### Implementation Standard
Every connection checkout executes a lightweight session-variable binding:
```sql
SET LOCAL app.current_tenant_id = 'b0d64742-d5e9-425f-a6ca-57eb003cf2be';
```
PostgreSQL evaluates the policy predicate in-line using index scans on `(tenant_id, document_id)`:
```sql
CREATE POLICY chunk_isolation ON document_chunks
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```

---

## Whitepaper 2: Hexagonal Architecture (Ports and Adapters) in Fast-Moving AI Products

### The Fragility of Framework-Coupled AI Architectures
The rapid evolution of generative AI libraries (LangChain, LlamaIndex, LiteLLM) often results in severe architectural decay. Framework abstractions couple business logic to changing third-party APIs, breaking builds when vendor APIs introduce breaking changes.

### The Hexagonal Boundary Doctrine
Retriever enforces strict Hexagonal Architecture (Alistair Cockburn's Ports and Adapters):
1. **The Domain Core is Pure:** `src/domain/` contains zero external dependencies other than Python standard libraries. It models core entities (`Document`, `Chunk`, `Query`, `SearchResult`) and defines abstract interfaces (`EmbeddingProvider`, `VectorStoragePort`, `RerankerPort`).
2. **Adapters Implement Inverted Dependencies:** All vendor SDKs (`pgvector`, `Ollama`, `Gemini`, `OpenAI`) reside strictly inside `src/adapters/` and implement the abstract domain interfaces.
3. **The Dependency Inversion Principle:** The core domain never imports an adapter. Adapters import domain interfaces.

```
       [ FastAPI Router ]        [ CLI Tool ]        [ Event Consumer ]
               │                       │                     │
               ▼                       ▼                     ▼
        ┌─────────────────────────────────────────────────────────┐
        │                 DRIVING PORTS (API / CLI)               │
        ├─────────────────────────────────────────────────────────┤
        │                   PURE DOMAIN CORE                      │
        │       Entities • Business Logic • Orchestration         │
        ├─────────────────────────────────────────────────────────┤
        │                DRIVEN PORTS (ABSTRACTIONS)              │
        └─────────────────────────────────────────────────────────┘
               ▲                       ▲                     ▲
               │                       │                     │
      [ pgvector Adapter ]    [ Ollama Adapter ]    [ Redis Cache ]
```

### Strategic Benefits
- **Zero-Mock Domain Testing:** Domain unit tests execute in milliseconds using in-memory mock adapters without spinning up Docker or external network connections.
- **Trivial Model Swapping:** Migrating from local Ollama to cloud Gemini requires authoring a single adapter file conforming to `EmbeddingProvider`; zero domain or API router files are modified.

---

## Whitepaper 3: Offline-First Synchronizer & AST Architecture Knowledge Graphs

### The Documentation Drift Anti-Pattern
In fast-iterating engineering projects, visual architecture diagrams and markdown documentation rapidly diverge from actual code, leading to incorrect assumptions during system expansion.

### AST-Driven Codebase Synchronization
The PrateekSync developer engine eliminates documentation drift through automated Python Abstract Syntax Tree (AST) analysis:
1. **Automated AST Crawling:** Scripts parse all Python and TypeScript files, extracting class definitions, imported modules, and function call boundaries.
2. **Blast Radius Analysis:** When an engineer modifies an interface (e.g., `EmbeddingProvider`), the AST engine calculates the exact transitive blast radius across all dependent adapters and routes.
3. **Automated Obsidian Canvas Regeneration:** The AST graph directly compiles an interactive Obsidian Canvas (`architecture_topology.canvas`), automatically laying out nodes and directional dependency arrows based on actual git commits.
