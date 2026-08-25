---
id: Retriever_API_v1_rlm
title: "API Specification: Recursive Language Model & Sandboxed Python REPL (/v1/rlm)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/rlm
  - cognitive/tree-synthesis
  - cognitive/python-repl
  - platform/retriever
blast_radius: HIGH
security_auth: BEARER_JWT
invariants:
  - "Python REPL execution MUST run in an isolated subprocess sandbox with 2.0s CPU timeout."
  - "File system, socket networking, and subprocess creation MUST be disabled in REPL AST."
---

# API Specification: Recursive Language Model & Sandboxed Python REPL (`/v1/rlm`)

#api #rlm #repl #sandbox #python #treesynthesis #retriever

> **Authoritative specification for recursive hierarchical document tree synthesis and zero-hallucination sandboxed Python REPL computation.**

---

## 1. RLM Hierarchical Synthesis Architecture

```mermaid
flowchart TD
    Doc[Large 200+ Page Document Corpus] --> L1[Level 1: Leaf Chunk Summaries]
    L1 --> L2[Level 2: Section Synthesis Nodes]
    L2 --> L3[Level 3: Chapter Synthesis Nodes]
    L3 --> Root[Root Executive Summary & Cross-Chapter Insights]
    
    Root --> Query[Targeted Synthesis Query]
    Query --> REPL[AST Sandboxed Python REPL Engine]
    REPL --> ExactMath[Deterministic Numerical Result]
```

---

## 2. API Endpoints

### 2.1 Execute Sandboxed Python REPL Code

Executes arbitrary math, statistical aggregation, or deterministic transformations in a hardened sandbox.

- **HTTP Method:** `POST`
- **Path:** `/v1/tenants/{tenantId}/rlm/repl`
- **Authentication:** `Bearer <TOKEN>`
- **Request Body:**
```json
{
  "code": "data = [1200, 3400, 5600, 1900]\nmean = sum(data) / len(data)\nprint(f'Mean: {mean:.2f}')"
}
```

#### Response Schema (`200 OK`)
```json
{
  "status": "success",
  "stdout": "Mean: 3025.00\n",
  "stderr": "",
  "executionDurationMs": 14.2,
  "exitCode": 0
}
```

---

## 🔗 Related Architecture & Cross-References
- [Agentic Workflows & REPL Sandbox](../cognitive/agentic_workflows_and_repl.md)
- [Agentic Tool Execution](agentic.md)
