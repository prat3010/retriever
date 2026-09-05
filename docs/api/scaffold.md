---
id: Retriever_API_v1_scaffold
title: "API Specification: Autonomous FDE Metaprogrammer & Scaffolding Studio (/v1/scaffold)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/scaffold
  - metaprogrammer/ast
  - plugins/custom
  - platform/retriever
blast_radius: HIGH
security_auth: BEARER_JWT_OR_ADMIN
invariants:
  - "Domain files (abstractions.py, service.py) MUST NOT contain framework imports (fastapi, sqlalchemy, celery, redis)."
  - "Generated plugins MUST reside in isolated git-untracked directories (src/plugins/custom/{plugin_id}/)."
  - "Plugin hot-mounting MUST execute inside isolated try/except error boundaries."
---

# API Specification: Autonomous Metaprogrammer & Scaffolding Studio (`/v1/scaffold`)

#api #scaffold #ast #metaprogrammer #plugins #retriever

> **Authoritative REST API specification for dual-persona capability gap analysis, AST-verified Hexagonal code synthesis, in-process plugin hot-mounting, and automated GitHub PR generation (Platform Battery #17).**

---

## 1. Overview & Dual-Persona Execution Flow

The Scaffolding API serves two distinct user personas:
1. **Business Operators:** Submits plain-language requirements and receives zero-code platform battery recommendations.
2. **Forward Deployed Engineers (FDEs):** Triggers automated generation of full-stack Hexagonal code slices (`abstractions.py`, `service.py`, `adapter.py`, `router.py`, `test_plugin.py`), validates them against static AST boundary rules, and hot-mounts them into the running FastAPI app.

```text
  [ Client Request ] ──► POST /v1/scaffold/analyze
                               │
               ┌───────────────┴───────────────┐
               ▼ (Battery Match >= 85%)        ▼ (Custom Capability Gap)
       [ Zero-Code Guide ]             POST /v1/scaffold/generate
       (Active Batteries Recommended)          │
                                               ▼
                                       POST /v1/scaffold/verify (AST AST Inspector)
                                               │
                                               ▼ (0 Framework Imports in Domain)
                                       POST /v1/scaffold/apply
                                       (Write to disk & Safe In-Process Hot-Mount)
```

---

## 2. API Endpoints

### 2.1 Analyze Requirement & Gap Analysis
* **Endpoint:** `POST /v1/scaffold/analyze`
* **Request Body:**
```json
{
  "title": "HubSpot CRM Connector",
  "description": "Bi-directional customer ticket vectorization and deal attribution tracking",
  "persona": "business"
}
```
* **Response (200 OK):**
```json
{
  "persona": "business",
  "recommendations": [
    {
      "battery_id": "pgvector_hnsw_dense",
      "confidence": 0.92,
      "rationale": "Directly stores and queries customer deal vector embeddings."
    }
  ],
  "needs_custom_scaffold": true,
  "total_matched": 1
}
```

### 2.2 Synthesize Hexagonal Scaffolding Plan
* **Endpoint:** `POST /v1/scaffold/generate`
* **Request Body:** Same `UseCaseRequirement` structure as `/analyze`.
* **Response (200 OK):**
```json
{
  "plugin_id": "hubspot_crm_connector",
  "name": "HubSpot CRM Connector",
  "scaffolded_files": [
    {
      "relative_path": "abstractions.py",
      "layer": "domain",
      "code": "from pydantic import BaseModel\n\nclass HubspotDeal(BaseModel):\n    deal_id: str\n"
    },
    {
      "relative_path": "service.py",
      "layer": "domain",
      "code": "class HubspotService:\n    def __init__(self):\n        pass\n"
    },
    {
      "relative_path": "router.py",
      "layer": "router",
      "code": "from fastapi import APIRouter\nrouter = APIRouter(prefix='/v1/plugins/hubspot')\n"
    }
  ],
  "git_branch_name": "feat/plugin-hubspot-crm-connector",
  "pr_markdown_summary": "### Automated FDE Plugin: HubSpot CRM Connector\n\n..."
}
```

### 2.3 Verify AST Boundary Conformance
* **Endpoint:** `POST /v1/scaffold/verify`
* **Request Body:** Array of `ScaffoldedFile` objects.
* **Response (200 OK):**
```json
{
  "is_valid": true,
  "inspected_files_count": 3,
  "violations": [],
  "passed_rules": [
    "NO_FASTAPI_IN_DOMAIN",
    "NO_SQLALCHEMY_IN_DOMAIN",
    "NO_EXTERNAL_SDK_IN_DOMAIN"
  ]
}
```

### 2.4 Apply Plan & Hot-Mount Plugin
* **Endpoint:** `POST /v1/scaffold/apply`
* **Query Parameters:** `dry_run` (boolean, default: false).
* **Request Body:** Complete `ScaffoldingPlan` object.
* **Response (200 OK):**
```json
{
  "plugin_id": "hubspot_crm_connector",
  "files_written": 5,
  "target_directory": "src/plugins/custom/hubspot_crm_connector",
  "mounted_router_prefix": "/v1/plugins/hubspot",
  "hot_reload_status": "SUCCESS"
}
```

### 2.5 List Active Custom Plugins
* **Endpoint:** `GET /v1/scaffold/plugins`
* **Response (200 OK):** Returns array of active `CustomPluginSummary` records.
