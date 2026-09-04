# Durable Asynchronous Workflows & Jobs REST API Specification

**Version:** 1.0 (Milestone 95 / v0.80.0)  
**Base Path:** `/v1`  
**Authentication:** Standard Tenant API Key (`X-API-Key`) or Admin Master Key (`X-Admin-Master-Key`).  
**Platform Battery:** Battery #15 (`durable_workflow_engine`) under `BACKGROUND_WORKFLOWS`.

---

## Overview

The Durable Workflows API provides deterministic, fault-tolerant background execution for multi-stage AI batch operations. Every workflow execution maintains step-level checkpoints in PostgreSQL with memoized output payloads, enabling resilient automatic retries, zero-duplicate execution idempotency, and crash recovery.

---

## Endpoints

### 1. List Pre-Packaged Workflow Blueprints

Retrieve all registered workflow blueprints available for execution within the tenant.

```http
GET /v1/tenants/{tenant_id}/workflows/blueprints
```

#### Response (`200 OK`):

```json
[
  {
    "name": "vault_bulk_ingest",
    "title": "Vault Bulk Ingest & Chunk Pipeline",
    "description": "Ingest multi-file markdown/PDF vaults, extract text chunks, compute nomic-embed-text embeddings, and index into pgvector.",
    "trigger_event": "vault.uploaded",
    "concurrency_limit": 2,
    "max_step_retries": 3,
    "backoff_factor": 2.0,
    "initial_interval_seconds": 1.0,
    "steps": [
      {
        "name": "scan_documents",
        "description": "Scan and checksum vault documents",
        "max_attempts": 3,
        "timeout_seconds": 60
      },
      {
        "name": "chunk_and_embed",
        "description": "Split text into semantic chunks and compute embeddings",
        "max_attempts": 3,
        "timeout_seconds": 180
      },
      {
        "name": "index_vectors",
        "description": "Persist chunks to PostgreSQL pgvector table",
        "max_attempts": 3,
        "timeout_seconds": 120
      }
    ]
  }
]
```

---

### 2. Trigger Workflow Execution

Trigger a new workflow run or return an existing execution if `idempotency_key` matches.

```http
POST /v1/tenants/{tenant_id}/workflows/{workflow_name}/run
Content-Type: application/json
```

#### Request Body:

```json
{
  "input_payload": {
    "vault_path": "documents/enterprise_knowledge",
    "batch_size": 25
  },
  "idempotency_key": "ingest_vault_2026_09_04_abc",
  "webhook_url": "https://api.prateeq.in/api/rag/workflow-webhook"
}
```

#### Response (`200 OK` or `202 Accepted`):

```json
{
  "execution_id": "exec_40f4d352-78d1-43ef-b31a-9eebe34ea475",
  "tenant_id": "tn_test_client",
  "workflow_name": "vault_bulk_ingest",
  "status": "queued",
  "trigger_event": "manual",
  "idempotency_key": "ingest_vault_2026_09_04_abc",
  "input_payload": {
    "vault_path": "documents/enterprise_knowledge",
    "batch_size": 25
  },
  "output_payload": {},
  "total_steps": 3,
  "completed_steps": 0,
  "current_step_name": "scan_documents",
  "error_message": null,
  "step_history": [],
  "webhook_url": "https://api.prateeq.in/api/rag/workflow-webhook",
  "started_at": "2026-09-04T19:30:00Z",
  "completed_at": null
}
```

---

### 3. List Tenant Workflow Executions

List historical and currently running workflow executions for the tenant.

```http
GET /v1/tenants/{tenant_id}/workflows/executions?limit=50&offset=0&status=running
```

#### Query Parameters:
- `limit` (integer, default 50, max 200)
- `offset` (integer, default 0)
- `status` (string, optional: `queued`, `running`, `completed`, `failed`, `cancelled`)

#### Response (`200 OK`):

```json
{
  "items": [
    {
      "execution_id": "exec_40f4d352-78d1-43ef-b31a-9eebe34ea475",
      "tenant_id": "tn_test_client",
      "workflow_name": "vault_bulk_ingest",
      "status": "completed",
      "total_steps": 3,
      "completed_steps": 3,
      "current_step_name": null,
      "started_at": "2026-09-04T19:30:00Z",
      "completed_at": "2026-09-04T19:30:14Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### 4. Get Execution Details & Step DAG Checkpoints

Retrieve full execution status and all intermediate step checkpoints.

```http
GET /v1/tenants/{tenant_id}/workflows/executions/{execution_id}
```

#### Response (`200 OK`):

```json
{
  "execution_id": "exec_40f4d352-78d1-43ef-b31a-9eebe34ea475",
  "tenant_id": "tn_test_client",
  "workflow_name": "vault_bulk_ingest",
  "status": "completed",
  "total_steps": 3,
  "completed_steps": 3,
  "output_payload": {
    "total_indexed": 128,
    "execution_summary": "All 3 steps executed successfully."
  },
  "step_history": [
    {
      "step_id": "chk_scan_documents_0",
      "execution_id": "exec_40f4d352-78d1-43ef-b31a-9eebe34ea475",
      "step_name": "scan_documents",
      "step_index": 0,
      "status": "completed",
      "attempts": 1,
      "max_attempts": 3,
      "memoized_output": {
        "files_scanned": 12,
        "valid_checksums": 12
      },
      "execution_time_ms": 145.2,
      "started_at": "2026-09-04T19:30:00Z",
      "completed_at": "2026-09-04T19:30:00.145Z"
    }
  ]
}
```

---

### 5. Resume / Retry Execution from Checkpoint

Resume a `failed` or `cancelled` execution from the last successfully completed step.

```http
POST /v1/tenants/{tenant_id}/workflows/executions/{execution_id}/retry
```

#### Response (`200 OK`):

Returns the updated `WorkflowExecution` transitioning back to `running` with memoized steps preserved.

---

### 6. Cancel In-Flight Execution

Safely cancel an execution in `queued` or `running` state.

```http
POST /v1/tenants/{tenant_id}/workflows/executions/{execution_id}/cancel
```

#### Response (`200 OK`):

Returns the updated `WorkflowExecution` marked as `cancelled`.

---

### 7. Trigger Workflow by Event

Submit an event to trigger any workflows configured with a matching `trigger_event`.

```http
POST /v1/tenants/{tenant_id}/workflows/events
Content-Type: application/json
```

#### Request Body:

```json
{
  "event_name": "vault.uploaded",
  "payload": {
    "vault_path": "uploads/client_q3_docs.zip"
  }
}
```

---

### 8. Admin Engine Overview

System-wide diagnostic inspection of engine status and blueprint registry (Admin Master Key required).

```http
GET /v1/admin/workflows/overview
Header: X-Admin-Master-Key: <ADMIN_MASTER_KEY>
```

#### Response (`200 OK`):

```json
{
  "total_blueprints": 4,
  "blueprints": [ ... ],
  "engine_status": "active",
  "checkpoint_backend": "postgresql_rls"
}
```
