---
id: Retriever_API_v1_operator
title: "API Specification: Kubernetes Native Operator & Helm Orchestrator (/v1/admin/operator)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/operator
  - kubernetes/crd
  - helm/orchestration
  - platform/retriever
blast_radius: HIGH
security_auth: ADMIN_KEY
invariants:
  - "Cluster status operations MUST only be accessible via X-Admin-Master-Key."
  - "Cluster reconciliation cycles MUST be level-triggered and idempotent."
  - "Dispatched backup jobs MUST record ISO-8601 audit timestamps."
---

# API Specification: Kubernetes Native Operator (`/v1/admin/operator`)

#api #operator #kubernetes #helm #crd #cloudnative #retriever

> **Authoritative REST API specification for Kubernetes Operator controller status, CRD cluster reconciliation, declarative specification enforcement, and automated database/vector backup dispatches (Platform Battery #28).**

---

## 1. Overview

The Operator API allows platform administrators to programmatically observe and reconcile `RetrieverCluster` custom resources running across Kubernetes clusters:
- **Declarative Reconciliation:** Level-triggered state reconciliation driving clusters from `Pending` to `Provisioning` to `Running`.
- **Zero-Downtime Rolling Upgrades:** Trigger image tag upgrades and monitor rolling replica transitions.
- **Disaster Recovery:** Dispatch automated database WAL and vector backup jobs on demand.

```text
  [ Admin Client / CI/CD ]                                [ Retriever Operator Controller ]
             │                                                         │
             │ 1. GET /v1/admin/operator/status                        │
             ├────────────────────────────────────────────────────────►│
             │◄────────────────────────────────────────────────────────┤
             │    { "status": "healthy", "active_clusters": 3 }        │
             │                                                         │
             │ 2. POST /v1/admin/operator/reconcile                    │
             │    { "name": "prod", "replicas": 5, ... }               │
             ├────────────────────────────────────────────────────────►│ (Level-triggered reconcile)
             │◄────────────────────────────────────────────────────────┤
             │    { "phase": "Running", "ready_replicas": 5 }          │
             │                                                         │
             │ 3. POST /v1/admin/operator/clusters/prod/backup         │
             ├────────────────────────────────────────────────────────►│ (Dispatch k8s Job)
             │◄────────────────────────────────────────────────────────┤
             │    { "status": "Accepted", "job_id": "job-backup-..." } │
```

---

## 2. Endpoints

### 2.1 Get Operator Status
* **Endpoint:** `GET /v1/admin/operator/status`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Retrieves the health of the in-memory/Kubernetes controller, supported CRD group, and count of active clusters.
* **Response (200 OK):**
```json
{
  "status": "healthy",
  "crd_group": "retriever.run",
  "crd_version": "v1alpha1",
  "crd_kind": "RetrieverCluster",
  "helm_chart_version": "1.2.0-alpha1",
  "active_clusters_count": 2,
  "in_memory_reconciler_active": true
}
```

---

### 2.2 List Clusters
* **Endpoint:** `GET /v1/admin/operator/clusters`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Query Parameters:**
  - `namespace` *(optional, string)*: Filter clusters by Kubernetes namespace.
* **Response (200 OK):**
```json
[
  {
    "apiVersion": "retriever.run/v1alpha1",
    "kind": "RetrieverCluster",
    "metadata": {
      "name": "retriever-prod",
      "namespace": "retriever-system"
    },
    "spec": {
      "name": "retriever-prod",
      "namespace": "retriever-system",
      "replicas": 3,
      "web_replicas": 2,
      "image_tag": "v1.2.0-alpha1",
      "postgres_pvc_size": "50Gi",
      "gpu": {
        "enabled": true,
        "gpu_type": "nvidia.com/gpu",
        "gpu_count": 1
      },
      "backup_policy": {
        "enabled": true,
        "schedule": "0 2 * * *",
        "s3_bucket": "enterprise-backups"
      }
    },
    "status": {
      "phase": "Running",
      "ready_replicas": 3,
      "desired_replicas": 3,
      "database_healthy": true,
      "active_image_tag": "v1.2.0-alpha1",
      "conditions": [
        {
          "type": "Available",
          "status": "True",
          "reason": "AllPodsReady",
          "message": "3/3 replicas available",
          "last_transition_time": "2026-09-15T00:20:00Z"
        }
      ]
    }
  }
]
```

---

### 2.3 Programmatic Reconcile Cluster
* **Endpoint:** `POST /v1/admin/operator/reconcile`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Request Body:**
```json
{
  "name": "retriever-prod",
  "namespace": "retriever-system",
  "replicas": 4,
  "web_replicas": 2,
  "image_tag": "v1.2.0-beta1",
  "postgres_pvc_size": "50Gi",
  "gpu": {
    "enabled": true,
    "gpu_type": "nvidia.com/gpu",
    "gpu_count": 1
  },
  "backup_policy": {
    "enabled": true,
    "schedule": "0 2 * * *",
    "retention_days": 30
  }
}
```
* **Response (200 OK):**
```json
{
  "phase": "Running",
  "ready_replicas": 4,
  "desired_replicas": 4,
  "web_ready_replicas": 2,
  "database_healthy": true,
  "last_backup_at": null,
  "last_reconciled_at": "2026-09-15T00:25:12Z",
  "active_image_tag": "v1.2.0-beta1",
  "message": "Upgraded to image v1.2.0-beta1 successfully.",
  "conditions": [
    {
      "type": "Available",
      "status": "True",
      "reason": "ReplicaScaled",
      "message": "Scaled to 4 replicas",
      "last_transition_time": "2026-09-15T00:25:12Z"
    },
    {
      "type": "GpuAllocated",
      "status": "True",
      "reason": "GpuConfigured",
      "message": "Assigned 1x nvidia.com/gpu accelerators",
      "last_transition_time": "2026-09-15T00:25:12Z"
    }
  ]
}
```

---

### 2.4 Trigger On-Demand Backup Job
* **Endpoint:** `POST /v1/admin/operator/clusters/{cluster_name}/backup`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Query Parameters:**
  - `namespace` *(optional, string, default: "default")*: Cluster namespace.
* **Response (202 Accepted):**
```json
{
  "status": "Accepted",
  "job_id": "job-backup-retriever-prod-a1b2c3d4",
  "cluster": "retriever-prod",
  "namespace": "retriever-system"
}
```
* **Errors:**
  - `404 Not Found`: If specified cluster is not registered.
