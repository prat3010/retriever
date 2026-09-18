# Operational Runbook: Kubernetes Native Operator & Helm Cluster Management

**Runbook ID:** RB-OPS-112  
**Audience:** Platform SREs, Kubernetes Operators, and Cloud Infrastructure Engineers  
**Applies to:** Retriever Cloud-Native Infrastructure (`v1.2.0-alpha1`+, Milestone 112)  

---

## 1. Health Checks & Battery Verification

### 1.1 Verify Platform Battery Status
Confirm that Battery #28 (`kubernetes_native_operator`) is operational:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  http://localhost:8000/v1/admin/operator/status | jq .
```

**Expected Output:**
```json
{
  "status": "healthy",
  "crd_group": "retriever.run",
  "crd_version": "v1alpha1",
  "crd_kind": "RetrieverCluster",
  "helm_chart_version": "1.2.0-alpha1",
  "active_clusters_count": 1,
  "in_memory_reconciler_active": true
}
```

### 1.2 Inspect Live Cluster CRD State
```bash
kubectl get retrieverclusters.retriever.run -A
```
```text
NAMESPACE          NAME             PHASE     DESIRED   READY   VERSION         AGE
retriever-system   retriever-prod   Running   3         3       v1.2.0-alpha1   12d
```

---

## 2. Common Incident Triage & Troubleshooting

### 2.1 Cluster Phase is `Degraded` or Pods in `CrashLoopBackOff`
**Symptoms:**
- `kubectl get rc` reports `PHASE: Degraded`.
- API pods fail liveness/readiness probes on `/health`.

**Diagnostic Steps:**
1. Check conditions on the custom resource:
   ```bash
   kubectl describe retrievercluster retriever-prod -n retriever-system
   ```
2. Check API container logs:
   ```bash
   kubectl logs -l app.kubernetes.io/component=api -n retriever-system --tail=100
   ```
3. Verify PostgreSQL pgvector StatefulSet connectivity:
   ```bash
   kubectl exec -it retriever-prod-postgresql-0 -n retriever-system -- \
     pg_isready -h localhost -p 5432
   ```

**Remediation:**
- If database connection failed, verify credentials secret:
  ```bash
  kubectl get secret retriever-prod-secret -n retriever-system -o yaml
  ```
- Trigger a level-triggered re-reconciliation:
  ```bash
  curl -X POST http://localhost:8000/v1/admin/operator/reconcile \
    -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d '{"name": "retriever-prod", "namespace": "retriever-system", "replicas": 3}'
  ```

---

### 2.2 Storage Volume Expansion (pgvector PVC Full)
**Procedure:**
1. Check PVC storage consumption:
   ```bash
   kubectl get pvc -n retriever-system
   ```
2. Update the `RetrieverCluster` spec capacity:
   ```yaml
   spec:
     postgresPvcSize: "100Gi"
   ```
3. Apply updated manifest:
   ```bash
   kubectl apply -f deploy/operator/samples/retriever_cluster_production.yaml
   ```
   *Note: Ensure the underlying StorageClass supports `allowVolumeExpansion: true`.*

---

## 3. Zero-Downtime Rolling Upgrades & Rollbacks

### 3.1 Initiating an Image Tag Upgrade
To upgrade to a new version without service disruption:
```bash
# Update spec image tag
kubectl patch retrievercluster retriever-prod -n retriever-system \
  --type='json' -p='[{"op": "replace", "path": "/spec/imageTag", "value": "v1.2.0-beta1"}]'
```

Watch the rolling update progress:
```bash
kubectl rollout status deployment/retriever-prod-api -n retriever-system
```

### 3.2 Emergency Rollback
If the new release exhibits regressions:
```bash
kubectl patch retrievercluster retriever-prod -n retriever-system \
  --type='json' -p='[{"op": "replace", "path": "/spec/imageTag", "value": "v1.2.0-alpha1"}]'
```

---

## 4. Disaster Recovery & Backup Management

### 4.1 Trigger Manual On-Demand S3 Backup
Before major database migrations or infrastructure maintenance:
```bash
curl -X POST "http://localhost:8000/v1/admin/operator/clusters/retriever-prod/backup?namespace=retriever-system" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" | jq .
```

### 4.2 Verify Backup Job Execution
```bash
kubectl get jobs -n retriever-system -l app.kubernetes.io/component=backup
```
