---
id: Retriever_API_v1_admin
title: "API Specification: Master Admin Gateway & Control Plane (/v1/admin)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/admin
  - control-plane
  - security/rbac
  - platform/retriever
blast_radius: CRITICAL
security_auth: BEARER_JWT
invariants:
  - "Admin routes MUST strictly require role='admin' or role='owner' in JWT claims."
  - "Audit log entries MUST be generated for every mutation across tenant configs, prompts, and keys."
---

# API Specification: Master Admin Gateway & Control Plane (`/v1/admin`)

#api #admin #controlplane #tenancy #evaluation #prompts #retriever

> **Authoritative specification for the 12-domain master admin gateway covering tenants, users, API keys, prompt templates, A/B experiments, semantic cache management, GraphRAG inspection, and online evaluation testbeds.**

---

## 1. Admin Control Plane Matrix

The `/v1/admin` gateway serves as the centralized orchestration backend for multi-tenant administration:

```mermaid
graph TD
    Admin[Platform Admin / Operator] -->|Bearer Admin JWT| Gateway[/v1/admin Gateway]
    
    Gateway --> T[Tenants & Workspaces]
    Gateway --> K[API Key Lifecycle]
    Gateway --> P[Prompt Templates & A/B Experiments]
    Gateway --> C[Connectors & Sync Pipelines]
    Gateway --> S[Semantic Cache Purge & Metrics]
    Gateway --> G[GraphRAG Entity Inspector]
    Gateway --> E[Evaluation & Faithfulness Benchmarks]
    Gateway --> M[Self-Memory & Epistemic Stores]
```

---

## 2. Admin API Endpoints

### 2.1 List All Tenants & Workspace Health

- **HTTP Method:** `GET`
- **Path:** `/v1/admin/tenants`
- **Query Parameters:** `status` (`active`, `suspended`, `trial`), `limit`, `offset`
- **Response Schema (`200 OK`):**
```json
{
  "totalTenants": 14,
  "tenants": [
    {
      "tenantId": "c9a28c30-e34d-4871-bc01-e9451d6c8b09",
      "name": "Prateeq Scoping Lab",
      "slug": "prateeq_scoping",
      "plan": "enterprise",
      "documentCount": 142,
      "totalTokens": 892000,
      "status": "active",
      "createdAt": "2026-08-01T00:00:00Z"
    }
  ]
}
```

---

### 2.2 Purge Semantic Similarity Cache

Purges exact and cosine-similarity semantic caches for a tenant or globally.

- **HTTP Method:** `POST`
- **Path:** `/v1/admin/tenants/{tenantId}/semantic-cache/purge`
- **Request Body:**
```json
{
  "reason": "Knowledge base updated with new Q3 guidelines",
  "scope": "all"
}
```
- **Response Schema (`200 OK`):**
```json
{
  "status": "success",
  "purgedKeys": 412,
  "timestamp": "2026-08-25T05:37:00Z"
}
```

---

### 2.3 Inspect GraphRAG Entities & Triples

- **HTTP Method:** `GET`
- **Path:** `/v1/admin/tenants/{tenantId}/graph/entities`
- **Query Parameters:** `entity_type` (e.g. `PERSON`, `ORGANIZATION`, `TECH_STACK`), `limit`
- **Response Schema (`200 OK`):**
```json
{
  "tenantId": "c9a28c30-e34d-4871-bc01-e9451d6c8b09",
  "entityCount": 84,
  "entities": [
    {
      "entityId": "ent_01",
      "name": "Next.js 16",
      "type": "FRAMEWORK",
      "degree": 12,
      "linkedTriples": 18
    },
    {
      "entityId": "ent_02",
      "name": "Supabase pgvector",
      "type": "DATABASE",
      "degree": 8,
      "linkedTriples": 11
    }
  ]
}
```

---

## 3. Error Responses & Status Codes

| Status Code | Code | Reason / Description |
|:---|:---|:---|
| `401 Unauthorized` | `INVALID_AUTH` | Missing Bearer token or invalid admin credentials. |
| `403 Forbidden` | `ADMIN_ROLE_REQUIRED` | Authenticated user is not an administrator. |
| `404 Not Found` | `TENANT_NOT_FOUND` | Specified tenant ID does not exist. |

---

## 🔗 Related Architecture & Cross-References
- [Tenant Provisioning Specification](tenant.md)
- [GraphRAG Cognitive Deep-Dive](../cognitive/graphrag.md)
- [Evaluation & Hallucinations](../cognitive/evaluation_and_hallucinations.md)
