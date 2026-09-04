# Serverless GPU Serving & Custom vLLM / LoRA Deployment Recipes (Milestone 96)

This directory contains production deployment recipes for running self-hosted, fine-tuned open-weights models on serverless GPU infrastructure with automatic **Scale-to-Zero** auto-scaling and dynamic **Multi-LoRA** adapter swapping.

---

## Architecture Overview

```text
  Client Inference Request ──► Retriever Gateway (M93)
                                        │
                         (Model: modal/vllm-llama-3.1-8b)
                                        ▼
                      Modal / BentoML Serverless Cluster
                     ┌───────────────────────────────────┐
                     │ • Auto-Scale: 0 ◄──► 5 Containers │
                     │ • Idle Timeout: 300s (Scale to 0) │
                     │ • Engine: vLLM PagedAttention     │
                     │ • Dynamic Multi-LoRA Swapping     │
                     └───────────────────────────────────┘
```

---

## 1. Deploying to Modal (`deploy/modal/`)

Modal provides true serverless GPUs with $<3\text{s}$ container warm-boot and per-second billing that automatically scales down to 0 instances when idle.

### Prerequisites
1. Install Modal CLI:
   ```bash
   pip install modal>=0.63.0
   ```
2. Authenticate:
   ```bash
   modal token new
   ```
3. Set up Hugging Face secret (for gated models like Llama 3.1):
   ```bash
   modal secret create huggingface-secret HF_TOKEN=hf_...
   ```

### Pre-Cache Model Weights
```bash
modal run deploy/modal/vllm_server.py::download_model --model-name meta-llama/Meta-Llama-3.1-8B-Instruct
```

### Deploy the Serving Application
```bash
modal deploy deploy/modal/vllm_server.py
```

After deployment, Modal outputs a permanent HTTPS endpoint URL (e.g. `https://<org>--retriever-vllm-serving-serve-vllm.modal.run`).

Configure Retriever's `.env`:
```env
MODAL_ENABLED=true
MODAL_ENDPOINT_URL=https://<org>--retriever-vllm-serving-serve-vllm.modal.run
SERVERLESS_BASE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
SERVERLESS_GPU_TIER=A10G
SERVERLESS_IDLE_TIMEOUT_SEC=300
```

---

## 2. Deploying to BentoCloud / BentoML (`deploy/bentoml/`)

BentoML enables deployment on BentoCloud or on your own Kubernetes cluster using Yatai.

### Build Bento Container
```bash
bentoml build -f deploy/bentoml/bentofile.yaml
```

### Deploy to BentoCloud
```bash
bentoml deploy retriever-vllm-service:latest --env BASE_MODEL=Qwen/Qwen2.5-7B-Instruct
```

Configure Retriever's `.env`:
```env
BENTOML_ENDPOINT_URL=https://<your-bento-endpoint>.bentocloud.ai
```

---

## 3. Dynamic Multi-LoRA Swapping

Both Modal and BentoML deployment recipes support dynamic tensor loading per request without restarting the base model.

When invoking the inference API, pass either:
1. Model identifier with LoRA suffix:
   ```json
   {
     "model": "meta-llama/Meta-Llama-3.1-8B-Instruct:enterprise_sow_v1",
     "messages": [{"role": "user", "content": "Draft technical proposal..."}]
   }
   ```
2. Or custom HTTP headers:
   ```http
   x-lora-id: lora_tn_client_123
   x-lora-artifact-uri: /root/loras/enterprise_sow_v1
   ```
