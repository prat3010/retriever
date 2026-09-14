# ☸️ Retriever Production Helm 3 Chart

Official Helm 3 Chart for deploying the **Retriever Cognitive RAG Engine & Studio** on Kubernetes.

This chart deploys high-availability FastAPI API pods, Next.js Web Studio, HorizontalPodAutoscalers, Ingress with TLS, bundled PostgreSQL 16 + pgvector storage, and Redis 7 caching.

---

## 🚀 Quickstart

### Prerequisites
- Kubernetes cluster 1.26+
- Helm 3.10+
- `kubectl` configured with cluster administrator permissions
- Dynamic PersistentVolume provisioner (or configured StorageClass)

### 1. Install Chart with Defaults
```bash
# Clone repository
git clone https://github.com/prat3010/retriever.git
cd retriever

# Install release
helm install retriever ./deploy/helm/retriever \
  --namespace retriever \
  --create-namespace
```

### 2. Verify Installation
```bash
# Watch pod initialization
kubectl get pods -n retriever -w

# Check services
kubectl get svc -n retriever
```

---

## ⚙️ Configuration Reference

The following table lists the configurable parameters of the Retriever chart and their default values in `values.yaml`:

| Parameter | Description | Default |
|:---|:---|:---|
| `api.replicaCount` | Number of FastAPI API pods | `2` |
| `api.image.repository` | API container repository | `ghcr.io/prateeksharma/retriever-api` |
| `api.image.tag` | API container image tag | `v1.2.0-alpha1` |
| `api.service.type` | Kubernetes service type | `ClusterIP` |
| `api.service.port` | API service port | `8000` |
| `api.autoscaling.enabled` | Enable HorizontalPodAutoscaler v2 | `true` |
| `api.autoscaling.minReplicas` | Minimum API replicas | `2` |
| `api.autoscaling.maxReplicas` | Maximum API replicas | `10` |
| `api.autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization % | `75` |
| `api.resources.requests.cpu` | Requested CPU | `250m` |
| `api.resources.requests.memory` | Requested Memory | `512Mi` |
| `api.resources.limits.cpu` | CPU limit | `1000m` |
| `api.resources.limits.memory` | Memory limit | `2Gi` |
| `web.enabled` | Enable Next.js Web Studio | `true` |
| `web.replicaCount` | Number of Web Studio pods | `1` |
| `web.service.port` | Web Studio service port | `3000` |
| `ingress.enabled` | Enable Ingress controller routing | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.annotations` | Ingress annotations (cert-manager TLS) | See `values.yaml` |
| `postgresql.enabled` | Bundled PostgreSQL 16 + pgvector | `true` |
| `postgresql.persistence.size` | PVC storage size for pgvector | `20Gi` |
| `postgresql.auth.database` | Database name | `retriever_db` |
| `postgresql.auth.username` | Database user | `postgres` |
| `postgresql.auth.password` | Database password | `change-me-in-production` |
| `redis.enabled` | Bundled Redis 7 caching & lock engine | `true` |
| `redis.persistence.size` | PVC storage size for Redis AOF | `5Gi` |
| `migrations.runOnDeploy` | Run Alembic migrations pre-install hook | `true` |
| `gpu.enabled` | Allocate dedicated GPU accelerators | `false` |
| `gpu.type` | Accelerator resource type | `nvidia.com/gpu` |
| `gpu.count` | Accelerator count per API replica | `1` |

---

## 🏭 Production Overrides Example

Create a `values-prod.yaml` file:

```yaml
api:
  replicaCount: 3
  autoscaling:
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: rag.mycompany.com
      paths:
        - path: /
          pathType: Prefix
          service: api
    - host: studio.rag.mycompany.com
      paths:
        - path: /
          pathType: Prefix
          service: web
  tls:
    - secretName: retriever-prod-tls
      hosts:
        - rag.mycompany.com
        - studio.rag.mycompany.com

postgresql:
  persistence:
    size: 100Gi
    storageClass: "gp3"
  auth:
    password: "StrongProductionPassword123!"

gpu:
  enabled: true
  type: "nvidia.com/gpu"
  count: 1
```

Deploy with custom overrides:
```bash
helm upgrade --install retriever ./deploy/helm/retriever \
  --namespace retriever \
  --values values-prod.yaml
```

---

## 🔄 Upgrading & Rollback

### Upgrade Release
```bash
helm upgrade retriever ./deploy/helm/retriever \
  --namespace retriever \
  --set api.image.tag="v1.2.0-beta1"
```

### Rollback Release
```bash
helm rollback retriever 1 --namespace retriever
```

### Uninstall Release
```bash
helm uninstall retriever --namespace retriever
```
