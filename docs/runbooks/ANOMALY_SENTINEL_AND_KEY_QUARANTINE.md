# Operational Runbook: Autonomous AI Anomaly Sentinel & Credential Abuse Guard

**Document Status:** Production-Ready  
**Milestone:** 83 (v0.68.0)  
**Target Audience:** SREs, Security Operations Center (SOC) Engineers & Platform Administrators  

---

## 1. Threat Landscape: Stolen API Keys & Silent Abuse

Static rate limit rules (e.g. 60 requests/min) are easily bypassed by sophisticated adversaries who intentionally throttle their attacks to 55 requests/min. Once an enterprise client's API key is leaked (e.g. committed to a public GitHub repository or stolen from an unencrypted client app), attackers silently scrape corporate document libraries or run automated fuzzing attacks.

The **Retriever Anomaly Sentinel (`apps/api/src/domain/telemetry/anomaly_detector.py`)** runs an unsupervised Machine Learning model in the background that continuously profiles behavioral patterns and **autonomously quarantines compromised credentials** within seconds of anomalous behavior.

---

## 2. Machine Learning Architecture: Scikit-Learn IsolationForest

The sentinel uses **Isolation Forests**, an unsupervised outlier detection algorithm well-suited for high-dimensional, non-stationary telemetry distributions:

```text
                  [Live Inference Telemetry Stream]
                                │
                                ▼
               ┌─────────────────────────────────┐
               │    Telemetry Window Aggregator   │
               │   (Sliding 60-Second Buffers)   │
               └────────────────┬────────────────┘
                                │
                 4-Dimensional Feature Vector:
                 [f_req, f_tokens, f_error, f_latency]
                                │
                                ▼
               ┌─────────────────────────────────┐
               │  Scikit-Learn Isolation Forest  │
               │ (n_estimators=100, contam=0.05) │
               └────────────────┬────────────────┘
                                │
                 Decision: Anomaly Score < -0.15?
                  ├── NO  ──> Baseline Normal (Pass)
                  └── YES ──> CRITICAL ANOMALY DETECTED!
                                │
                                ▼
               ┌─────────────────────────────────┐
               │   Autonomous Quarantine Action  │
               │  • Lock key in database         │
               │  • Emit Critical Security Alert │
               │  • Reject requests with 403     │
               └─────────────────────────────────┘
```

### Feature Vector Composition:
1. **`request_count_1m`:** Instantaneous request velocity.
2. **`token_throughput_1m`:** Cumulative prompt and completion tokens consumed.
3. **`error_rate_pct`:** Ratio of HTTP 4xx/5xx responses (detects automated parameter fuzzing and injection attempts).
4. **`latency_deviation_ms`:** Severe deviations from moving average response latency (detects complex algorithmic DoS queries).

---

## 3. Autonomous Quarantine Lifecycle

When an API key exhibits outlier behavior:
1. **Immediate Quarantine:** The sentinel updates the `api_keys` record:
   ```sql
   UPDATE api_keys 
   SET is_quarantined = TRUE, 
       quarantine_reason = 'Autonomous Sentinel: High anomaly score detected in 60s sliding window',
       quarantined_at = NOW()
   WHERE key_id = :key_id;
   ```
2. **Instant Rejection:** The authentication middleware immediately rejects subsequent requests:
   ```http
   HTTP/1.1 403 Forbidden
   Content-Type: application/json

   {
     "error": "CredentialQuarantined",
     "message": "This API key has been suspended due to anomalous usage patterns. Please contact your platform administrator."
   }
   ```
3. **High-Priority Alert Emitted:** An alert item is written to the platform alert repository for SRE review.

---

## 4. SRE Incident Response Procedure

When an Anomaly Alert fires, follow this 4-step checklist:

### Step 1: Inspect Active Alerts
```bash
curl -X GET "https://rag.prateeq.in/v1/admin/telemetry/alerts?status=active" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```
**Sample Alert:**
```json
{
  "alert_id": "alt_84920482",
  "tenant_id": "tn_client_4820a1",
  "key_id": "key_prod_app_39",
  "risk_level": "CRITICAL",
  "reason": "Anomaly score -0.32: Error rate surged to 88% with abnormal token velocity",
  "detected_at": "2026-09-04T03:22:10Z",
  "status": "active"
}
```

### Step 2: Audit Historical Telemetry Logs
Query recent requests for the flagged `key_id` to determine origin IPs, user agents, and requested documents:
```bash
curl -X GET "https://rag.prateeq.in/v1/admin/tenants/{tenantId}/logs?key_id={key_id}&limit=50" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```

### Step 3: Determine Resolution
- **If Compromised (e.g. unknown foreign IPs, brute-force search queries):**  
  Revoke the key permanently via `DELETE /v1/admin/tenants/{tenantId}/api-keys/{key_id}` and notify the client to rotate credentials.
- **If Legitimate False Positive (e.g. client running an approved batch backfill):**  
  Proceed to Step 4 to restore the key.

### Step 4: Unquarantine Key (Restoration)
```bash
curl -X POST "https://rag.prateeq.in/v1/admin/api-keys/{key_id}/unquarantine" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```
**Response:**
```json
{
  "status": "success",
  "key_id": "key_prod_app_39",
  "active": true
}
```
The key is immediately restored to active rotation without restarting the server.

---

## 5. Testing & Verification

Administrators can test the Anomaly Sentinel pipeline without triggering real attacks by running the automated pytest suite:
```bash
uv run --project apps/api pytest apps/api/tests/test_anomaly_detector.py apps/api/tests/test_anomaly_sentinel_service.py -v
```
To emit a test alert via API:
```bash
curl -X POST "https://rag.prateeq.in/v1/admin/telemetry/test-alert" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"risk_level": "HIGH", "reason": "Manual SRE Fire Drill Test"}'
```
