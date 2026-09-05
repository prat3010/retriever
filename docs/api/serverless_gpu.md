---
id: Retriever_API_v1_serverless_gpu
title: "API Specification: Serverless Dedicated GPU & Dynamic Multi-LoRA Pipeline (/v1/admin/serverless, /v1/tenants/{tenantId}/lora-adapters)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/serverless
  - gpu/vllm
  - lora/adapters
  - platform/retriever
blast_radius: HIGH
security_auth: ADMIN_KEY_OR_BEARER_JWT
invariants:
  - "Serverless GPU containers MUST auto-hibernate after 300 seconds of idle traffic."
  - "Tenant LoRA adapter registrations and artifacts MUST strictly enforce tenant_id isolation."
  - "A maximum of 16 active in-memory LoRA adapters can be loaded simultaneously per container."
---

# API Specification: Serverless GPU Serving & Dynamic Multi-LoRA (`/v1/serverless`)

#api #serverless #gpu #vllm #lora #finetuning #retriever

> **Authoritative REST API specification for serverless GPU cluster observability, scale-to-zero cost comparisons, cold-start warm-boot triggers, and multi-tenant dynamic LoRA adapter lifecycle management (Platform Battery #16).**

---

## 1. Overview & Dynamic LoRA Swapping Flow

The Serverless GPU API interfaces with Modal and BentoML containerized vLLM clusters running NVIDIA A10G GPUs:
- **Scale-to-Zero Auto-Scaling:** Hibernates idle workers after 300 seconds of inactivity.
- **Dynamic LoRA Swapping:** Ingests low-rank adapter weights from S3/MinIO and dynamically mounts them onto a shared foundational model (`meta-llama/Meta-Llama-3.1-8B-Instruct` or `qwen/Qwen2.5-7B-Instruct`) per request without server restarts.

```text
  [ Admin / Tenant Client ]                               [ Retriever Serverless API ]
             │                                                         │
             │ 1. POST /v1/admin/serverless/warmup                     │
             ├────────────────────────────────────────────────────────►│ (Measure Warm-Boot TTFT)
             │◄────────────────────────────────────────────────────────┤
             │    { "is_warm": true, "warm_boot_latency_ms": 28.4 }    │
             │                                                         │
             │ 2. POST /v1/tenants/{id}/lora-adapters                  │
             │    { "name": "Legal LoRA", "artifact_uri": "s3://..." } │
             ├────────────────────────────────────────────────────────►│ (Store in PostgreSQL RLS)
             │◄────────────────────────────────────────────────────────┤
             │    { "adapter_id": "lora_01", "status": "ACTIVE" }      │
             │                                                         │
             │ 3. POST /v1/chat/completions                            │
             │    { "model": "meta-llama-3.1-8b:lora_01" }             │
             ├────────────────────────────────────────────────────────►│ (Hot-swap weights in vLLM)
```

---

## 2. Admin Serverless Endpoints

### 2.1 Get Serverless Deployment Status
* **Endpoint:** `GET /v1/admin/serverless/status`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Retrieves real-time cluster status, active vs. idle container counts, GPU memory utilization, and active base models.
* **Response (200 OK):**
```json
{
  "provider": "modal",
  "gpu_tier": "A10G",
  "active_containers": 1,
  "min_containers": 0,
  "max_containers": 4,
  "is_warm": true,
  "idle_seconds_remaining": 240,
  "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "loaded_lora_count": 3
}
```

### 2.2 Trigger Container Warm-Boot Probe
* **Endpoint:** `POST /v1/admin/serverless/warmup`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Sends a probe request to pre-warm cold container pools and measures time-to-first-token (TTFT).
* **Response (200 OK):**
```json
{
  "is_warm": true,
  "warm_boot_latency_ms": 28.5,
  "cold_start_detected": false,
  "probed_at": "2026-09-05T18:00:00Z"
}
```

### 2.3 Get Serverless Cost Comparison
* **Endpoint:** `GET /v1/admin/serverless/cost-comparison`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Query Parameters:** `monthly_requests` (int), `avg_tokens_per_req` (int).
* **Response (200 OK):**
```json
{
  "always_on_monthly_cost_usd": 730.00,
  "serverless_monthly_cost_usd": 84.50,
  "total_savings_usd": 645.50,
  "savings_percentage": 88.4,
  "currency": "USD"
}
```

---

## 3. Tenant LoRA Registry Endpoints

### 3.1 List Tenant LoRA Adapters
* **Endpoint:** `GET /v1/tenants/{tenantId}/lora-adapters`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):** Array of `LoraAdapterMetadata` objects.

### 3.2 Register Fine-Tuned LoRA Adapter
* **Endpoint:** `POST /v1/tenants/{tenantId}/lora-adapters`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "name": "Legal Contract Analyzer LoRA",
  "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "artifact_uri": "s3://retriever-tenant-vaults/legal_lora_v2.safetensors",
  "rank": 16,
  "alpha": 32.0,
  "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
  "adapter_type": "llm",
  "description": "Trained on standard commercial NDAs and service agreements",
  "activate_immediately": true
}
```
* **Response (201 Created):** Returns confirmed `LoraAdapterMetadata` with generated `adapter_id`.

### 3.3 Activate LoRA Adapter for Inference
* **Endpoint:** `POST /v1/tenants/{tenantId}/lora-adapters/{adapterId}/activate`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):** Confirms dynamic weight mounting into active vLLM runner.

### 3.4 Delete LoRA Adapter
* **Endpoint:** `DELETE /v1/tenants/{tenantId}/lora-adapters/{adapterId}`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):** Confirms unmounting and database record deletion.
