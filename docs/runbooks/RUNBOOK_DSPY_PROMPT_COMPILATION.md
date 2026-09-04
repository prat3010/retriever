# Runbook: DSPy Declarative Prompt Compilation & Algorithmic Optimization

**Service:** Retriever Cognitive Engine  
**Milestone:** 92 (Phase L)  
**Version:** `v0.77.0`  
**Classification:** Prompt Engineering & Cognitive Compilation Runbook  

---

## 1. Overview & Architecture

Retriever Milestone 92 replaces static string prompt templates with declarative DSPy prompt programs. Prompt compilation discovers high-leverage system prompt instructions and selects verified, high-scoring few-shot demonstrations from tenant evaluation datasets (`eval_questions` / `eval_datasets`).

### Architectural Topology

```text
POST /v1/tenants/{tenantId}/prompts/compile
                 │
                 ▼
     [DSPyCompilerAdapter]
         ├── 1. Evaluate Handcrafted Baseline Score (e.g. 68%)
         ├── 2. Teleprompter Optimization (BootstrapFewShot / MIPROv2)
         ├── 3. Filter Demonstrations by Grounding Metric
         └── 4. Validate Score Lift on Holdout Split (e.g. 89%, +30%)
                 │
                 ▼
     [SqlCompiledPromptRepository]  <── Stored in `compiled_prompt_programs`
                 │
      POST .../activate
                 │
                 ▼
       [Inference Engine]
         └── PromptBuilder injects compiled instructions and exemplars
             into live chat inference path
```

---

## 2. Teleprompter Optimization Strategies

### 1. `BootstrapFewShot`
- **Mechanism:** Runs model generations on training questions. Evaluates candidate answers using the target metric (`composite`, `faithfulness`, `context_relevance`).
- **Demonstration Pool:** Trajectories that exceed the quality threshold are filtered, deduplicated, and assembled into formatted few-shot exemplars with chain-of-thought (CoT) reasoning steps.
- **Best For:** Quick compilation runs, high demonstration precision, cold-start prompt optimization.

### 2. `MIPROv2` (Multi-Prompt Instruction Proposal & Evaluation)
- **Mechanism:** Jointly optimizes both the primary system prompt instructions and the selected few-shot demonstrations.
- **Instruction Proposal:** Synthesizes multiple prompt instruction variations from high-performing exemplars and scores candidates against the validation split.
- **Best For:** Complex enterprise domains with nuanced terminology or high anti-hallucination constraints.

### 3. `RandomSearch`
- **Mechanism:** Shuffles demonstration orders and samples candidate subsets to maximize stability and minimize positional bias.

---

## 3. Operational CLI & API Procedures

### A. Compiling a Prompt Program

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/{tenantId}/prompts/compile" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "support_cot_v1",
    "optimizer": "BootstrapFewShot",
    "metric_target": "composite",
    "max_demos": 3
  }'
```

**Response (`200 OK`):**
```json
{
  "program_id": "prog_a1b2c3d4e5f6",
  "tenant_id": "tn_client_123",
  "name": "support_cot_v1",
  "signature_name": "RAGAnswerSignature",
  "optimizer": "BootstrapFewShot",
  "baseline_score": 0.684,
  "compiled_score": 0.892,
  "improvement_pct": 30.41,
  "metric_name": "composite",
  "compiled_instruction": "You are Retriever's optimized cognitive agent...",
  "few_shot_demos": [ ... ],
  "is_active": false,
  "created_at": "2026-09-04T16:50:00Z"
}
```

### B. Hot-Activating a Compiled Program

Activating a program atomically deactivates any existing active program for that tenant and hot-reloads the prompt injection cache in `PromptBuilder`.

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/{tenantId}/prompts/compiled/prog_a1b2c3d4e5f6/activate" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY"
```

### C. Deactivating & Reverting to Default String Template

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/{tenantId}/prompts/compiled/prog_a1b2c3d4e5f6/deactivate" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY"
```

---

## 4. Troubleshooting & Health Checks

| Symptom | Probable Cause | Action |
|---|---|---|
| `401 Unauthorized` on `/prompts/compile` | Missing or invalid `X-Admin-Master-Key` | Verify header matches `ADMIN_MASTER_KEY` in environment. |
| Negative or zero improvement percentage | Inadequate training examples or ambiguous ground truth answers | Ensure tenant eval questions have clear factual reference answers in ingested chunks. |
| Chat inference latency increase | Too many few-shot demonstrations configured (`max_demos > 5`) | Reduce `max_demos` to 2 or 3 in the compilation request. |
| Tenancy violation error | Tenant ID in URL does not match API key claim | Use tenant-scoped API key or master admin key. |

---

## 5. Rollback Plan

If an activated compiled prompt causes behavioral anomalies:
1. Navigate to `/prompts` in the Retriever Admin Dashboard or `/rag/app` in the portfolio.
2. Click **Deactivate & Revert** in the Active Production State banner.
3. Live chat inference immediately falls back to the tenant's base handcrafted `PromptTemplate` without server downtime.
