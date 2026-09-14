---
id: Retriever_API_v1_connectors
title: "API Specification: Enterprise Community Connectors & CDC Pipeline (/v1/admin/connectors, /v1/admin/tenants/{tenantId}/connectors)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/connectors
  - cdc/database
  - ingestion/sources
  - platform/retriever
blast_radius: HIGH
security_auth: ADMIN_KEY
invariants:
  - "Connector credentials MUST be encrypted using AES-256 before persistence."
  - "Incremental sync operations MUST advance monotonic cursors without re-ingesting unmodified records."
  - "All connector executions MUST strictly enforce tenant_id isolation."
---

# API Specification: Community Connectors & CDC Pipeline (`/v1/admin/connectors`)

#api #connectors #cdc #database #s3 #slack #github #retriever

> **Authoritative REST API specification for connector manifest introspection, tenant data source lifecycle, and incremental high-watermark synchronization (Platform Battery #27).**

---

## 1. Overview

The Community Connectors API manages continuous data replication from external business systems into Retriever's multi-tenant vector and keyword indexes:
- **Relational Databases (PostgreSQL / MySQL):** Chronological high-watermark CDC (`DatabaseCdcConnector`).
- **Cloud Object Storage (S3 / R2 / GCS / MinIO):** ETag differential auto-indexing (`S3StorageConnector`).
- **Developer & Workspace Tools:** GitHub repository docs & issues (`GitHubConnector`), Slack channel discussions (`SlackConnector`).

```text
  [ Admin / Synchronizer ]                               [ Retriever Connectors Engine ]
             │                                                         │
             │ 1. GET /v1/admin/connectors/manifests                   │
             ├────────────────────────────────────────────────────────►│ (Return descriptor schemas)
             │◄────────────────────────────────────────────────────────┤
             │                                                         │
             │ 2. POST /v1/admin/tenants/{id}/connectors               │
             │    { "type": "database_cdc", "config": { ... } }        │
             ├────────────────────────────────────────────────────────►│ (Store encrypted config)
             │◄────────────────────────────────────────────────────────┤
             │                                                         │
             │ 3. POST /v1/admin/tenants/{id}/connectors/{cId}/sync    │
             ├────────────────────────────────────────────────────────►│ (Run incremental sync)
             │◄────────────────────────────────────────────────────────┤
             │    { "documents_ingested": 42, "watermark": "..." }     │
```

---

## 2. Endpoints

### 2.1 List Available Connector Manifests
* **Endpoint:** `GET /v1/admin/connectors/manifests`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Returns the catalog of registered connector types and their parameter schemas.
* **Response (200 OK):**
```json
[
  {
    "type": "database_cdc",
    "name": "Relational Database CDC",
    "description": "High-watermark chronological replication for PostgreSQL and MySQL.",
    "version": "1.0.0",
    "author": "Retriever Core Team",
    "supported_features": ["incremental_sync", "soft_delete", "custom_sql"],
    "parameter_schema": {
      "database_url": {"type": "string", "required": true, "secret": true},
      "table_name": {"type": "string", "required": true},
      "watermark_column": {"type": "string", "default": "updated_at"},
      "batch_size": {"type": "integer", "default": 500}
    }
  },
  {
    "type": "s3",
    "name": "Cloud Object Storage Watcher",
    "description": "Auto-indexes new/modified documents from S3-compatible buckets.",
    "version": "1.0.0",
    "author": "Retriever Core Team",
    "supported_features": ["etag_diffing", "prefix_filter", "multi_cloud"],
    "parameter_schema": {
      "bucket_name": {"type": "string", "required": true},
      "endpoint_url": {"type": "string", "required": false},
      "prefix": {"type": "string", "default": ""},
      "allowed_extensions": {"type": "array", "default": [".pdf", ".md", ".txt"]}
    }
  }
]
```

---

### 2.2 List Tenant Connectors
* **Endpoint:** `GET /v1/admin/tenants/{tenantId}/connectors`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Response (200 OK):**
```json
[
  {
    "connector_id": "conn_pg_customers",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "type": "database_cdc",
    "name": "Production Customers CDC",
    "sync_state": {
      "watermark": "2026-09-14T22:00:00Z",
      "cursor": "10500",
      "last_sync_at": "2026-09-15T01:30:00Z"
    },
    "created_at": "2026-09-14T08:00:00Z"
  }
]
```

---

### 2.3 Create Tenant Connector
* **Endpoint:** `POST /v1/admin/tenants/{tenantId}/connectors`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Request Body:**
```json
{
  "name": "Engineering GitHub Docs",
  "type": "github",
  "config": {
    "repo": "prat3010/retriever",
    "branch": "main",
    "path": "docs",
    "sync_issues": true,
    "github_token": "ghp_..."
  }
}
```
* **Response (201 Created):**
```json
{
  "connector_id": "conn_gh_eng",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "type": "github",
  "name": "Engineering GitHub Docs",
  "status": "CONFIGURED"
}
```

---

### 2.4 Trigger Connector Synchronization
* **Endpoint:** `POST /v1/admin/tenants/{tenantId}/connectors/{connectorId}/sync`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Request Body:**
```json
{
  "mode": "incremental"
}
```
* **Response (200 OK):**
```json
{
  "status": "COMPLETED",
  "documents_ingested": 18,
  "chunks_created": 74,
  "duration_ms": 1420.5,
  "previous_watermark": "2026-09-14T12:00:00Z",
  "new_watermark": "2026-09-15T02:00:00Z"
}
```
