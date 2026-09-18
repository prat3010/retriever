# Operational Runbook: Community Connectors & Change-Data-Capture (CDC) Operations

**Runbook ID:** RB-OPS-111  
**Audience:** Data Platform Engineers, Integration SREs, and Tenant Administrators  
**Applies to:** Retriever Data Pipeline (`v1.1.0-alpha1`+, Milestone 111)  

---

## 1. Health Checks & Battery Verification

### 1.1 Verify Platform Battery Status
Confirm that Battery #27 (`cdc_community_connectors`) is operational:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  http://localhost:8000/v1/admin/platform/batteries | jq '.batteries[] | select(.id == "cdc_community_connectors")'
```

### 1.2 Inspect Registered Connector Types
```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  http://localhost:8000/v1/admin/connectors/manifests | jq '.[].name'
```

---

## 2. Common Incident Triage & Troubleshooting

### 2.1 Database CDC Watermark Lag / Missing Records
**Symptoms:**
- Recently mutated records in PostgreSQL/MySQL do not appear in search results.
- `last_sync_at` timestamp is stale.

**Diagnostic Steps:**
1. Check tenant connector status:
   ```bash
   curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     http://localhost:8000/v1/admin/tenants/{tenantId}/connectors | jq .
   ```
2. Verify target table indexing: Ensure `updated_at` (or configured watermark column) has a B-tree index in the upstream database:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_customers_updated_at ON customers (updated_at);
   ```
3. Test connectivity and run manual sync:
   ```bash
   curl -X POST http://localhost:8000/v1/admin/tenants/{tenantId}/connectors/{connectorId}/sync \
     -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"mode": "incremental"}' | jq .
   ```

---

### 2.2 Cloud Object Storage ETag Desync / Re-indexing
**Symptoms:**
- Changed documents in S3/R2 are not re-indexed because ETag metadata was corrupted or reset.

**Remediation:**
Trigger a forced full re-sync (bypassing the ETag cache):
```bash
curl -X POST http://localhost:8000/v1/admin/tenants/{tenantId}/connectors/{connectorId}/sync \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "full"}' | jq .
```

---

### 2.3 Upstream API Rate Limiting (GitHub / Slack HTTP 429)
**Symptoms:**
- Sync job fails with `RateLimitError` or HTTP 429 status code.

**Remediation:**
1. Inspect response headers for `x-ratelimit-reset` or `Retry-After`.
2. The connector implements exponential backoff up to 3 retries. If tenant credentials exceeded personal limits:
   - For GitHub: Provide an enterprise GitHub Personal Access Token (PAT) with 5,000 req/hr quota instead of unauthenticated (60 req/hr).
   - For Slack: Configure batch intervals $\ge 60\text{s}$ to respect Slack Tier 3/4 limits.

---

## 3. Resetting Connector Watermarks
To reset a connector to ingest all historical data from epoch:
```bash
curl -X PUT http://localhost:8000/v1/admin/tenants/{tenantId}/connectors/{connectorId}/reset \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" | jq .
```
