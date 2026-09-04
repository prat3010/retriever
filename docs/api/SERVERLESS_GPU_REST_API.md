# Serverless Dedicated GPU & Dynamic LoRA REST API Reference

**Base URLs:**
- Production Engine: `https://rag.prateeq.in`
- Local Development: `http://localhost:8000`

---

## 1. Administrative Serverless Observability

### `GET /v1/admin/serverless/status`
Returns deployment tier, active/min/max container scale counts, scaledown timeout window, and current model.

**Headers:**
- `X-Admin-Master-Key`: Master administrative key

**Response (200 OK):**
```json
{
  "provider": "modal",
  "gpu_tier": "A10G",
  "active_containers": 0,
  "min_containers": 0,
  "max_containers": 5,
  "scaledown_window_seconds": 300,
  "is_warm": false,
  "endpoint_url": "https://prateeq--vllm-llama-serve.modal.run",
  "current_active_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "active_lora_adapters": []
}
```

---

### `POST /v1/admin/serverless/probe`
Sends an authentic minimal probe request to measure warm-boot and cold-start TTFT latencies.

**Headers:**
- `X-Admin-Master-Key`: Master administrative key

**Response (200 OK):**
```json
{
  "container_init_time_ms": 1820.0,
  "model_weights_load_time_ms": 590.0,
  "first_token_latency_ms": 142.0,
  "total_cold_start_time_ms": 2552.0,
  "is_cold_start": true,
  "probed_at": "2026-09-05T02:20:00Z"
}
```

---

### `GET /v1/admin/serverless/cost-savings`
Computes empirical cost savings of scale-to-zero compared to a 24/7 dedicated GPU instance.

**Query Parameters:**
- `active_compute_hours` (float, default: `15.0`): Estimated compute hours used per month.
- `gpu_tier` (string, default: `"A10G"`): GPU hardware tier.

**Response (200 OK):**
```json
{
  "active_hours": 15.0,
  "gpu_tier": "A10G",
  "hourly_gpu_rate_usd": 1.0,
  "serverless_monthly_cost_usd": 15.0,
  "dedicated_monthly_cost_usd": 720.0,
  "monthly_savings_usd": 705.0,
  "savings_percentage": 97.92
}
```

---

## 2. Multi-Tenant LoRA Registry & Dynamic Swapping

### `POST /v1/tenants/{tenantId}/lora-adapters`
Registers a fine-tuned LoRA adapter for a specific tenant.

**Headers:**
- `Authorization: Bearer <tenant_token>` OR `X-Admin-Master-Key: <admin_key>`

**Request Body:**
```json
{
  "name": "Production Architecture LoRA",
  "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "artifact_uri": "s3://vault/adapters/arch_lora_v1",
  "rank": 16,
  "alpha": 32.0,
  "target_modules": ["q_proj", "v_proj"],
  "adapter_type": "llm",
  "description": "Enterprise software architecture fine-tuning",
  "activate_immediately": true
}
```

**Response (201 Created):**
```json
{
  "adapter_id": "c1f76d5e-...",
  "tenant_id": "tn_test",
  "name": "Production Architecture LoRA",
  "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "artifact_uri": "s3://vault/adapters/arch_lora_v1",
  "rank": 16,
  "alpha": 32.0,
  "target_modules": ["q_proj", "v_proj"],
  "adapter_type": "llm",
  "description": "Enterprise software architecture fine-tuning",
  "is_active": true,
  "created_at": "2026-09-05T02:20:00Z"
}
```

---

### `GET /v1/tenants/{tenantId}/lora-adapters`
Lists all registered LoRA adapters for the tenant.

### `GET /v1/tenants/{tenantId}/lora-adapters/active`
Retrieves the currently hot-activated adapter for the tenant.

### `POST /v1/tenants/{tenantId}/lora-adapters/{adapterId}/activate`
Hot-activates a specific adapter, deactivating all others for this tenant.

### `POST /v1/tenants/{tenantId}/lora-adapters/{adapterId}/deactivate`
Deactivates the adapter, reverting to the baseline foundation model.

### `DELETE /v1/tenants/{tenantId}/lora-adapters/{adapterId}`
Deletes the adapter metadata record from the tenant registry.
