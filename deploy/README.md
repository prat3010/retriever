# 🚀 Retriever Deployment Architecture & Recipes

Retriever provides turnkey deployment pathways tailored to every operational tier—from local developer laptops and single virtual machines to enterprise multi-tenant Kubernetes clusters and serverless GPU fleets.

---

## 🗺️ Deployment Strategies Matrix

| Tier | Target Infrastructure | Primary Artifacts | Ideal Use Case | Documentation Link |
|:---|:---|:---|:---|:---|
| **1-Click Quickstart** | Local Dev / Single VM | `install.sh`, `scripts/quickstart.sh` | Instant evaluation, 30-second time-to-dopamine | [Quickstart Guide](../README.md#-quickstart-in-30-seconds) |
| **Docker Compose** | Single Server / VPS | `docker-compose.yml`, `deploy/docker/` | Self-hosted small teams, internal enterprise PoCs | [Docker Guide](../README.md#-1-click-docker-compose-quickstart) |
| **Production Helm 3 Chart** | Enterprise Kubernetes | `deploy/helm/retriever/` | Multi-replica high-availability clusters (AWS EKS, GCP GKE, Azure AKS) | [Helm Chart Guide](helm/retriever/README.md) |
| **Kubernetes Native Operator** | Self-Healing Clusters | `deploy/operator/` | Declarative CRD reconciliation, rolling upgrades & automated backups | [Operator Guide](operator/README.md) |
| **Serverless GPU Serving** | Cloud GPU Auto-Scaling | `deploy/modal/`, `deploy/bentoml/` | Scale-to-zero vLLM serving with dynamic multi-LoRA weight swapping | [Serverless GPU Recipes](#serverless-gpu-serving-recipes-m96) |
| **Production Cloud VPS** | Oracle Cloud / Ubuntu | `docs/infrastructure/DEPLOYMENT.md` | Free-tier / low-cost production hosting on dedicated VPS | [Oracle VPS Guide](../docs/infrastructure/DEPLOYMENT.md) |

---

## ☸️ Cloud-Native Kubernetes & Helm 3 (Milestone 112)

For enterprise production deployments on Kubernetes:

- **Production Helm 3 Chart (`deploy/helm/retriever/`):**
  - High-availability FastAPI API pods with HorizontalPodAutoscaler v2.
  - Next.js Web Studio with Ingress TLS termination.
  - StatefulSet with persistent storage for pgvector PostgreSQL 16 and Redis 7.
  - See the [Helm Chart Documentation](helm/retriever/README.md).

- **Kubernetes Native Operator (`deploy/operator/`):**
  - Custom Resource Definition: `RetrieverCluster` (`retriever.run/v1alpha1`).
  - Level-triggered controller automating rolling image updates, GPU affinity, and S3 backups.
  - See the [Kubernetes Operator Documentation](operator/README.md).

---

## ⚡ Serverless GPU Serving Recipes (Milestone 96)

For hosting self-hosted, fine-tuned open-weights models on serverless GPU infrastructure with automatic **Scale-to-Zero** auto-scaling and dynamic **Multi-LoRA** adapter swapping:

### 1. Deploying to Modal (`deploy/modal/`)
Modal provides true serverless GPUs with $<3\text{s}$ container warm-boot and per-second billing that automatically scales down to 0 instances when idle.

```bash
# Pre-cache model weights
modal run deploy/modal/vllm_server.py::download_model --model-name meta-llama/Meta-Llama-3.1-8B-Instruct

# Deploy serving application
modal deploy deploy/modal/vllm_server.py
```

### 2. Deploying to BentoCloud / BentoML (`deploy/bentoml/`)
BentoML enables deployment on BentoCloud or on your own Kubernetes cluster using Yatai.

```bash
# Build bento container
bentoml build -f deploy/bentoml/bentofile.yaml

# Deploy to BentoCloud
bentoml deploy retriever-vllm-service:latest --env BASE_MODEL=Qwen/Qwen2.5-7B-Instruct
```

### 3. Dynamic Multi-LoRA Swapping
Both Modal and BentoML deployment recipes support dynamic tensor loading per request without restarting the base model via the `x-lora-id` HTTP header.
