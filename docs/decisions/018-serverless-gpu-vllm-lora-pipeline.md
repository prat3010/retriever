# ADR-018: Serverless Dedicated GPU Serving & Dynamic vLLM / LoRA Deployment Pipeline

**Status:** Accepted  
**Date:** 2026-09-05  
**Deciders:** Core Engineering Team  
**Consulted:** Cloud Infrastructure Architects, ML Systems Engineers  
**Informed:** Platform Tenants, API Consumers  

---

## 1. Context and Problem Statement

Deploying dedicated, unshared LLMs (such as Llama 3.1 8B, Qwen 2.5 7B, Mistral 7B) for commercial enterprise tenants is critical for stringent data compliance, low variance latency, and domain-specific fine-tuning. However, running 24/7 dedicated GPU instances (e.g. AWS `g5.xlarge` with NVIDIA A10G at $1.00–$1.25/hr) incurs continuous monthly infrastructure costs of $720 to $900 per tenant regardless of whether inferences are being requested. For tenants requesting inferences during business hours or in sporadic batches, 80%–95% of GPU cycles sit idle.

Furthermore, fine-tuning custom models for distinct tenants traditionally required running separate containers for each tenant model, creating prohibitive GPU VRAM duplication.

The platform required:
1. **Scale-to-Zero Serverless GPU Compute:** Automated container hibernation after an idle window (300 seconds), eliminating idle compute costs by 70%–90%+.
2. **Sub-3s Warm-Boot Handshake:** Fast container spin-up with warm weight volume caching.
3. **Dynamic Multi-Tenant LoRA Swapping:** Serving multiple tenant fine-tuned weights on a single foundational vLLM container instance without container restarts or memory thrashing.
4. **Hexagonal Boundary Purity & Zero Mock Invariants:** Full interface decoupling, authentic vLLM OpenAI API protocol support, and real mathematical cost formulas.

---

## 2. Decision Drivers

- **Scale-to-Zero Economics:** Active billing only for fractional GPU seconds used during inference and the scaledown window.
- **Dynamic LoRA Swapping (`--enable-lora`):** Hot-swap LoRA adapters via standard request headers or model alias parameters (`model: "meta-llama/Meta-Llama-3.1-8B-Instruct:lora_adapter_id"`).
- **Hexagonal Boundary Rule:** Pure domain protocols (`ServerlessGpuClientProtocol`, `TenantLoraRegistryProtocol`) with 0 framework imports in `src/domain/abstractions/serverless_gpu.py`.
- **Tenant Isolation & RLS Security:** Tenant LoRA adapter metadata and weights are strictly isolated by `tenant_id` at the database level.
- **Gateway Router Smart Cascade Integration:** Serverless GPU models (`modal/vllm-llama-3.1-8b`, `bentoml/vllm-qwen-2.5-7b`) seamlessly participate in primary/fallback cascades with automatic failover to Gemini/OpenAI or local Ollama.
- **Platform Battery Registration:** Formalized as Platform Battery #16 (`serverless_gpu_vllm`) under `ML_INTELLIGENCE`.

---

## 3. Considered Options

1. **Option 1: Always-On Dedicated Cloud VMs (e.g., AWS EC2 g5.xlarge or GCP a2-highgpu):**
   - *Downside:* Flat $720+/month per tenant, zero scale-to-zero capability, manual capacity planning.
2. **Option 2: Replicate full model weights per fine-tune in separate containers:**
   - *Downside:* Enormous VRAM footprint (16GB+ per tenant model), slow switching (minutes to pull images and weights).
3. **Option 3: Hybrid Serverless GPU Cluster with vLLM Dynamic LoRA (Modal + BentoML) (Chosen):**
   - Pure scale-to-zero (min containers = 0, scaledown window = 300s).
   - High-performance vLLM 0.6+ runtime with PagedAttention and `--enable-lora`.
   - Shared model weight volume caching (`retriever-model-cache`).
   - Dynamic per-request LoRA loading via S3/MinIO artifact URIs.

---

## 4. Decision Outcome

We adopted **Option 3: Serverless GPU Serving & Custom vLLM / LoRA Deployment Pipeline**:

1. **Domain Abstraction:**
   - `src/domain/abstractions/serverless_gpu.py`: Pure domain contracts (`ServerlessProviderType`, `ServerlessGpuTier`, `LoraAdapterMetadata`, `WarmBootMetrics`, `ServerlessCostComparison`, `ServerlessGpuClientProtocol`, `TenantLoraRegistryProtocol`).
2. **Production Compute Recipes:**
   - `deploy/modal/vllm_server.py`: Serverless Modal recipe deploying vLLM with A10G GPU, persistent HuggingFace volume caching, dynamic LoRA mounting, and automatic scale-to-zero (`scaledown_window=300`).
   - `deploy/bentoml/service.py` & `deploy/bentoml/bentofile.yaml`: Containerized BentoML vLLM service for self-hosted Kubernetes / GPU VPS clusters.
3. **Infrastructure Adapters:**
   - `src/adapters/cognitive/modal_client.py`: Implements `LlmProvider` and `ServerlessGpuClientProtocol`, with cold-start detection, warm-boot latency telemetry, dynamic LoRA injection, and cost savings math.
   - `src/adapters/database/tenant_lora_repository.py`: Implements `TenantLoraRegistryProtocol` with Postgres RLS multi-tenant security and zero-downtime hot-activation.
4. **Gateway Router Integration:**
   - `src/adapters/cognitive/gateway_router.py`: Registered catalog models, serverless completion and streaming dispatch with active tenant LoRA resolution, and probe connectivity checks.
5. **Platform Battery #16:**
   - Registered in `BatteryService` as `serverless_gpu_vllm` (Category: `ML_INTELLIGENCE`, Milestone: `M96 (v0.81.0)`).
6. **FastAPI Endpoints:**
   - Admin router `/v1/admin/serverless/*` (status, probe, cost-savings).
   - Tenant router `/v1/tenants/{tenantId}/lora-adapters/*` (CRUD, hot-activation).
7. **Client Control Plane:**
   - `Prateek_website/src/components/rag/GatewayPanel.tsx`: Interactive Serverless GPU cluster status card, cold-start latency probe button, scale-to-zero cost savings metrics, and dynamic LoRA adapter activator.

---

## 5. Consequences

### Positive
- **Dramatic Cost Reduction:** Tenants with intermittent or business-hours workloads experience 70%–95% compute cost savings ($15–$60/mo vs $720/mo).
- **Zero VRAM Duplication:** Multiple fine-tuned tenant adapters run simultaneously against a single cached foundation model.
- **Enterprise Self-Service:** Tenants can hot-activate and evaluate fine-tuned LoRA adapters directly from the SaaS Studio.
- **Full Fallback Safety:** If cold-start exceeds latency SLA or GPU capacity is constrained, Gateway Router cascades seamlessly to Gemini 2.5 Flash or local Ollama.

### Neutral / Operational Considerations
- Cold-start overhead (1.5s–2.5s) on initial request after idle scale-to-zero, handled via warm-boot pre-warming probes and transparent UI badges.
