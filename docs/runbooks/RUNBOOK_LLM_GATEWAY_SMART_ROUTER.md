# Runbook: Enterprise LLM Gateway & Smart Router Operations

**Service:** Retriever Cognitive Engine & Inference Router  
**Milestone:** 93 (Phase L)  
**Version:** `v0.78.0`  
**Classification:** Inference Routing, Multi-Provider High-Availability & Budget Governance Runbook  

---

## 1. System Overview & Key Ports

The Enterprise LLM Gateway provides multi-model routing, automated failovers, circuit-breaker cooldowns, and virtual spending limits across upstream providers and local VPS models.

| Component | Path / Location | Purpose |
| :--- | :--- | :--- |
| **Domain Port** | `apps/api/src/domain/abstractions/gateway.py` | Abstract router & budget repository interfaces |
| **Router Adapter** | `apps/api/src/adapters/cognitive/gateway_router.py` | Multi-model dispatcher, fallback cascades & cooldown circuit |
| **Budget Repository** | `apps/api/src/adapters/database/budget_repository.py` | PostgreSQL aggregate spend queries & budget enforcement |
| **REST Router** | `apps/api/src/routers/gateway.py` | REST endpoints for catalog, probes, routes, and spend |
| **Admin Cockpit** | `apps/web/src/app/(dashboard)/gateway/page.tsx` | Visual cascade builder, live latency pings, budget limits |
| **SaaS Studio Panel** | `Prateek_website/src/components/rag/GatewayPanel.tsx` | Interactive client cockpit with dual-theme sensory parity |

---

## 2. Standard Operational Procedures

### A. Inspecting Live Provider Latency & Reachability
Execute a live probe across all configured upstream providers:
```bash
curl -X POST "https://rag.prateeq.in/v1/gateway/probe" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY"
```
**Expected Response:**
```json
[
  { "provider": "gemini", "target_model": "gemini-2.5-flash", "reachable": true, "latency_ms": 115 },
  { "provider": "openai", "target_model": "gpt-4o-mini", "reachable": true, "latency_ms": 220 },
  { "provider": "anthropic", "target_model": "claude-3-haiku", "reachable": true, "latency_ms": 315 },
  { "provider": "ollama", "target_model": "qwen2.5:14b", "reachable": true, "latency_ms": 40 }
]
```

### B. Configuring a Tenant Fallback Cascade & Budget Limits
To configure primary model Claude 3.5 Sonnet with GPT-4o Mini and local Ollama fallback, with a $100 monthly cap and automatic downgrade:
```bash
curl -X PUT "https://rag.prateeq.in/v1/tenants/{tenantId}/gateway/routes" \
  -H "Authorization: Bearer $TENANT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_model": "anthropic/claude-3-5-sonnet-20240620",
    "fallback_models": [
      "openai/gpt-4o-mini",
      "ollama/qwen2.5:14b"
    ],
    "latency_sla_ms": 3500,
    "cooldown_seconds": 60,
    "monthly_cost_budget": 100.0,
    "daily_cost_budget": 10.0,
    "hard_limit_action": "downgrade_free_model",
    "free_fallback_model": "ollama/qwen2.5:14b",
    "currency": "USD"
  }'
```

### C. Checking Current Tenant Spend & Cost Breakdown
```bash
curl -X GET "https://rag.prateeq.in/v1/tenants/{tenantId}/gateway/budget" \
  -H "Authorization: Bearer $TENANT_API_KEY"
```

---

## 3. Troubleshooting & Incident Response

### Incident 1: Upstream Provider 429 Rate Limit Wave
- **Symptom:** Logs show `Provider <provider> rate limited (429). Entering cooldown for 60s`.
- **System Action:** Router automatically trips circuit breaker for that provider and routes subsequent traffic to the next model in the fallback cascade.
- **Operator Verification:**
  1. Inspect `/v1/gateway/probe` to verify health.
  2. Check whether tenant's secondary models (e.g. `openai/gpt-4o-mini`) are picking up load without error.
  3. If rate limits persist, temporarily lower `latency_sla_ms` or elevate `cooldown_seconds` via the Admin Dashboard.

### Incident 2: Tenant Budget Ceiling Breached (HTTP 402)
- **Symptom:** Clients receive `402 Payment Required` with `BudgetExceededError`.
- **Root Cause:** Tenant has reached `monthly_cost_budget` and policy is set to `block`.
- **Resolution Options:**
  1. *Elevate Budget Ceiling:* Update tenant's `monthly_cost_budget` via PUT `/v1/tenants/{tenantId}/gateway/routes`.
  2. *Switch to Zero-Downtime Local Downgrade:* Set `hard_limit_action: "downgrade_free_model"`. The platform will instantly resume answering queries using the local VPS model (`ollama/qwen2.5:14b`) at zero API cost.

### Incident 3: Local Ollama Emergency Fallback Down
- **Symptom:** Probe indicates `provider: "ollama", reachable: false`.
- **Diagnosis:**
  SSH into Oracle Cloud VPS:
  ```bash
  ssh ubuntu@130.210.35.134
  systemctl status ollama
  ```
- **Remediation:**
  ```bash
  sudo systemctl restart ollama
  curl http://localhost:11434/api/tags
  ```
  Ensure local weights are loaded:
  ```bash
  ollama pull qwen2.5:14b
  ```

---

## 4. Disaster Recovery & Rollback

If gateway router behavior requires rollback to static provider mode:
1. Revert container dependency injection in `apps/api/src/container.py` to route directly via `ai_provider`.
2. Restart the API server:
   ```bash
   sudo systemctl restart retriever
   ```
3. Run verification test suite:
   ```bash
   uv run pytest apps/api/tests/test_gateway_router.py -v
   ```
