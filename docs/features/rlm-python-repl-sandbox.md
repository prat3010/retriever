# Recursive Language Model (RLM) Python REPL Execution Sandbox

**Milestone:** M48 / M56 (v0.45.0)  
**System Layer:** Sandboxed Code Execution & Deterministic Computation (Platform Battery #5)  
**Architecture:** Restricted Python AST Visitor + Process Resource Limits + Pure Whitelist Built-in Environment + Interactive REPL Studio  

---

## 1. Executive Summary

Milestone 48 and 56 establish **Platform Battery #5: `rlm_python_repl`**, equipping Retriever with on-the-fly deterministic computation capabilities.

Large Language Models struggle with precise multi-step arithmetic, cumulative tax calculations, floating-point rounding, and dynamic aggregations over large tabular datasets. Prompting an LLM to "calculate total interest compounded quarterly over 7 years" frequently yields hallucinated digits and unreliable financial ledgers.

Platform Battery #5 implements a Recursive Language Model (RLM) pattern:
1. The model formulates its reasoning chain and emits executable Python code snippets.
2. The RLM execution sandbox intercepts the snippet, inspects the Abstract Syntax Tree (AST) against strict security policies, and executes it in a sandboxed runtime.
3. The deterministic outputs and stdout logs are fed back into the context window as verified ground-truth observations.

---

## 2. Security Sandbox Architecture & AST Inspection

To guarantee zero remote code execution (RCE) vulnerabilities in a multi-tenant environment, the execution engine validates every line of code prior to compilation using Python's standard `ast` module.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        RLM AST VERIFICATION & EXECUTION ENGINE                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Generated Code Snippet ]                                                           │
│                │                                                                       │
│                ▼                                                                       │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 1. ast.parse() Abstract Syntax Tree Traversal                            │         │
│   │    - Rejects Import, ImportFrom (no os, sys, subprocess, socket)         │         │
│   │    - Rejects Exec, Eval, Compile, getattr, setattr, globals, locals      │         │
│   │    - Rejects File I/O operations (open, read, write)                     │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │ (Passes Security Verification)                │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 2. Isolated Built-in Sandbox Construction                                │         │
│   │    - Allowed built-ins: len, sum, min, max, abs, round, enumerate, zip   │         │
│   │    - Allowed safe libraries: math, statistics, datetime, json            │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 3. Time-Limited Execution Thread (resource.setrlimit / timeout=5s)       │         │
│   │    - Caps CPU time and memory allocation (<50MB)                         │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ Output: Deterministic Results + Intercepted Stdout / Return Values       │         │
│   └──────────────────────────────────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Use Cases

1. **Deterministic CPQ Pricing Calculations:** Calculates multi-item package pricing, tiered volume discounts, and sales commissions with exact rupee/dollar rounding.
2. **Tabular Data Filtering:** Performs SQL-like group-by, mean, and standard deviation calculations over retrieved document tables.
3. **Interactive REPL Studio:** Tenants can test and prototype mathematical subroutines directly inside `/rag/app` under the RLM Studio panel.

---

## 4. Implementation Details

- **Core Module:** `apps/api/src/domain/rlm/sandbox.py`
- **FastAPI Router:** `apps/api/src/routers/rlm.py`
- **Latency Profile:** $\sim 18\text{ms}$ execution latency for standard algorithmic workloads.
- **Resource Constraints:** Strict 5-second execution timeout; 50MB RAM limit per process execution.
- **Health Check Endpoint:** `GET /v1/rlm/sandbox/health`

---

## 5. Non-Negotiable Invariants

1. **Zero External I/O:** Any code attempting socket connections, filesystem access, or environment variable inspection immediately triggers `SecurityViolationError` and terminates the execution.
2. **Infinite Loop Protection:** CPU time limits prevent `while True` denial-of-service attempts from locking up server threads.
3. **Stateless Execution:** State does not persist between distinct execution requests; each run begins in a freshly initialized sandbox namespace.
