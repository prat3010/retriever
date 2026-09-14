# Kubernetes Native Operator & Production Helm Cloud-Native Orchestrator

**Milestone:** M112 (v1.2.0-alpha1)  
**System Layer:** Cloud-Native Orchestration & Infrastructure Resiliency (Platform Battery #28)  
**Architecture:** Level-Triggered State Reconciliation + CRD OpenAPI v3 Validation + Production Helm 3 Package  

---

## 1. Executive Summary

Milestone 112 registers **Platform Battery #28 (`kubernetes_native_operator`)** under the `SYSTEM_EXTENSIBILITY` architectural category.

While single-machine Docker Compose setups serve development environments, enterprise deployments mandate high-availability multi-replica pod scheduling, automated HorizontalPodAutoscalers, zero-downtime rolling upgrades, hardware-sensed GPU acceleration, and automated disaster recovery.

Milestone 112 delivers a turnkey cloud-native control plane:
- **Production Helm 3 Chart (`deploy/helm/retriever/`):** Full cluster template bundling FastAPI API pods, Next.js Web Studio, HPA v2, Ingress with cert-manager Let's Encrypt TLS annotations, PostgreSQL 16 + pgvector StatefulSet (20Gi PVC), Redis 7 StatefulSet, and pre-install database migration hooks (`alembic upgrade head`).
- **Kubernetes Custom Resource Definition (`RetrieverCluster`):** Custom API group `retriever.run/v1alpha1` with comprehensive OpenAPI v3 schema validation, subresources (`status`, `scale`), and `kubectl get rc` printer columns.
- **Level-Triggered State Machine Reconciler:** Hexagonal reconciler adapter in `apps/api/src/adapters/operator/cluster_reconciler.py` executing level-triggered phase transitions (`Pending` $\rightarrow$ `Provisioning` $\rightarrow$ `Running`), detecting image tag divergence for zero-downtime rolling updates, replica autoscaling, GPU worker node assignments, and automated S3 backup dispatches.
- **In-Memory Kubernetes Client (`InMemoryKubernetesClient`):** Pure abstract port implementation allowing 100% test coverage in CI without requiring live Minikube or Kind clusters.

---

## 2. Component Topology

```text
       Kubernetes API Server
                 │
                 ▼
  ┌──────────────────────────────┐
  │ RetrieverCluster CRD         │  (retriever.run/v1alpha1)
  └──────────────┬───────────────┘
                 │ Watch / Level-Triggered Events
                 ▼
  ┌──────────────────────────────┐
  │ ClusterReconciler            │  (Hexagonal Reconciler Adapter)
  └──────────────┬───────────────┘
                 │
        ┌────────┴────────┬───────────────────┬──────────────────┐
        ▼                 ▼                   ▼                  ▼
  FastAPI Pods      Next.js Web         PostgreSQL 16        Redis 7
  (Deployments      (Deployments        pgvector             (StatefulSet
   + HPA v2)         + Services)         (StatefulSet + PVC)  + PVC)
```

---

## 3. Specifications & Parameters

### Battery Specification
- **Identifier:** `kubernetes_native_operator`
- **Category:** `SYSTEM_EXTENSIBILITY`
- **Latency Profile:** `<5ms` in-memory reconcile loop / declarative k8s watch
- **Algorithm Foundation:** Level-Triggered Declarative State Reconciliation + CRD OpenAPI v3 Schema Validation
- **Health Check Endpoint:** `/v1/admin/operator/status`

### Key Spec Parameters (`RetrieverClusterSpec`)
| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `replicas` | `int` | `2` | Number of FastAPI API pods ($1 \le n \le 50$) |
| `web_replicas` | `int` | `1` | Number of Next.js Web Studio pods ($0 \le n \le 20$) |
| `image_tag` | `str` | `"v1.2.0-alpha1"` | Container image tag for rolling upgrades |
| `postgres_pvc_size` | `str` | `"20Gi"` | PersistentVolumeClaim capacity for pgvector storage |
| `gpu.enabled` | `bool` | `false` | Enable GPU node selector and tolerations |
| `gpu.gpu_type` | `str` | `"nvidia.com/gpu"` | Accelerator resource type |
| `backup_policy.enabled` | `bool` | `true` | Enable automated database and vector WAL backups |
| `backup_policy.schedule` | `str` | `"0 2 * * *"` | Nightly backup cron schedule |

---

## 4. Verification & Testing

Validated by automated test suite in `apps/api/tests/test_kubernetes_operator.py`:
- 11/11 tests passing covering Hexagonal import purity, spec validations, reconciliation state machine, rolling upgrades, GPU allocations, Helm YAML structure, and CRD OpenAPI v3 validation.
