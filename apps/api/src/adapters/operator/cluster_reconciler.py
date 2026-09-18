"""Kubernetes Native Operator Reconciler and In-Memory Controller Implementation."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from src.domain.abstractions.operator import (
    ClusterCondition,
    IKubernetesClient,
    RetrieverClusterSpec,
    RetrieverClusterStatus,
)

logger = logging.getLogger(__name__)


class InMemoryKubernetesClient(IKubernetesClient):
    """In-memory Kubernetes API client for level-triggered reconciliation testing and standalone operations."""

    def __init__(self) -> None:
        self.clusters: dict[str, dict[str, Any]] = {}
        self.statuses: dict[str, RetrieverClusterStatus] = {}
        self.deployments: dict[str, dict[str, Any]] = {}
        self.backup_jobs: list[dict[str, Any]] = []

    def _key(self, name: str, namespace: str) -> str:
        return f"{namespace}/{name}"

    def register_cluster(self, manifest: dict[str, Any]) -> None:
        """Register a RetrieverCluster manifest into in-memory store."""
        metadata = manifest.get("metadata", {})
        name = metadata.get("name", "retriever-cluster")
        namespace = metadata.get("namespace", "default")
        key = self._key(name, namespace)
        self.clusters[key] = manifest

    async def list_clusters(self, namespace: str | None = None) -> list[dict[str, Any]]:
        if namespace:
            return [
                c for k, c in self.clusters.items()
                if c.get("metadata", {}).get("namespace") == namespace
            ]
        return list(self.clusters.values())

    async def get_cluster(self, name: str, namespace: str) -> dict[str, Any] | None:
        return self.clusters.get(self._key(name, namespace))

    async def update_cluster_status(
        self, name: str, namespace: str, status: RetrieverClusterStatus
    ) -> None:
        key = self._key(name, namespace)
        self.statuses[key] = status
        if key in self.clusters:
            self.clusters[key]["status"] = status.model_dump()

    async def reconcile_deployment(self, spec: RetrieverClusterSpec) -> dict[str, Any]:
        key = self._key(spec.name, spec.namespace)
        deployment_record = {
            "name": f"{spec.name}-api",
            "namespace": spec.namespace,
            "replicas": spec.replicas,
            "web_replicas": spec.web_replicas,
            "image": f"ghcr.io/prateeksharma/retriever-api:{spec.image_tag}",
            "gpu_enabled": spec.gpu.enabled,
            "gpu_type": spec.gpu.gpu_type if spec.gpu.enabled else None,
            "gpu_count": spec.gpu.gpu_count if spec.gpu.enabled else 0,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.deployments[key] = deployment_record
        return deployment_record

    async def trigger_backup_job(self, spec: RetrieverClusterSpec) -> str:
        job_id = f"job-backup-{spec.name}-{uuid.uuid4().hex[:8]}"
        job_record = {
            "job_id": job_id,
            "cluster_name": spec.name,
            "namespace": spec.namespace,
            "schedule": spec.backup_policy.schedule,
            "s3_bucket": spec.backup_policy.s3_bucket or "retriever-backups-default",
            "created_at": datetime.now(UTC).isoformat(),
            "status": "Completed",
        }
        self.backup_jobs.append(job_record)
        return job_id


class ClusterReconciler:
    """Level-triggered Kubernetes Operator Reconciler for RetrieverCluster CRDs."""

    def __init__(self, client: IKubernetesClient) -> None:
        self.client = client

    def _create_condition(
        self,
        cond_type: str,
        status: str,
        reason: str,
        message: str,
    ) -> ClusterCondition:
        return ClusterCondition(
            type=cond_type,
            status="True" if status == "True" else ("False" if status == "False" else "Unknown"),
            last_transition_time=datetime.now(UTC).isoformat(),
            reason=reason,
            message=message,
        )

    async def reconcile(
        self,
        spec: RetrieverClusterSpec,
        current_status: RetrieverClusterStatus | None = None,
    ) -> RetrieverClusterStatus:
        """Reconcile target cluster state toward the desired specification.

        Handles:
        - Provisioning initialization
        - Rolling updates upon image tag divergence
        - Dynamic horizontal replica scaling
        - GPU affinity and node allocation conditions
        - Backup policy state verification
        """
        now_iso = datetime.now(UTC).isoformat()

        # 1. Initialize status if first reconciliation cycle
        if current_status is None:
            current_status = RetrieverClusterStatus(
                phase="Pending",
                ready_replicas=0,
                desired_replicas=spec.replicas,
                web_ready_replicas=0,
                database_healthy=False,
                active_image_tag="",
                last_reconciled_at=now_iso,
                message="RetrieverCluster resource detected. Beginning reconciliation.",
            )

        new_status = current_status.model_copy(deep=True)
        new_status.desired_replicas = spec.replicas
        new_status.last_reconciled_at = now_iso
        conditions_map: dict[str, ClusterCondition] = {c.type: c for c in new_status.conditions}

        # 2. State machine transitions
        if new_status.phase == "Pending":
            # Transition to Provisioning
            new_status.phase = "Provisioning"
            new_status.message = "Provisioning database statefulsets and network services."
            conditions_map["Progressing"] = self._create_condition(
                "Progressing", "True", "ProvisioningStarted", "Deploying database and API pods"
            )
            conditions_map["Available"] = self._create_condition(
                "Available", "False", "PodsStarting", "FastAPI replicas not yet healthy"
            )

            # Reconcile underlying deployment
            await self.client.reconcile_deployment(spec)

            # Database becomes healthy after statefulset creation
            new_status.database_healthy = True
            new_status.ready_replicas = spec.replicas
            new_status.web_ready_replicas = spec.web_replicas
            new_status.active_image_tag = spec.image_tag
            new_status.phase = "Running"
            new_status.message = "All pods healthy and serving traffic."

            conditions_map["DatabaseReady"] = self._create_condition(
                "DatabaseReady", "True", "PgvectorHealthy", f"pgvector PVC size {spec.postgres_pvc_size} mounted"
            )
            conditions_map["Progressing"] = self._create_condition(
                "Progressing", "False", "ProvisioningComplete", "Cluster successfully provisioned"
            )
            conditions_map["Available"] = self._create_condition(
                "Available", "True", "AllPodsReady", f"{new_status.ready_replicas}/{spec.replicas} replicas available"
            )

        elif new_status.phase == "Running":
            # Check for Image Tag Update (Rolling Upgrade)
            if new_status.active_image_tag and new_status.active_image_tag != spec.image_tag:
                logger.info(
                    "Rolling upgrade triggered from %s to %s for %s",
                    new_status.active_image_tag,
                    spec.image_tag,
                    spec.name,
                )
                new_status.phase = "Upgrading"
                new_status.message = f"Upgrading image from {new_status.active_image_tag} to {spec.image_tag}"
                conditions_map["Progressing"] = self._create_condition(
                    "Progressing", "True", "RollingUpgrade", f"Upgrading to image tag {spec.image_tag}"
                )

                # Deploy new image
                await self.client.reconcile_deployment(spec)
                new_status.active_image_tag = spec.image_tag
                new_status.phase = "Running"
                new_status.message = f"Upgraded to image {spec.image_tag} successfully."
                conditions_map["Progressing"] = self._create_condition(
                    "Progressing", "False", "UpgradeComplete", f"Now running {spec.image_tag}"
                )
            else:
                # Standard replica scaling check
                if new_status.ready_replicas != spec.replicas or new_status.web_ready_replicas != spec.web_replicas:
                    logger.info("Scaling replicas to %d for %s", spec.replicas, spec.name)
                    await self.client.reconcile_deployment(spec)
                    new_status.ready_replicas = spec.replicas
                    new_status.web_ready_replicas = spec.web_replicas
                    conditions_map["Available"] = self._create_condition(
                        "Available", "True", "ReplicaScaled", f"Scaled to {spec.replicas} replicas"
                    )

        elif new_status.phase == "Upgrading":
            await self.client.reconcile_deployment(spec)
            new_status.active_image_tag = spec.image_tag
            new_status.phase = "Running"
            new_status.message = f"Upgraded to image {spec.image_tag}."
            conditions_map["Progressing"] = self._create_condition(
                "Progressing", "False", "UpgradeFinished", "Rolling update complete"
            )

        # 3. GPU Evaluation
        if spec.gpu.enabled:
            conditions_map["GpuAllocated"] = self._create_condition(
                "GpuAllocated",
                "True",
                "GpuConfigured",
                f"Assigned {spec.gpu.gpu_count}x {spec.gpu.gpu_type} accelerators",
            )
        else:
            conditions_map["GpuAllocated"] = self._create_condition(
                "GpuAllocated",
                "False",
                "GpuDisabled",
                "Standard CPU worker nodes utilized",
            )

        # 4. Backup Evaluation
        if spec.backup_policy.enabled:
            conditions_map["BackupConfigured"] = self._create_condition(
                "BackupConfigured",
                "True",
                "BackupScheduleActive",
                f"Cron schedule: {spec.backup_policy.schedule}, retention: {spec.backup_policy.retention_days}d",
            )
        else:
            conditions_map["BackupConfigured"] = self._create_condition(
                "BackupConfigured",
                "False",
                "BackupDisabled",
                "Automated nightly backups disabled",
            )

        new_status.conditions = list(conditions_map.values())

        # Persist updated status
        await self.client.update_cluster_status(spec.name, spec.namespace, new_status)
        return new_status

    async def trigger_manual_backup(self, spec: RetrieverClusterSpec) -> str:
        """Dispatch a manual vector & WAL backup job."""
        job_id = await self.client.trigger_backup_job(spec)
        cluster_data = await self.client.get_cluster(spec.name, spec.namespace)
        if cluster_data and "status" in cluster_data:
            current_status = RetrieverClusterStatus(**cluster_data["status"])
            current_status.last_backup_at = datetime.now(UTC).isoformat()
            await self.client.update_cluster_status(spec.name, spec.namespace, current_status)
        return job_id
