# Strix AI Penetration Testing Specification (`retriever`)

## Overview

[Strix](https://github.com/usestrix/strix) (`usestrix/strix`) is an open-source, autonomous AI penetration testing framework. In the **Retriever** codebase, Strix is deployed to dynamically evaluate API endpoints, multi-tenant isolation boundaries, and prompt injection resilience.

---

## Architecture & Target Scope

Strix executes AI security agents inside Docker containers and targets:
1. **OpenAPI Specification**: Automatically generated from FastAPI via [`generate_openapi.py`](../apps/api/scripts/generate_openapi.py) and output to [`docs/openapi.json`](openapi.json).
2. **Source Code**: Static analysis of Python FastAPI routes under [`apps/api/src`](../apps/api/src).
3. **Local API Server**: Dynamic HTTP scanning against `http://localhost:8000`.

```
                    ┌──────────────────────────────────────────┐
                    │      Strix AI Penetration Agent          │
                    │       (Docker Sandbox Container)         │
                    └────────────────────┬─────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      ┌──────────────────────────┐               ┌──────────────────────────┐
      │   OpenAPI & Source Code  │               │   Local FastAPI Server   │
      ├──────────────────────────┤               ├──────────────────────────┤
      │ • docs/openapi.json      │               │ • http://localhost:8000  │
      │ • apps/api/src/          │               │ • Tenant Isolation       │
      └──────────────────────────┘               └──────────────────────────┘
```

---

## Key Security Assertions Verified by Strix

* **Multi-Tenant Isolation**: Ensures all database queries, vector searches, and document store endpoints strictly enforce `tenant_id` boundaries.
* **Authentication & Authorization**: Validates API key enforcement, bearer tokens, and administrative endpoints.
* **Injection Resilience**: Tests for SQL injection, vector index manipulation, and prompt injection vulnerabilities in RAG context building.
* **IDOR & Broken Object Level Authorization**: Verifies that resources owned by `tenant_A` cannot be read, modified, or deleted by `tenant_B`.

---

## How to Run Security Audits

### 1. Execute Strix Audit Script
```bash
python3 apps/api/scripts/security_audit_strix.py --mode quick
```

### 2. Deep Audit Mode (with Spend Limit)
```bash
export OPENROUTER_API_KEY="your_openrouter_key"
python3 apps/api/scripts/security_audit_strix.py --mode deep --max-budget 5.0
```

---

## Artifacts & Reporting

Audit runs, trace logs, and validated exploit proof-of-concepts (PoCs) are saved under `./strix_runs/` for developer review and remediation.
