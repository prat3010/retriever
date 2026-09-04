# Operational Runbook: Serverless Dedicated GPU Serving & Dynamic vLLM / LoRA Pipeline

**Runbook ID:** RB-OPS-096  
**Audience:** Platform SREs, MLOps Engineers, and System Administrators  
**Applies to:** Retriever AI Engine (v0.81.0+)  

---

## 1. Health Checks & Battery Verification

### 1.1 Verify Platform Battery Status
Confirm that Battery #16 (`serverless_gpu_vllm`) is active and operational:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/admin/serverless/status | jq .
```

**Expected Output:**
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

## 2. Cold-Start Probing & Container Warm-Boot

### 2.1 Trigger Cold-Start Handshake Probe
Probe the serverless GPU endpoint to verify scale-up latency and time-to-first-token (TTFT):

```bash
curl -X POST "https://rag.prateeq.in/v1/admin/serverless/probe" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" | jq .
```

**Expected Output:**
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

### 2.2 Calculate Scale-to-Zero Monthly Savings
Verify cost reduction metrics for given active tenant compute hours:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  "https://rag.prateeq.in/v1/admin/serverless/cost-savings?active_compute_hours=15.0&gpu_tier=A10G" | jq .
```

---

## 3. Dynamic Multi-Tenant LoRA Adapter Management

### 3.1 Registering a Tenant LoRA Adapter
Register fine-tuned LoRA weights stored on cloud storage:

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/$TENANT_ID/lora-adapters" \
  -H "Authorization: Bearer $TENANT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Domain Architecture Copilot LoRA",
    "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "artifact_uri": "s3://vault/adapters/arch_lora_v1",
    "rank": 16,
    "alpha": 32.0,
    "target_modules": ["q_proj", "v_proj"],
    "description": "Enterprise cloud architecture tuning",
    "activate_immediately": true
  }' | jq .
```

### 3.2 Hot-Activating a LoRA Adapter
Activate a registered adapter for immediate tenant inference:

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/$TENANT_ID/lora-adapters/$ADAPTER_ID/activate" \
  -H "Authorization: Bearer $TENANT_API_KEY" | jq .
```

### 3.3 Deactivating a LoRA Adapter (Revert to Base Foundation Model)

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/$TENANT_ID/lora-adapters/$ADAPTER_ID/deactivate" \
  -H "Authorization: Bearer $TENANT_API_KEY" | jq .
```

---

## 4. Modal & BentoML Deployment Commands

### 4.1 Deploying to Modal
From `retriever/deploy/modal/`:
```bash
modal setup
modal deploy vllm_server.py
```

### 4.2 Building BentoML Container Image
From `retriever/deploy/bentoml/`:
```bash
bentoml build
bentoml containerize vllm_service:latest -t vllm-serverless:latest
docker run --gpus all -p 3000:3000 vllm-serverless:latest
```
