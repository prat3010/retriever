# REST API Reference: Enterprise LLM Gateway & Smart Router

**Base Paths:**
- Public Gateway Catalog & Probes: `/v1/gateway`
- Tenant Gateway Routing & Budget: `/v1/tenants/{tenantId}/gateway`

**Authentication:**
- Master Administration: `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
- Tenant Session / API Key: `Authorization: Bearer <API_KEY_OR_JWT>`
- **Milestone:** 93 (Phase L)  
- **Version:** `v0.78.0`

---

## Overview

The Enterprise LLM Gateway & Smart Router exposes unified control planes for dynamic multi-provider routing (OpenAI, Anthropic, Gemini, Groq, Mistral, and local Ollama), dynamic fallback cascades, circuit-breaker cooldowns, and virtual tenant spending ledgers.

---

## Endpoints

### 1. List Supported Gateway Models

Returns the catalog of upstream and local models supported by the gateway, including real-time pricing per 1k tokens, capabilities, and health status.

- **Method:** `GET`
- **Path:** `/v1/gateway/models`
- **Headers:** None (Public / Authenticated)
- **Response (`200 OK`):**
  ```json
  [
    {
      "model_id": "gemini-2.5-flash",
      "provider": "gemini",
      "name": "Google Gemini 2.5 Flash",
      "input_cost_per_1k": 0.075,
      "output_cost_per_1k": 0.30,
      "capabilities": ["chat", "vision", "tools", "json"],
      "is_local": false,
      "health_status": "healthy",
      "latency_ms": 115,
      "description": "High-speed multimodal baseline with sub-second time-to-first-token."
    },
    {
      "model_id": "openai/gpt-4o-mini",
      "provider": "openai",
      "name": "OpenAI GPT-4o Mini",
      "input_cost_per_1k": 0.15,
      "output_cost_per_1k": 0.60,
      "capabilities": ["chat", "tools", "json"],
      "is_local": false,
      "health_status": "healthy",
      "latency_ms": 220,
      "description": "Cost-efficient secondary fallback for structured generation."
    },
    {
      "model_id": "anthropic/claude-3-5-sonnet-20240620",
      "provider": "anthropic",
      "name": "Anthropic Claude 3.5 Sonnet",
      "input_cost_per_1k": 3.00,
      "output_cost_per_1k": 15.00,
      "capabilities": ["chat", "vision", "tools"],
      "is_local": false,
      "health_status": "healthy",
      "latency_ms": 320,
      "description": "High-reasoning tier for complex synthesis and code evaluation."
    },
    {
      "model_id": "ollama/qwen2.5:14b",
      "provider": "ollama",
      "name": "Ollama Qwen 2.5 14B (Local)",
      "input_cost_per_1k": 0.0,
      "output_cost_per_1k": 0.0,
      "capabilities": ["chat", "tools"],
      "is_local": true,
      "health_status": "healthy",
      "latency_ms": 40,
      "description": "Local zero-cost emergency fallback running on VPS hardware."
    }
  ]
  ```

---

### 2. Upstream Provider Connectivity & Latency Probe

Executes concurrent, live reachability and latency benchmarks against configured upstream provider endpoints.

- **Method:** `POST`
- **Path:** `/v1/gateway/probe`
- **Headers:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>` or `Authorization: Bearer <TOKEN>`
- **Response (`200 OK`):**
  ```json
  [
    {
      "provider": "gemini",
      "target_model": "gemini-2.5-flash",
      "reachable": true,
      "latency_ms": 118,
      "error_message": null
    },
    {
      "provider": "openai",
      "target_model": "gpt-4o-mini",
      "reachable": true,
      "latency_ms": 225,
      "error_message": null
    },
    {
      "provider": "anthropic",
      "target_model": "claude-3-haiku",
      "reachable": true,
      "latency_ms": 310,
      "error_message": null
    },
    {
      "provider": "ollama",
      "target_model": "qwen2.5:14b",
      "reachable": true,
      "latency_ms": 42,
      "error_message": null
    }
  ]
  ```

---

### 3. Get Tenant Gateway Routes & Budget Limits

Retrieves the active model routing cascade, latency SLA, cooldown threshold, and spending caps for a tenant.

- **Method:** `GET`
- **Path:** `/v1/tenants/{tenantId}/gateway/routes`
- **Headers:** `Authorization: Bearer <TOKEN>` or `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
- **Response (`200 OK`):**
  ```json
  {
    "tenant_id": "tn_client_848da0c4-a690-4101-bca6-5a40989f6b4e",
    "gateway_settings": {
      "primary_model": "gemini-2.5-flash",
      "fallback_models": [
        "openai/gpt-4o-mini",
        "ollama/qwen2.5:14b"
      ],
      "latency_sla_ms": 4000,
      "cooldown_seconds": 60,
      "retry_attempts": 2
    },
    "budget_settings": {
      "daily_cost_budget": 5.0,
      "monthly_cost_budget": 50.0,
      "hard_limit_action": "downgrade_free_model",
      "free_fallback_model": "ollama/qwen2.5:14b",
      "currency": "USD"
    }
  }
  ```

---

### 4. Update Tenant Gateway Routes & Budget Limits

Updates the model routing cascade, cooldown parameters, SLA thresholds, and virtual spending limits for the tenant.

- **Method:** `PUT`
- **Path:** `/v1/tenants/{tenantId}/gateway/routes`
- **Headers:** `Authorization: Bearer <TOKEN>` or `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
- **Request Body:**
  ```json
  {
    "primary_model": "anthropic/claude-3-5-sonnet-20240620",
    "fallback_models": [
      "openai/gpt-4o",
      "gemini-2.5-flash",
      "ollama/qwen2.5:14b"
    ],
    "latency_sla_ms": 3000,
    "cooldown_seconds": 90,
    "retry_attempts": 2,
    "daily_cost_budget": 10.0,
    "monthly_cost_budget": 100.0,
    "hard_limit_action": "downgrade_free_model",
    "free_fallback_model": "ollama/qwen2.5:14b",
    "currency": "USD"
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "status": "updated",
    "tenant_id": "tn_client_848da0c4-a690-4101-bca6-5a40989f6b4e",
    "gateway_settings": {
      "primary_model": "anthropic/claude-3-5-sonnet-20240620",
      "fallback_models": [
        "openai/gpt-4o",
        "gemini-2.5-flash",
        "ollama/qwen2.5:14b"
      ],
      "latency_sla_ms": 3000,
      "cooldown_seconds": 90,
      "retry_attempts": 2
    },
    "budget_settings": {
      "daily_cost_budget": 10.0,
      "monthly_cost_budget": 100.0,
      "hard_limit_action": "downgrade_free_model",
      "free_fallback_model": "ollama/qwen2.5:14b",
      "currency": "USD"
    }
  }
  ```

---

### 5. Get Virtual Tenant Budget Ledger & Cost Attribution

Calculates real-time token expenditure, remaining balance, and per-model spend attribution from historical inference logs.

- **Method:** `GET`
- **Path:** `/v1/tenants/{tenantId}/gateway/budget`
- **Headers:** `Authorization: Bearer <TOKEN>` or `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
- **Response (`200 OK`):**
  ```json
  {
    "daily_budget": 10.0,
    "monthly_budget": 100.0,
    "hard_limit_action": "downgrade_free_model",
    "free_fallback_model": "ollama/qwen2.5:14b",
    "currency": "USD",
    "current_daily_spend": 2.450,
    "current_monthly_spend": 28.625,
    "is_budget_exceeded": false,
    "cost_by_model": {
      "anthropic/claude-3-5-sonnet-20240620": 18.200,
      "openai/gpt-4o-mini": 7.425,
      "gemini-2.5-flash": 3.000,
      "ollama/qwen2.5:14b": 0.000
    }
  }
  ```

---

## Error Handling & Budget Breach Responses

### 1. HTTP 402 Payment Required (`BudgetExceededError`)
When a tenant's cumulative spend crosses the configured `monthly_cost_budget` or `daily_cost_budget` and `hard_limit_action` is set to `"block"`:
```json
{
  "error": "BudgetExceededError",
  "detail": "Virtual monthly budget ceiling exceeded ($102.50 >= $100.00). Inference blocked by tenant policy."
}
```

### 2. Automatic Zero-Downtime Downgrade
When `hard_limit_action` is set to `"downgrade_free_model"`, the request succeeds with HTTP 200, but the orchestrator reroutes generation to `free_fallback_model` (e.g. `ollama/qwen2.5:14b`), returning:
```json
{
  "content": "...",
  "model_used": "ollama/qwen2.5:14b",
  "metadata": {
    "budget_downgraded": true,
    "original_model": "anthropic/claude-3-5-sonnet-20240620"
  }
}
```
