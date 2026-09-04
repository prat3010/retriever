# Operational Runbook: NeMo Guardrails & Safety Management

**Runbook ID:** RB-OPS-094  
**Audience:** Platform SREs, Solutions Engineers, and System Administrators  
**Applies to:** Retriever AI Engine (v0.79.0+)  

---

## 1. Routine Verification & Health Checks

### 1.1 Verify Platform Battery Status
Check that Battery #13 (`nemo_conversational_guardrails`) is active and registered:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/guardrails/overview | jq .
```

**Expected Output:**
```json
{
  "engine": "NVIDIA NeMo Guardrails (Colang Runtime)",
  "version": "v0.79.0 (Milestone 94)",
  "battery_status": "active",
  "fast_path_latency": "<20ms",
  "grounding_latency": "~80ms"
}
```

---

## 2. Tenant Onboarding & Policy Tuning

### 2.1 Applying a Standard Colang Template
To set up a new tenant with the **Enterprise Customer Support** rails:

1. **Via Retriever Master Admin Dashboard ([`admin.rag.prateeq.in/guardrails`](https://admin.rag.prateeq.in/guardrails)):**
   - Select the target tenant from the top tenant picker.
   - Under **Colang Flow Specifications**, choose **Enterprise Customer Support** from the template dropdown.
   - Adjust PII Redaction, Competitor Shielding, and Grounding Threshold.
   - Click **Save Guardrails**.
2. **Via Client SaaS Studio ([`prateeq.in/rag/app`](https://prateeq.in/rag/app)):**
   - Navigate to the **NeMo Guardrails** panel.
   - Select preset template or edit rules.
   - Click **Save Policy Config**.
3. **Via Admin REST API:**
```bash
curl -X PUT https://rag.prateeq.in/v1/tenants/$TENANT_ID/guardrails/config \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "full_conversational",
    "competitor_shield_enabled": true,
    "competitor_names": ["pinecone", "weaviate", "qdrant"],
    "grounding_threshold": 0.70
  }'
```

---

## 3. Troubleshooting & Incident Response

### 3.1 Investigating False-Positive Blocks
* **Symptom:** A developer or legitimate user receives:
  `HTTP 400 Bad Request: Security check triggered: Prompt injection pattern detected.`
* **Root Cause Diagnosis:**
  1. Fetch tenant telemetry:
     ```bash
     curl -s https://rag.prateeq.in/v1/tenants/$TENANT_ID/guardrails/telemetry | jq .recent_violations
     ```
  2. Inspect the `query_excerpt` and `matched_flow_or_rule`.
  3. If the query was a technical prompt (e.g., describing SQL injection defenses or shell scripting), switch the tenant's Colang template to `developer_assistant` or update mode to `fast_input_only`.

### 3.2 High Latency on Chat Requests
* **Symptom:** RAG chat response latency increases by $>100ms$.
* **Diagnostic Procedure:**
  1. Check if the tenant is running in `strict_factual` mode. In `strict_factual` mode, output grounding verifies token containment across all retrieved chunks.
  2. If the tenant's chunk size is very large ($>2000$ tokens) or retrieved top-k is high ($>10$), relax `grounding_threshold` or switch mode to `full_conversational`.
  3. Check the average rail latency reported in telemetry:
     ```bash
     curl -s https://rag.prateeq.in/v1/tenants/$TENANT_ID/guardrails/telemetry | jq .average_rail_latency_ms
     ```

### 3.3 Mitigating an Active Jailbreak Campaign
* **Symptom:** A burst of hostile prompt-injection attempts is flagged in telemetry.
* **Remediation:**
  1. Fast-path input rail automatically blocks requests with HTTP 400 without consuming upstream LLM tokens.
  2. If an emerging injection pattern bypasses standard rules, add a new flow directly to the tenant's Colang script:
     ```colang
     define user attempt new exploit
       "emerging exploit keyword"

     define flow new exploit defense
       user attempt new exploit
       bot refuse unsafe
     ```
  3. Click **Save Policy Config**. Changes take effect instantly without restarting the server.
