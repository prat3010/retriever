# 🤖 Retriever Kubernetes Operator

Custom Cloud-Native Kubernetes Operator for declarative lifecycle management, automated rollouts, and disaster recovery of **Retriever Cognitive Clusters**.

Registered as **Platform Battery #28 (`kubernetes_native_operator`)** in the Retriever capabilities catalog.

---

## 🏛️ Architecture Overview

```text
       Kubernetes API Server
                 │
                 ▼
  ┌──────────────────────────────┐
  │ RetrieverCluster CRD         │  (group: retriever.run/v1alpha1)
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

## 📋 Custom Resource Definition (`RetrieverCluster`)

The operator manages the custom resource `RetrieverCluster` (`retrieverclusters.retriever.run`):

- **API Group:** `retriever.run`
- **Version:** `v1alpha1`
- **Kind:** `RetrieverCluster`
- **Short Names:** `rc`, `rcluster`
- **Subresources:** `status`, `scale` (`specReplicasPath: .spec.replicas`, `statusReplicasPath: .status.readyReplicas`)

### Key Specification Fields (`.spec`)
| Field | Type | Description | Default |
|:---|:---|:---|:---|
| `replicas` | `integer` | Number of FastAPI API pods | `2` |
| `webReplicas` | `integer` | Number of Next.js Web Studio pods | `1` |
| `imageTag` | `string` | Container image tag for Retriever components | `v1.2.0-alpha1` |
| `postgresPvcSize` | `string` | Storage capacity for pgvector PersistentVolumeClaim | `20Gi` |
| `postgresStorageClass` | `string` | Optional Kubernetes storage class | `nil` |
| `gpu.enabled` | `boolean` | Whether to schedule API pods on GPU worker nodes | `false` |
| `gpu.gpuType` | `string` | Accelerator identifier (`nvidia.com/gpu`) | `nvidia.com/gpu` |
| `gpu.gpuCount` | `integer` | Accelerator count per pod | `1` |
| `backupPolicy.enabled` | `boolean` | Enable automated database and vector WAL backups | `true` |
| `backupPolicy.schedule` | `string` | Backup cron expression | `0 2 * * *` |
| `backupPolicy.s3Bucket` | `string` | Destination S3 bucket for WAL snapshots | `retriever-backups` |

### Status Lifecycle Phases (`.status.phase`)
- `Pending`: CRD accepted; underlying storage and cluster resources queued.
- `Provisioning`: Database statefulsets mounted, network services linked.
- `Running`: All pods healthy, serving traffic, ready replicas match desired replicas.
- `Upgrading`: Detected new `imageTag` divergence; performing zero-downtime rolling update.
- `Degraded`: One or more pods failed health probes or database volume unmounted.
- `Failed`: Fatal misconfiguration or resource exhaustion.

---

## 🚀 Installation & Usage

### 1. Install Custom Resource Definition
```bash
kubectl apply -f deploy/operator/crds/retrieverclusters.retriever.run.crd.yaml
```

Verify CRD registration:
```bash
kubectl get crd retrieverclusters.retriever.run
```

### 2. Deploy a Minimal Dev Cluster
```bash
kubectl apply -f deploy/operator/samples/retriever_cluster_minimal.yaml
```

### 3. Deploy a Production Cluster with GPU & Backups
```bash
kubectl apply -f deploy/operator/samples/retriever_cluster_production.yaml
```

Inspect cluster status with native printer columns:
```bash
kubectl get rc -n retriever-system
```
Output:
```text
NAME             PHASE     DESIRED   READY   VERSION         AGE
retriever-prod   Running   3         3       v1.2.0-alpha1   2m
```

---

## 🛡️ Admin REST API & Programmatic Control

Admins can inspect operator status, list active clusters, trigger reconciliations, and dispatch on-demand backups via authenticated REST endpoints:

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/v1/admin/operator/status` | Controller health, CRD group, and active cluster count |
| `GET` | `/v1/admin/operator/clusters` | List managed clusters across all namespaces |
| `POST` | `/v1/admin/operator/reconcile` | Programmatically reconcile a `RetrieverClusterSpec` |
| `POST` | `/v1/admin/operator/clusters/{cluster_name}/backup` | Dispatch on-demand database & vector backup job |

---

## 🧪 Testing

The operator controller includes a comprehensive Pytest test suite covering all state transitions, CRD OpenAPI v3 validation, and Hexagonal boundaries:

```bash
pytest apps/api/tests/test_kubernetes_operator.py -v
```
