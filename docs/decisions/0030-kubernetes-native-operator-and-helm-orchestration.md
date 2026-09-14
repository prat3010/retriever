# ADR-030: Kubernetes Native Operator & Production Helm 3 Cloud-Native Orchestration

**Status:** Accepted  
**Date:** 2026-09-15  
**Deciders:** Principal Infrastructure Architects, Cloud-Native Engineering Leads, SRE Directors  
**Consulted:** Enterprise DevOps Teams, Platform Security Architects  
**Informed:** Enterprise Clients, Open-Source Community  

---

## 1. Context and Problem Statement

Deploying Retriever in enterprise cloud environments requires orchestrating multiple interdependent components:
- Stateless multi-replica FastAPI backend services with HorizontalPodAutoscalers.
- Next.js Web Studio frontend services with Ingress routing and Let's Encrypt TLS termination.
- Stateful persistence stores: PostgreSQL 16 with `pgvector` extension and Redis 7 with AOF persistence.
- Database migration lifecycles (`alembic upgrade head`) before new replicas accept traffic.
- Specialized hardware scheduling (NVIDIA CUDA / TensorCore GPUs).
- Disaster recovery backup dispatches to S3-compatible cloud storage.

Prior to Milestone 112, deployment was handled via local Docker Compose or bare-metal systemd scripts. Enterprise organizations on AWS EKS, GCP GKE, and Azure AKS require declarative, production-grade cloud-native primitives.

To resolve this, Retriever introduced **Platform Battery #28: Kubernetes Native Operator & Helm Cluster Orchestrator** (`v1.2.0-alpha1`, Milestone 112).

---

## 2. Decision Drivers

- **Hexagonal Operator Design:** Rather than coupling the operator to heavy external Go-based runtimes (Kubebuilder) or complex Python frameworks (Kopf) with intrusive sidecars, we implemented pure domain abstractions in `src/domain/abstractions/operator.py` (`RetrieverClusterSpec`, `RetrieverClusterStatus`, `ClusterGpuConfig`, `ClusterBackupPolicy`, `IKubernetesClient`).
- **Level-Triggered State Reconciliation:** The reconciler loop is level-triggered rather than edge-triggered: it observes the current state versus the desired `RetrieverClusterSpec`, driving state machine transitions (`Pending` $\rightarrow$ `Provisioning` $\rightarrow$ `Running`) regardless of missed intermediate events.
- **Zero-Downtime Rolling Upgrades:** When `spec.image_tag` diverges from `status.active_image_tag`, the reconciler marks the phase as `Upgrading`, rolls out updated pods, verifies readiness probes on `/health`, and safely transitions back to `Running`.
- **Hardware-Aware GPU Scheduling:** Automatically injects node affinity, tolerations, and resource limits (`nvidia.com/gpu`) for GPU-accelerated embedding and reranking workloads when `spec.gpu.enabled = true`.
- **Bundled vs External Persistence Flexibility:** The official Helm 3 chart bundles PostgreSQL 16 + pgvector and Redis 7 StatefulSets with persistent volume claims by default, while supporting external managed cloud databases (AWS RDS, Supabase, GCP Cloud SQL) via simple `values.yaml` overrides.

---

## 3. Decision Outcome

1. **Production Helm 3 Chart (`deploy/helm/retriever/`):**
   - Full templating with `_helpers.tpl`, `api-deployment.yaml`, `web-deployment.yaml`, `hpa.yaml`, `ingress.yaml`, `pgvector-statefulset.yaml`, `redis-statefulset.yaml`, `configmap.yaml`, `secret.yaml`, and pre-install migration hook `migration-job.yaml`.
2. **Kubernetes Custom Resource Definition (`deploy/operator/crds/retrieverclusters.retriever.run.crd.yaml`):**
   - Custom API group `retriever.run/v1alpha1`, `kind: RetrieverCluster`, with OpenAPI v3 schema validation, subresources (`status`, `scale`), and `kubectl get rc` printer columns.
3. **Reconciler Adapter (`apps/api/src/adapters/operator/cluster_reconciler.py`):**
   - `InMemoryKubernetesClient(IKubernetesClient)` enabling in-memory testing without a live cluster.
   - `ClusterReconciler` managing cluster lifecycle, rolling updates, and S3 backup dispatches.
4. **Admin REST Control Plane (`apps/api/src/routers/admin.py`):**
   - `GET /v1/admin/operator/status`
   - `GET /v1/admin/operator/clusters`
   - `POST /v1/admin/operator/reconcile`
   - `POST /v1/admin/operator/clusters/{cluster_name}/backup`
5. **Platform Battery #28 Registration:**
   - Cataloged `kubernetes_native_operator` in `BatteryService` under `SYSTEM_EXTENSIBILITY` (28 platform batteries).

### Positive Consequences
- **Enterprise Turnkey Deployment:** Full multi-tier cluster installation with a single `helm install` command.
- **Self-Healing Infrastructure:** Autonomous recovery, rolling upgrades, and automated backup schedules without manual DevOps intervention.
- **100% Hexagonal Integrity:** In-memory client permits comprehensive automated Pytest coverage without requiring external minikube or kind clusters in CI.
