# Operational Runbook: Durable Asynchronous Workflows & Jobs

**Runbook ID:** RB-OPS-095  
**Audience:** Platform SREs, Solutions Engineers, and System Administrators  
**Applies to:** Retriever AI Engine (v0.80.0+)  

---

## 1. Health Checks & Battery Verification

### 1.1 Verify Platform Battery Status
Confirm that Battery #15 (`durable_workflow_engine`) is active:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/admin/workflows/overview | jq .
```

**Expected Output:**
```json
{
  "total_blueprints": 4,
  "engine_status": "active",
  "checkpoint_backend": "postgresql_rls"
}
```

---

## 2. Managing Workflow Executions

### 2.1 Inspecting Active Jobs
List all currently running jobs across the cluster:

```bash
curl -s -H "X-API-Key: $TENANT_API_KEY" \
  "https://rag.prateeq.in/v1/tenants/$TENANT_ID/workflows/executions?status=running" | jq .
```

### 2.2 Resuming a Failed Execution from Checkpoint
When an execution fails (e.g. due to temporary network failure or upstream model rate limits):

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/$TENANT_ID/workflows/executions/$EXEC_ID/retry" \
  -H "X-API-Key: $TENANT_API_KEY" | jq .
```

The runner automatically skips previously completed steps using their memoized output and restarts from the failing step.

### 2.3 Cancelling a Runaway Job
If a pipeline is queued or running and needs to be stopped immediately:

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/$TENANT_ID/workflows/executions/$EXEC_ID/cancel" \
  -H "X-API-Key: $TENANT_API_KEY" | jq .
```

---

## 3. Webhook Delivery & HMAC Verification

When configuring webhooks for asynchronous notification:
1. Deliveries include the signature header:
   ```http
   X-Workflow-Signature-256: sha256=<hex_digest>
   ```
2. Compute the HMAC in Node.js / Python:
   ```javascript
   const crypto = require('crypto');
   const signature = 'sha256=' + crypto.createHmac('sha256', SECRET).update(rawBody).digest('hex');
   ```

---

## 4. Troubleshooting & Maintenance

### 4.1 Stuck `running` Status after Server Crash
If the backend process was hard-killed (e.g. `kill -9` or OOM killer) and an execution is stuck in `running`:
- The client or admin can invoke the `/retry` endpoint to re-arm the execution.
- If the execution is no longer desired, call `/cancel`.

### 4.2 Pruning Stale Checkpoints
Checkpoints older than 90 days can be archived or cleaned using standard PostgreSQL queries:
```sql
DELETE FROM workflow_step_checkpoints
WHERE created_at < NOW() - INTERVAL '90 days';
```
