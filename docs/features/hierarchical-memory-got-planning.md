# Hierarchical Memory Augmentation with Graph-of-Thoughts (GoT) Planning (Platform Battery #38)

## 1. Overview
The **Hierarchical Memory Augmentation with Graph-of-Thoughts (GoT) Planning (Battery #38)** introduces non-linear cognitive planning and multi-tiered associative memory into the Retriever Cognitive Engine.

While traditional Chain-of-Thought (CoT) and Tree-of-Thoughts (ToT) models restrict reasoning to sequential chains or strictly hierarchical branching trees, **Graph-of-Thoughts (GoT)** models cognitive reasoning as an arbitrary **Directed Acyclic Graph (DAG)** $G = (V, E)$. This enables:
1. **Multi-Parent Thought Aggregation ($M \to 1$):** Synthesizing, reconciling, and cross-validating divergent reasoning paths into a unified synergistic thought.
2. **Dynamic In-Process Refinement ($1 \to 1$):** Iteratively improving a thought's quality, correcting subtle logical errors, and boosting confidence.
3. **Adaptive Branch Pruning ($v \to \emptyset$):** Halting exploration of unpromising reasoning paths below an empirical threshold $\tau_{\text{prune}}$.
4. **3-Tier Hierarchical Memory Architecture:** Partitioning knowledge across **L1 Scratchpad** (volatile sub-step buffer), **L2 Episodic Memory** (decaying session history via the Ebbinghaus forgetting curve), and **L3 Semantic Memory** (distilled persistent knowledge graphs with associative spreading activation).

---

## 2. Mathematical Foundations

### 2.1. Graph-of-Thoughts DAG Representation
A cognitive plan is modeled as a Directed Acyclic Graph $G = (V, E)$ where:
- $V = \{v_1, v_2, \dots, v_n\}$ is the set of thought vertices.
- $E \subseteq V \times V$ is the set of directed reasoning dependency edges.

Each thought node $v \in V$ is parameterized by:
$$v = \langle \text{id}, \text{content}, \text{type}, \text{status}, S(v), d(v), \mathcal{M}(v) \rangle$$
Where:
- $\text{type} \in \{\text{ORIGIN}, \text{GENERATION}, \text{REFINEMENT}, \text{AGGREGATION}, \text{PRUNED}\}$
- $\text{status} \in \{\text{PENDING}, \text{EVALUATING}, \text{EXPLORING}, \text{PRUNED}, \text{CONVERGED}\}$
- $S(v) \in [0.0, 1.0]$ represents the empirical confidence / evaluation score of the thought.
- $d(v) \in \mathbb{N}_0$ is the node depth from the root origin.
- $\mathcal{M}(v) \in \{\text{L1\_SCRATCHPAD}, \text{L2\_EPISODIC}, \text{L3\_SEMANTIC}\}$ is the active memory tier.

### 2.2. Thought Transformations

1. **Branch Generation ($1 \to N$):**
   Given parent $u$, generate $k$ distinct reasoning continuations $\{v_1, \dots, v_k\}$ such that $(u, v_i) \in E$ and:
   $$S(v_i) = \min(1.0, S(u) + \Delta_{\text{gen}})$$

2. **Thought Aggregation ($M \to 1$):**
   Given parent subset $P = \{u_1, u_2, \dots, u_m\} \subset V$ where $m \ge 2$, synthesize a new convergence thought $v_{\text{agg}}$ with directed edges $(u_j, v_{\text{agg}}) \in E$ for all $j \in \{1, \dots, m\}$. The aggregate score reflects synergetic cross-validation:
   $$S(v_{\text{agg}}) = \min\left(1.0, \frac{1}{m} \sum_{j=1}^m S(u_j) + \alpha \cdot \sqrt{\frac{m - 1}{m}}\right)$$
   Where $\alpha \in (0, 0.25)$ rewards multi-perspective consensus.

3. **Thought Refinement ($1 \to 1$):**
   For a node $u$, generate improved variant $v_{\text{ref}}$ with $(u, v_{\text{ref}}) \in E$:
   $$S(v_{\text{ref}}) = \min(1.0, S(u) \cdot (1 + \beta))$$

4. **Branch Pruning:**
   For any thought $v$ where $S(v) < \tau_{\text{prune}}$ (default $0.35$):
   $$\text{status}(v) \leftarrow \text{PRUNED}, \quad \text{type}(v) \leftarrow \text{PRUNED}$$

### 2.3. Optimal Path Dynamic Programming via Kahn's Topological Sort
Because $G$ is guaranteed to be a DAG (enforced through cycle-detection on every edge insertion), an optimal reasoning trajectory from the origin root $v_0$ to any converged node $v_c$ is determined via Dynamic Programming over topological ordering:

1. Compute in-degree $d^-(v)$ for all $v \in V$.
2. Initialize queue with nodes where $d^-(v) = 0$.
3. Process nodes in topological order $L = [v_{(1)}, v_{(2)}, \dots, v_{(|V|)}]$.
4. For each node $v$, the maximum cumulative path score $DP[v]$ and predecessor $\pi[v]$ are computed as:
   $$DP[v] = S(v) + \max_{u \in \text{Parents}(v)} DP[u]$$
   $$\pi[v] = \arg\max_{u \in \text{Parents}(v)} DP[u]$$
5. Backtrack from $\arg\max_{v \in \text{Converged}} DP[v]$ to root $v_0$ to reconstruct the optimal reasoning path $\mathcal{P}^*$.

### 2.4. 3-Tier Hierarchical Memory & Ebbinghaus Forgetting Curve

Knowledge retention follows a 3-tier hierarchy:
- **L1 Scratchpad:** Transient in-flight execution buffer for active plan generation. Pruned or promoted upon convergence.
- **L2 Episodic Memory:** Stores task-level episode traces. Retention decays over time following Hermann Ebbinghaus's exponential forgetting law:
  $$R(t) = e^{-\frac{t}{S}}$$
  Where $t$ is the elapsed time (hours) since creation/access, and $S$ is memory stability (retention factor, default $S = 18.0\text{ hours}$).
- **L3 Semantic Memory:** Persistent cross-plan knowledge base. Formed by distilling converged DAG subgraphs into contracted associative nodes. Stability is reinforced:
  $$S_{\text{new}} = S_{\text{old}} \cdot (1 + \gamma \cdot \text{repetition})$$

### 2.5. Graph Contraction & Distillation Ratio
When a plan $G$ converges, distillation compresses the full reasoning DAG into high-order semantic insights:
$$\text{Contraction Ratio } C = 1 - \frac{|V_{\text{distilled}}|}{|V_{\text{raw}}|}$$
Consolidating verbose reasoning steps into dense, associative semantic representations without loss of salient decision points.

---

## 3. Architecture & Hexagonal Structure

```
                      FastAPI Router: /v1/got/* & /v1/tenants/{tenant_id}/got/*
                                             │
                                             ▼
                 Domain Abstraction Interface: GoTPlannerProtocol
                      (apps/api/src/domain/abstractions/got_planner.py)
                                             │
                                             ▼
                      Adapter: GoTPlannerAdapter (Battery #38)
                      (apps/api/src/adapters/cognitive/got_planner_adapter.py)
                                 ┌───────────┴───────────┐
                                 ▼                       ▼
                        GoT DAG Reasoning      3-Tier Memory Hierarchy
                        - Dynamic LLM Expansion- L1 Scratchpad
                        - Kahn's Topo Sort     - L2 Episodic (Ebbinghaus)
                        - Aggregation M->1     - L3 Semantic (Distilled)
                        - Refinement 1->1      - Spreading Activation
                        - DP Optimal Path
                                 │
                                 ▼
                     Repository: GoTRepositoryProtocol
                     Adapter: PgGoTRepository
                     (apps/api/src/adapters/database/got_repository.py)
                                 │
                                 ▼
                   PostgreSQL Tables (with Row-Level Security):
                   - got_graphs (graph metadata, query, optimal path)
                   - got_thoughts (vertices, scores, parents/children)
```

### 3.1 PostgreSQL Persistence Schema (`got_graphs` & `got_thoughts`)
```sql
CREATE TABLE got_graphs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    root_id VARCHAR(64) NOT NULL,
    best_score FLOAT NOT NULL DEFAULT 0.0,
    is_converged BOOLEAN NOT NULL DEFAULT FALSE,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_latency_ms FLOAT NOT NULL DEFAULT 0.0,
    optimal_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    edges JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE got_thoughts (
    id VARCHAR(64) PRIMARY KEY,
    graph_id VARCHAR(64) NOT NULL REFERENCES got_graphs(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    content TEXT NOT NULL,
    thought_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    score FLOAT NOT NULL DEFAULT 0.0,
    grounding_score FLOAT NOT NULL DEFAULT 0.0,
    coherence_score FLOAT NOT NULL DEFAULT 0.0,
    constraint_score FLOAT NOT NULL DEFAULT 0.0,
    token_cost INTEGER NOT NULL DEFAULT 0,
    latency_ms FLOAT NOT NULL DEFAULT 0.0,
    iteration_depth INTEGER NOT NULL DEFAULT 0,
    is_optimal_path BOOLEAN NOT NULL DEFAULT FALSE,
    parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    child_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at DOUBLE PRECISION NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE got_graphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE got_thoughts ENABLE ROW LEVEL SECURITY;
```

---

## 4. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/got/plans` | Create a new GoT planning session and root thought |
| `GET` | `/v1/got/plans/{plan_id}` | Retrieve full GoT DAG, topological path, and metrics |
| `POST` | `/v1/got/plans/{plan_id}/step` | Execute a discrete transformation (generate, aggregate, refine, prune) |
| `POST` | `/v1/got/plans/{plan_id}/execute` | Run autonomous convergence loop up to `max_iterations` |
| `POST` | `/v1/got/plans/{plan_id}/aggregate` | Multi-parent thought aggregation ($M \to 1$) |
| `GET` | `/v1/got/memory` | Retrieve 3-tier hierarchical memory view (L1, L2, L3) |
| `POST` | `/v1/got/plans/{plan_id}/distill` | Distill converged plan DAG into L3 Semantic memory |
| `POST` | `/v1/got/simulate` | Mathematical simulation of DAG search space & Ebbinghaus decay |
| `GET` | `/v1/got/health` | Health and diagnostic status of GoT planner battery |

---

## 5. Client SDK Usage

### TypeScript SDK (`@prat3010/retriever-client`)
```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  apiKey: "retriever_live_...",
  baseUrl: "http://localhost:8000",
  tenantId: "tn_client_enterprise",
});

// 1. Create a GoT Plan
const plan = await client.createGoTPlan({
  query: "Synthesize optimal multi-region pgvector failover with Raft consensus",
  branch_factor: 3,
  max_depth: 4,
  prune_threshold: 0.35,
  convergence_threshold: 0.85,
});

// 2. Aggregate Thoughts (M -> 1)
const parentIds = Object.keys(plan.graph.nodes).slice(1, 3);
const aggregated = await client.aggregateGoTThoughts(plan.plan_id, {
  parent_node_ids: parentIds,
  prompt: "Synthesize quorum tradeoffs from both candidate hypotheses",
});

// 3. Autonomous Execution
const converged = await client.executeGoTPlan(plan.plan_id, 10);
console.log("Converged Optimal Path:", converged.graph.optimal_path);

// 4. Distill into L3 Semantic Memory
const distilled = await client.distillGoTPlan(plan.plan_id, {
  target_tier: "L3_SEMANTIC",
});
console.log("Nodes consolidated:", distilled.nodes_consolidated);
```

### Python SDK (`retriever-python`)
```python
from retriever import RetrieverClient

client = RetrieverClient(
    api_key="retriever_live_...",
    base_url="http://localhost:8000",
    tenant_id="tn_client_enterprise",
)

# 1. Create Plan
plan = client.create_got_plan(
    query="Design multi-tenant zero-trust vector pipeline",
    branch_factor=3,
    max_depth=4,
)

# 2. Autonomous Execution
result = client.execute_got_plan(plan["plan_id"], max_iterations=8)
print("Converged:", result["graph"]["is_converged"])
print("Optimal Path:", result["graph"]["optimal_path"])

# 3. Inspect Memory Pyramid
memory = client.get_hierarchical_memory()
print(f"L1 Scratchpad: {len(memory['l1_scratchpad'])} nodes")
print(f"L2 Episodic: {len(memory['l2_episodic'])} nodes")
print(f"L3 Semantic: {len(memory['l3_semantic'])} nodes")
```
