---
id: Retriever_API_v1_workflow
title: "API Specification: n8n Workflow Automation & Webhooks (/v1/workflow)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/workflow
  - integrations/n8n
  - webhooks
  - platform/retriever
blast_radius: HIGH
security_auth: BEARER_JWT
invariants:
  - "Inbound workflow webhooks MUST enforce rate limits and validate HMAC shared secret tokens."
---

# API Specification: n8n Workflow Automation & Webhooks (`/v1/workflow`)

#api #workflow #n8n #automation #webhooks #retriever

> **Authoritative specification for n8n workflow integration, auto-ingest webhooks, event triggers, and OpenAPI 3.0 schema exports.**

---

## 1. Workflow Automation Flow

```mermaid
sequenceDiagram
    autonumber
    participant n8n as n8n Automated Node
    participant Router as Workflow Router (/v1/workflow)
    participant Celery as Async Ingestion Queue
    participant DB as PostgreSQL 16
    n8n->>Router: POST /v1/workflow/n8n/webhook (Document Stream)
    Router->>Router: Validate Tenant Secret Token
    Router->>Celery: Queue Document Ingestion Pipeline
    Router-->>n8n: 202 Accepted (jobId)
    Celery->>DB: Ingestion Complete & Vector Indexed
    Celery->>n8n: POST Outbound Webhook (Event: "document.ready")
```

---

## 2. API Endpoints

### 2.1 Inbound n8n Auto-Ingest Webhook

- **HTTP Method:** `POST`
- **Path:** `/v1/workflow/n8n/webhook`
- **Headers:** `X-Tenant-Key: <SECRET_KEY>`
- **Request Body:**
```json
{
  "tenantId": "c9a28c30-e34d-4871-bc01-e9451d6c8b09",
  "source": "gmail",
  "documentUrl": "https://drive.google.com/uc?id=...",
  "filename": "Client_Invoice_July.pdf"
}
```

#### Response Schema (`202 Accepted`)
```json
{
  "status": "queued",
  "jobId": "job_98127391823",
  "tenantId": "c9a28c30-e34d-4871-bc01-e9451d6c8b09"
}
```

---

## 🔗 Related Architecture & Cross-References
- [n8n Workflow Integration Guide](../integrations/n8n_workflow_integration.md)
- [Document Ingestion Pipeline](document.md)
