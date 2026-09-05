# Serverless GPU Serving & Dynamic Multi-LoRA Pipeline

**Milestone:** M96 (v0.81.0)  
**System Layer:** Dedicated Serverless Inference & Dynamic Parameter-Efficient Fine-Tuning (Platform Battery #16)  
**Architecture:** Modal / BentoML Scale-to-Zero Auto-Scaler + vLLM PagedAttention Runtime + Dynamic Multi-LoRA Tensor Swapping + LiteLLM Gateway Integration  

---

## 1. Executive Summary

Milestone 96 delivers **Platform Battery #16: `serverless_gpu_vllm`**, bringing scale-to-zero serverless dedicated GPU computing and multi-tenant dynamic LoRA weight swapping to Retriever.

Enterprise tenants frequently require dedicated open-source LLMs (e.g. Llama 3.1 8B, Qwen 2.5 7B) fine-tuned on proprietary internal knowledge. However, traditional GPU infrastructure deployments face severe economic challenges:
1. **Idle GPU Burn:** Running dedicated cloud GPU instances (AWS `g5.xlarge` A10G at $1.00–$1.25/hr) 24/7 costs $720–$900/month per tenant, with 80%–95% of GPU cycles sitting completely idle during off-peak hours.
2. **VRAM Duplication:** Deploying separate full-model containers for each tenant fine-tune rapidly exhausts GPU cluster capacity.

Platform Battery #16 solves this with a two-pronged serverless architecture:
- **Scale-to-Zero Container Scaling:** Containers spin down to 0 instances after a 300-second idle window, cutting cloud GPU costs by 70%–90%+.
- **Multi-Tenant Dynamic LoRA Swapping:** A single shared base model container serves dozens of tenant-specialized Low-Rank Adaptation (LoRA) adapters concurrently without container restarts or memory thrashing.

---

## 2. Technical Architecture & Dynamic LoRA Swapping

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SERVERLESS MULTI-LORA ARCHITECTURE                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Tenant Request: "meta-llama/Meta-Llama-3.1-8B-Instruct:lora_legal_v2" ]           │
│                         │                                                              │
│                         ▼                                                              │
│            ┌───────────────────────────┐                                               │
│            │ LiteLLM Smart Gateway     │ ── Evaluates Provider Health & Cold Status    │
│            └────────────┬──────────────┘                                               │
│                         │                                                              │
│                         ▼                                                              │
│            ┌───────────────────────────┐                                               │
│            │ Modal / BentoML Orchestrator                                             │
│            │ - If 0 containers: Fast warm-boot (<3s) from persistent volume cache     │
│            │ - If active container: Route to warm worker (~25ms TTFT)                 │
│            └────────────┬──────────────┘                                               │
│                         │                                                              │
│                         ▼                                                              │
│            ┌─────────────────────────────────────────────────────────────┐             │
│            │ Shared vLLM Runtime Container (NVIDIA A10G 24GB VRAM)       │             │
│            │                                                             │             │
│            │  ┌───────────────────────────────────────────────────────┐  │             │
│            │  │ Base Model Weights: Meta-Llama-3.1-8B-Instruct        │  │             │
│            │  │ (PagedAttention VRAM KV-Cache, Locked in GPU Memory)   │  │             │
│            │  └───────────────────────────┬───────────────────────────┘  │             │
│            │                              │                              │             │
│            │         ┌────────────────────┴────────────────────┐         │             │
│            │         ▼                                         ▼         │             │
│            │  [ LoRA: Legal Contract ]                 [ LoRA: Tech Support ]   │     │
│            │  - ΔW = B · A (Rank r=16)                 - ΔW = B · A (Rank r=8)   │     │
│            │  - Hot-swapped dynamically                - Loaded on-the-fly       │     │
│            │  - Tiny memory footprint (<50MB)          - Multi-tenant isolated   │     │
│            └─────────────────────────────────────────────────────────────┘             │
│                         │                                                              │
│                         ▼                                                              │
│   [ SSE Streaming Token Stream (Sub-25ms TTFT Warm Latency) ]                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Capabilities

1. **Scale-to-Zero Hibernation:** Automated scaledown after 300s of inactivity; billing drops to $0.00 while idle.
2. **Sub-3s Warm Boot:** Pre-caches foundational model weights on persistent SSD volumes (`retriever-model-cache`), reducing cold container initialization from minutes to under 3 seconds.
3. **Dynamic `--enable-lora` Swapping:** Ingests low-rank adapter weights ($\approx 20\text{MB}-80\text{MB}$) directly from S3/MinIO and loads them into GPU memory per request without restarting the inference server.
4. **Transparent Gateway Cascade:** In the event of cold-boot container scaling, the smart router can speculatively fall back to local Ollama or cloud models if low-latency SLA headers are present.

---

## 4. Implementation Details

- **Compute Recipes:** `deploy/modal/vllm_server.py` and `deploy/bentoml/service.py`
- **Adapter:** `apps/api/src/adapters/cognitive/modal_client.py`
- **LoRA Repository:** `apps/api/src/adapters/database/tenant_lora_repository.py`
- **FastAPI Router:** `apps/api/src/routers/serverless_gpu.py`
- **SaaS UI:** `Prateek_website/src/components/rag/GatewayPanel.tsx`
- **Latency Profile:** $\sim 25\text{ms}$ TTFT warm / $<3\text{s}$ cold boot.
- **Health Check Endpoint:** `GET /v1/admin/serverless/status`

---

## 5. Non-Negotiable Invariants

1. **Strict LoRA Isolation:** Adapter weights and metadata are strictly isolated by `tenant_id` via PostgreSQL Row-Level Security; cross-tenant adapter invocation is blocked at the gateway router.
2. **Volume Cache Integrity:** Base model weights must reside on local persistent NVMe/SSD cache volumes; containers must never pull 16GB weights from public HuggingFace registries during boot.
3. **Max LoRA Capacity:** The runtime enforces a hard limit of 16 active in-memory LoRA adapters per container instance to prevent GPU VRAM exhaustion.
