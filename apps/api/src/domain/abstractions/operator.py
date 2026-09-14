"""Domain abstractions and ports for Kubernetes Native Operator and Cluster Management."""

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

ClusterPhase = Literal["Pending", "Provisioning", "Running", "Degraded", "Upgrading", "Failed"]


class ClusterGpuConfig(BaseModel):
    enabled: bool = False
    gpu_type: str = "nvidia.com/gpu"
    gpu_count: int = 1
    node_selector: dict[str, str] = Field(default_factory=dict)
    tolerations: list[dict[str, Any]] = Field(default_factory=list)


class ClusterBackupPolicy(BaseModel):
    enabled: bool = True
    schedule: str = "0 2 * * *"  # Cron format (nightly at 2:00 AM)
    retention_days: int = 30
    s3_bucket: str | None = None
    s3_prefix: str = "cluster-backups"


class RetrieverClusterSpec(BaseModel):
    name: str = Field(..., min_length=1, max_length=63, description="DNS-1123 label for cluster")
    namespace: str = Field(default="default", min_length=1, max_length=63)
    replicas: int = Field(default=2, ge=1, le=50, description="FastAPI API pod replica count")
    web_replicas: int = Field(default=1, ge=0, le=20, description="Next.js Web Studio replica count")
    image_tag: str = Field(default="v1.2.0-alpha1", description="Retriever image tag")
    postgres_pvc_size: str = Field(default="20Gi", description="PersistentVolumeClaim capacity for pgvector")
    postgres_storage_class: str | None = None
    gpu: ClusterGpuConfig = Field(default_factory=ClusterGpuConfig)
    backup_policy: ClusterBackupPolicy = Field(default_factory=ClusterBackupPolicy)
    environment_variables: dict[str, str] = Field(default_factory=dict)


class ClusterCondition(BaseModel):
    type: str
    status: Literal["True", "False", "Unknown"]
    last_transition_time: str
    reason: str
    message: str


class RetrieverClusterStatus(BaseModel):
    phase: ClusterPhase = "Pending"
    ready_replicas: int = 0
    desired_replicas: int = 2
    web_ready_replicas: int = 0
    database_healthy: bool = False
    last_backup_at: str | None = None
    last_reconciled_at: str | None = None
    active_image_tag: str = ""
    conditions: list[ClusterCondition] = Field(default_factory=list)
    message: str = "Cluster initialized"


class IKubernetesClient(ABC):
    """Abstract port interface for Kubernetes cluster API interactions."""

    @abstractmethod
    async def list_clusters(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """List RetrieverCluster custom resources."""
        pass

    @abstractmethod
    async def get_cluster(self, name: str, namespace: str) -> dict[str, Any] | None:
        """Fetch single RetrieverCluster custom resource manifest."""
        pass

    @abstractmethod
    async def update_cluster_status(
        self, name: str, namespace: str, status: RetrieverClusterStatus
    ) -> None:
        """Update .status subresource on target RetrieverCluster."""
        pass

    @abstractmethod
    async def reconcile_deployment(self, spec: RetrieverClusterSpec) -> dict[str, Any]:
        """Apply or scale Kubernetes Deployment resources for API and Web components."""
        pass

    @abstractmethod
    async def trigger_backup_job(self, spec: RetrieverClusterSpec) -> str:
        """Dispatch a Kubernetes Job executing database WAL and vector backup."""
        pass
