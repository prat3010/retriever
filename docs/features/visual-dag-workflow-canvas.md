# Visual DAG Workflow Canvas & Agentic Graph Composer (Platform Battery #40)

## Overview & Executive Summary

**Milestone 126 (v2.4.0)** delivers an interactive visual workflow design studio, declarative DAG execution compiler, and step-by-step pipeline stepper to Retriever.

Previously, complex multi-step pipelines (such as legal compliance auditing, intent-routed customer support, and code analysis) required writing code or rigid procedural workflows. The Visual DAG Studio allows non-developer architects and AI engineers to visually compose, connect, cycle-check, debug, and execute multi-node cognitive DAG pipelines with real-time token cost attribution and out-of-the-box enterprise templates.

---

## Architectural Topology & Mathematical Formulation

### 1. Kahn's Algorithm for Topological Sort & Cycle Detection

A workflow graph is modeled as a directed graph $G = (V, E)$, where $V$ represents computational nodes and $E$ represents directed dependency links $(u, v)$ with $u, v \in V$.

The compiler computes in-degrees $\text{deg}^-(v)$ for all $v \in V$:
$$\text{deg}^-(v) = \sum_{(u, v) \in E} 1$$

A queue $Q$ is initialized with all vertices having in-degree 0:
$$Q = \{v \in V \mid \text{deg}^-(v) = 0\}$$

Iteratively, vertex $u$ is removed from $Q$ and appended to topological order $L$. For each outgoing edge $(u, v)$, $\text{deg}^-(v)$ is decremented:
$$\text{deg}^-(v) \leftarrow \text{deg}^-(v) - 1$$
If $\text{deg}^-(v) = 0$, $v$ is enqueued into $Q$.

**Cycle Invariant:**
If $|L| < |V|$, there exists at least one directed cycle $C \subseteq V$. The compiler isolates the cyclical component $V_{\text{cycle}} = V \setminus L$ and aborts compilation with `CyclicWorkflowError`.

### 2. Level-Based Parallel Stage Partitioning

To maximize execution concurrency, nodes are partitioned into topological stages $S_0, S_1, \dots, S_K$:
$$\text{level}(v) = \begin{cases} 0 & \text{if } \text{deg}^-(v) = 0 \\ \max_{(u, v) \in E} (\text{level}(u)) + 1 & \text{otherwise} \end{cases}$$

Nodes at the same level $\text{level}(v) = k$ possess zero mutual dependencies and are executed concurrently via `asyncio.gather`.

### 3. Cubic Bézier Curve Geometry

The visual canvas connects port anchors $(x_1, y_1)$ on source nodes to $(x_2, y_2)$ on target nodes using parametric cubic Bézier splines $C(t)$:
$$C(t) = (1-t)^3 P_0 + 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3 P_3, \quad t \in [0, 1]$$
where control points are horizontally offset:
$$P_0 = (x_1, y_1), \quad P_1 = (x_1 + \Delta x, y_1), \quad P_2 = (x_2 - \Delta x, y_2), \quad P_3 = (x_2, y_2)$$
$$\Delta x = \max(40, |x_2 - x_1| \times 0.45)$$

### 4. Per-Step Token Cost Attribution

Every node invocation records input tokens $T_{\text{in}}$, output tokens $T_{\text{out}}$, execution latency $\tau_{\text{ms}}$, and cost $C_{\text{USD}}$:
$$C_{\text{node}} = \left(\frac{T_{\text{in}}}{1000} \times P_{\text{in}}\right) + \left(\frac{T_{\text{out}}}{1000} \times P_{\text{out}}\right) + C_{\text{flat}}$$
where $P_{\text{in}} = \$0.00015 / \text{1K}$, $P_{\text{out}} = \$0.00030 / \text{1K}$, and $C_{\text{flat}} = \$0.00005$ for vector searches.

---

## Node Taxonomy

| Node Type | Responsibility | Configurable Parameters | Inputs | Outputs |
|---|---|---|---|---|
| `INPUT` | User trigger & parameter ingress | `default_query` | User payload | `query`, `raw_input` |
| `RETRIEVAL` | Dense HNSW + sparse BM25 search | $k$, strategy (`hybrid`, `vector`, `splade`), threshold | `query` | `context`, `retrieved_chunks` |
| `GUARDRAIL` | Regex PII scrub & safety filtering | `mode` (`pii_redact`), `fail_action` (`mask`, `block`) | `query`, `content` | `sanitized_query`, `is_safe` |
| `TRANSFORM` | Context compression & AST symbol parsing | `operation` (`compress`, `ast_extract`) | `context` | `compressed_context`, ratio |
| `PROMPT` | String template interpolation | `template` with `{var}` substitution | Upstream vars | `interpolated_prompt` |
| `LLM` | Cognitive answer generation | `model`, `temperature`, `max_tokens`, `system_prompt` | `prompt` | `response`, `answer`, tokens |
| `EVALUATOR` | Groundedness & faithfulness score | `metric` (`faithfulness`), `threshold` (0.70) | `context`, `response` | `faithfulness_score`, `passed` |
| `ROUTER` | Conditional branch routing | `condition_key`, `default_branch` | `passed`, `intent` | `selected_branch` |
| `OUTPUT` | Final response formatting | N/A | `answer`, citations | `final_output` |

---

## Pre-Configured Enterprise Templates

1. **Legal Document & Contract Analyzer (`tpl_legal_analyzer`):**
   `Input` $\to$ `PII Redaction` $\to$ `Clause Retrieval (k=8)` $\to$ `Context Compression` $\to$ `Statute Analysis Prompt` $\to$ `Legal LLM` $\to$ `Faithfulness Gate (0.75)` $\to$ `Audit Memo Output`.
2. **Customer Support & FAQ Copilot (`tpl_customer_support`):**
   `Input` $\to$ `Intent Router` $\to$ `KB Search (k=5)` $\to$ `Tone & Policy Prompt` $\to$ `Support Copilot LLM` $\to$ `Resolution Output`.
3. **Technical Codebase & Architecture Assistant (`tpl_codebase_assistant`):**
   `Input` $\to$ `AST Symbol Extraction` $\to$ `Hybrid Code Search (k=6)` $\to$ `Code Reasoning Prompt` $\to$ `Coding Copilot LLM` $\to$ `Engineered Code Output`.
4. **Multimodal Schematic & Diagram Inspector (`tpl_multimodal_inspector`):**
   `Input` $\to$ `Vision GraphRAG Search (k=5)` $\to$ `Cross-Modal Linker` $\to$ `System Topology Prompt` $\to$ `Diagnostic LLM` $\to$ `Diagnostic Report Output`.

---

## REST API Specification

### 1. Compile DAG Workflow
- **Route:** `POST /v1/tenants/{tenantId}/workflows/dag/compile`
- **Auth:** Tenant Bearer API Key or `X-Admin-Master-Key`
- **Request:** `WorkflowDAGGraph`
- **Response:** `DAGCompilerResult` (topological order, parallel stages, warnings, errors).

### 2. Execute DAG Workflow
- **Route:** `POST /v1/tenants/{tenantId}/workflows/dag/execute`
- **Auth:** Tenant Bearer API Key or `X-Admin-Master-Key`
- **Request:** `{"graph": WorkflowDAGGraph, "input_payload": {"query": "..."}}`
- **Response:** `DAGExecutionResult` (step details, latency ms, tokens, USD cost, final output).

### 3. Enterprise Templates
- **Route:** `GET /v1/tenants/{tenantId}/workflows/dag/templates`
- **Route:** `GET /v1/tenants/{tenantId}/workflows/dag/templates/{templateId}`

---

## Verification Records

- **Unit Tests:** `apps/api/tests/test_dag_workflow.py` (9/9 passed in 2.31s).
- **Battery Tests:** `apps/api/tests/test_batteries.py` (10/10 passed in 2.38s, total 40 batteries).
- **Zero-Toy Linter:** `python3 scripts/audit_zero_toy.py` (353 files scanned, 0 violations).
- **Web Studio Build:** `apps/web` compiled cleanly via Next.js 16 (Turbopack) in 2.2s.
