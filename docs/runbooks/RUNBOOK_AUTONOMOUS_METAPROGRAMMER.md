# Operational Runbook: Autonomous Metaprogrammer & Capability Scaffolding Studio

**Runbook ID:** RB-OPS-097  
**Audience:** Platform Architects, Core Cognitive Engineers, System Automators  
**Applies to:** Retriever AI Engine (v0.82.0+, Milestone 97)  
**Platform Battery:** Battery #17 (`autonomous_metaprogrammer`)  

---

## 1. System Overview & AST Scaffolding Engine

The Autonomous Metaprogrammer synthesizes, lints, tests, and deploys new cognitive adapters, FastAPI routers, and domain abstractions directly from natural language or structured capability specifications:
- **AST Generation:** Emits deterministic Python AST nodes (`ast.parse`) with zero syntax hallucination.
- **Architectural Linter:** Enforces strict Hexagonal boundary rules (blocking forbidden framework imports like `fastapi`, `sqlalchemy`, or `redis` in `src/domain/abstractions/`).
- **Automated Test Synthesis:** Generates accompanying Pytest test suites ensuring domain purity and integration roundtrips.
- **Atomic Hot-Reload:** Applies generated files to disk with atomic backups, reloading uvicorn workers safely without downtime.

```text
  [ Platform Operator / Studio ]                             [ Retriever Metaprogrammer Engine ]
                 │                                                          │
                 │ 1. POST /v1/scaffold/generate (Capability Spec)          │
                 ├─────────────────────────────────────────────────────────►│ (Synthesize Python AST)
                 │◄─────────────────────────────────────────────────────────┤ (Returns AST preview)
                 │                                                          │
                 │ 2. POST /v1/scaffold/validate                            │
                 ├─────────────────────────────────────────────────────────►│ (Run Architectural Linter)
                 │◄─────────────────────────────────────────────────────────┤ (Report: 0 Boundary Violations)
                 │                                                          │
                 │ 3. POST /v1/scaffold/apply                               │
                 ├─────────────────────────────────────────────────────────►│ (Write to disk & hot-reload)
                 │◄─────────────────────────────────────────────────────────┤ (Capability LIVE)
```

---

## 2. Health Monitoring & Observability Commands

### 2.1 Verify Metaprogrammer Battery Status
Confirm that Battery #17 (`autonomous_metaprogrammer`) is active:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/scaffold/health | jq .
```

**Expected Output:**
```json
{
  "status": "healthy",
  "battery_id": "autonomous_metaprogrammer",
  "active_capabilities_generated": 12,
  "ast_validation_pass_rate": 1.0,
  "last_scaffold_timestamp": "2026-09-05T18:40:00Z"
}
```

---

## 3. Standard Operational Procedures (SOPs)

### SOP-SCAFFOLD-01: Generating a New Capability

To scaffold a new cognitive adapter or domain protocol:

```bash
curl -X POST "https://rag.prateeq.in/v1/scaffold/generate" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_name": "quantum_random_oracle",
    "description": "Hardware true random number generation for key derivation",
    "target_tier": "domain_abstraction",
    "methods": [
      { "name": "generate_entropy_bytes", "args": ["length: int"], "return_type": "bytes" }
    ]
  }' | jq .
```

### SOP-SCAFFOLD-02: Validating AST Architecture Boundaries

Always run architectural validation before writing to disk:

```bash
curl -X POST "https://rag.prateeq.in/v1/scaffold/validate" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "code_content": "from pydantic import BaseModel\nclass QuantumEntropy(BaseModel): ...",
    "target_path": "apps/api/src/domain/abstractions/quantum.py"
  }' | jq .
```

### SOP-SCAFFOLD-03: Applying Scaffolding to Live Codebase

Commit generated files to disk and trigger atomic hot-reload:

```bash
curl -X POST "https://rag.prateeq.in/v1/scaffold/apply" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_name": "quantum_random_oracle",
    "create_git_branch": false,
    "run_tests_immediately": true
  }' | jq .
```

### SOP-SCAFFOLD-04: Emergency Capability Rollback

If a newly applied capability triggers runtime exceptions:

```bash
curl -X POST "https://rag.prateeq.in/v1/scaffold/rollback" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_name": "quantum_random_oracle",
    "restore_backup": true
  }' | jq .
```

---

## 4. Incident Triage & Troubleshooting Matrix

| Error Message | Probable Root Cause | Remediation Action |
| :--- | :--- | :--- |
| **`422 Architecture Boundary Violation`** | Domain abstraction file attempted to import `fastapi`, `sqlalchemy`, or external SDK. | Strip framework imports; inject interfaces via Abstract Base Classes or Protocols. |
| **`400 AST Syntax Error`** | Malformed Python code produced by template formatting. | Inspect line syntax error returned in `validation_errors`; correct template strings. |
| **`500 Hot-Reload Loop / Crash`** | New router registered duplicate FastAPI path. | Run `SOP-SCAFFOLD-04` immediately to restore previous clean snapshot. |

---

## 5. Automated Verification

Verify metaprogramming AST generation and architecture boundaries:

```bash
pytest apps/api/tests/test_scaffold.py -v
```
