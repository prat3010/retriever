# Technical Stack, Frameworks & Deep Proficiency Matrix

Architecture Tier: Modern Enterprise Full-Stack & Cognitive AI
Frontend Engine: Next.js 16 (App Router), React 19, TypeScript 5.8
Backend Framework: FastAPI (Python 3.13), Uvicorn, Celery
Database Architecture: PostgreSQL 16, pgvector extension, Supabase BaaS
Vector Inference: Local Ollama (`nomic-embed-text`), ColBERT MaxSim
Deployment Model: Hybrid Cloud (Vercel Edge + Oracle Cloud VPS)

---

## 1. Subsystem Architecture & Technology Selection

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND CLIENT & CONTROL PLANE                    │
│   Next.js 16 (App Router) • React 19 • TypeScript • CSS Modules • Lenis   │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │  HTTPS / WSS / SSE Streaming
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    API GATEWAY & HYBRID SEARCH SERVICE                    │
│        FastAPI (Python 3.13) • Strict Hexagonal Ports & Adapters          │
├─────────────────────────────────────┬─────────────────────────────────────┤
│   Dense Vector Search               │   Sparse Keyword Search             │
│   Ollama nomic-embed-text (768d)    │   Sublinear BM25 Index              │
│   pgvector Cosine Distance (HNSW)   │   PostgreSQL Full-Text Search (ts)  │
├─────────────────────────────────────┴─────────────────────────────────────┤
│                      RECIPROCAL RANK FUSION (RRF k=60)                    │
│                 TOKEN-LEVEL COLBERT MAXSIM LATE RERANKING                 │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │  Connection Session Context
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER & SECURITY ISOLATION                  │
│       PostgreSQL 16 Engine • Row-Level Security (RLS) Multi-Tenancy       │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technical Stack Performance & Hardware Budget Matrix

| Layer / Subsystem | Primary Technology | Target P95 Latency | Target P99 Latency | Memory Footprint | Concurrency Budget |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Edge Web Serving** | Next.js 16 App Router | 18 ms | 45 ms | ~128 MB / edge lambda | 10,000+ req/sec (Vercel Edge) |
| **Semantic Response Cache** | In-Memory Cosine Hash | 8 ms | 22 ms | ~256 MB RAM | 2,500 req/sec |
| **Dense Vector Query** | pgvector HNSW (768d) | 35 ms | 65 ms | ~1.5 GB Index Cache | 400 queries/sec |
| **Sparse BM25 Index** | PostgreSQL TSVector / GIN | 12 ms | 30 ms | ~400 MB Shared Buffer| 800 queries/sec |
| **ColBERT MaxSim Rerank**| PyTorch / NumPy Vectorized | 40 ms | 85 ms | ~800 MB RAM | 150 evaluations/sec |
| **Local Text Embedding** | Ollama nomic-embed-text | 60 ms | 110 ms | ~1.8 GB RAM (VPS) | 50 docs/sec |
| **Layout-Aware PDF Parse**| RapidOCR + Docling Core | 250 ms / page | 450 ms / page | ~1.2 GB RAM (Worker) | 12 pages/sec |

---

## 3. Production Code Implementations

### Python Database-Level RLS Tenant Session Manager
In Retriever, multi-tenancy is never trusted to application-level query parameters. It is enforced directly at the connection level via PostgreSQL session variables:

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.adapters.database.connection import async_session_factory

@asynccontextmanager
async def tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated SQLAlchemy session with PostgreSQL RLS variables bound."""
    async with async_session_factory() as session:
        # Enforce PostgreSQL connection session variable for RLS
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Corresponding PostgreSQL Row-Level Security Policy:
```sql
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON document_chunks
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```

### TypeScript Transitive DAG Dependency Closure Resolver
In the Scoping Studio, feature prerequisites (such as `payments` and `auth` before `booking`) are dynamically resolved using directed acyclic graph topological traversals:

```typescript
export interface FeatureModule {
  id: string;
  label: string;
  dependsOn?: string[];
}

export function resolveFeatureDependencies(
  selectedIds: string[],
  catalog: FeatureModule[]
): string[] {
  const catalogMap = new Map(catalog.map((m) => [m.id, m]));
  const resolved = new Set<string>(selectedIds);
  const queue = [...selectedIds];

  while (queue.length > 0) {
    const currentId = queue.shift()!;
    const module = catalogMap.get(currentId);
    if (!module || !module.dependsOn) continue;

    for (const depId of module.dependsOn) {
      if (!resolved.has(depId)) {
        resolved.add(depId);
        queue.push(depId);
      }
    }
  }

  return Array.from(resolved);
}
```

---

## 4. Software Craftsmanship & Testing Rigor

- **Strict Static Typing:** 100% strict TypeScript (`tsconfig.json` with `strict: true`, `noImplicitAny: true`) and full Python type annotations checked via Pyright / Mypy.
- **Automated Test Coverage:**
  - Python: Over 600 tests across unit, integration, and RAG evaluation suites running on Pytest with AsyncIO.
  - TypeScript: Vitest suites asserting DAG dependency closures, currency conversion parity, and PDF page counts.
- **Zero-Lint Tolerances:** Ruff enforced with strict rule selections (E, F, B, SIM, I, UP) and ESLint with React Compiler guidelines.
