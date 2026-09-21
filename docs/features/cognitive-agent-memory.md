# Cognitive Agent Memory Consolidation & Experience Distillation

**Milestone:** M108 (v0.92.0)  
**System Layer:** Machine Learning & Cognitive Intelligence (Platform Battery #25)  
**Architecture:** Ebbinghaus Retention Decay Curve + Episodic & Procedural Memory Synthesis + Semantic Reflection  

---

## 1. Executive Summary

Milestone 108 registers **Platform Battery #25 (`cognitive_agent_memory`)** under the `ML_INTELLIGENCE` category.

Standard conversational systems treat user sessions as ephemeral context windows: once a session expires or exceeds its token limit, historical problem-solving patterns, user preferences, and learned operational mistakes are permanently lost.

Milestone 108 introduces long-horizon agent memory consolidation:
- **Dual-Tier Memory Model:**
  - **Episodic Memory:** Stores concrete past interaction trajectories, tool arguments, and successful execution traces.
  - **Procedural Reflexes:** Distills recurring execution patterns into synthesized behavioral heuristics ("When queried for financial tables, always format decimals to 2 places and verify totals via the REPL").
- **Ebbinghaus Forgetting & Retention Decay Curve:** Dynamically weighs memory relevance using logarithmic decay based on time elapsed and access frequency:
  $$R(t) = e^{-\lambda \cdot \Delta t} \cdot (1 + \alpha \cdot \log(1 + f_{\text{access}}))$$
- **Pre-Execution Context Injection:** Automatically injects the top-$k$ most relevant consolidated memories into downstream ReAct reasoning loops and multi-agent debates, preventing repeated mistakes.

---

## 2. Mathematical Foundation

### Retention Probability
For a memory node $m$ with age $\Delta t$ days and access count $f$:
$$S(m, q) = \underbrace{\cos(\mathbf{e}_m, \mathbf{e}_q)}_{\text{Semantic Similarity}} \times \underbrace{\exp(-\lambda \cdot \Delta t)}_{\text{Ebbinghaus Decay}} \times \underbrace{\left(1 + \beta \cdot \frac{f}{f + 1}\right)}_{\text{Reinforcement Boost}}$$
Where:
- $\lambda = 0.05$: Daily exponential decay rate.
- $\beta = 0.3$: Access frequency reinforcement coefficient.

---

## 3. Battery Specifications & Parameters

- **Identifier:** `cognitive_agent_memory`
- **Category:** `ML_INTELLIGENCE`
- **Latency Profile:** `<8ms` memory retrieval
- **Algorithm Foundation:** Ebbinghaus Retention Decay Curve + Episodic / Procedural Experience Distillation
- **Health Check Endpoint:** `/v1/agentic/memory`

### Active Parameters
| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `decay_lambda` | `float` | `0.05` | Exponential decay rate parameter |
| `consolidation_batch_size` | `int` | `25` | Session turns required before background consolidation |
| `retrieval_k` | `int` | `5` | Top-$k$ memory guidelines injected into prompts |
| `min_similarity_threshold` | `float` | `0.72` | Minimum cosine similarity to trigger injection |

---

## 4. PostgreSQL Persistence & Row-Level Security (RLS) (M124)

Prior to Milestone 124, consolidated memory nodes resided strictly in ephemeral process memory (`_stores: dict[str, dict]`), which was lost on pod restart.

Milestone 124 introduces full relational persistence with database-level multi-tenancy:

### 4.1 Schema Definition (`cognitive_memories`)
```sql
CREATE TABLE cognitive_memories (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    memory_type VARCHAR(32) NOT NULL DEFAULT 'episodic',
    query TEXT NOT NULL,
    distilled_insight TEXT NOT NULL,
    tool_chain JSONB NOT NULL DEFAULT '[]'::jsonb,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    turns_count INTEGER NOT NULL DEFAULT 1,
    importance_score FLOAT NOT NULL DEFAULT 0.5,
    stability_score FLOAT NOT NULL DEFAULT 1.0,
    last_accessed_at DOUBLE PRECISION NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at DOUBLE PRECISION NOT NULL,
    embedding vector(768),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX ix_cognitive_memories_tenant_id ON cognitive_memories(tenant_id);
CREATE INDEX ix_cognitive_memories_tenant_type ON cognitive_memories(tenant_id, memory_type);
CREATE INDEX ix_cognitive_memories_embedding_hnsw 
    ON cognitive_memories USING hnsw (embedding vector_cosine_ops);
```

### 4.2 Row-Level Security (RLS) Policy
```sql
ALTER TABLE cognitive_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_cognitive_memories ON cognitive_memories
    FOR ALL
    USING (tenant_id::text = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant', true));
```

### 4.3 Architecture & Write-Through Lifecycle
1. **Hydration on Demand (`_ensure_tenant_store`):** Upon first access for tenant $T$, `CognitiveMemoryEngine` lazily queries `PgCognitiveMemoryRepository.get_nodes(tenant_id)` to warm the local process cache.
2. **Write-Through Persistence:** Calls to `consolidate_trace()` immediately persist new episodic nodes into `cognitive_memories`.
3. **Telemetry & Reinforcement:** Memory retrievals asynchronously update `access_count` and `stability_score` via `PgCognitiveMemoryRepository.update_access()`.
4. **Hygiene & Compliance:** Deletion requests (`delete_memory()`) execute atomic cascading deletions at the database layer.
