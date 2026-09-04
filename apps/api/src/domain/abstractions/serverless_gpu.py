"""Serverless GPU & Dynamic vLLM / LoRA Serving Abstractions (M96).

Defines pure domain entities, models, and abstract interfaces for serverless
GPU auto-scaling down to zero, cold-start telemetry, and multi-tenant
dynamic LoRA adapter swapping. Contains zero framework or infrastructure imports.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.domain.abstractions.inference import InferenceRequest, InferenceResponse


class ServerlessProviderType(StrEnum):
    """Supported serverless GPU provider platforms."""

    MODAL = "modal"
    BENTOML = "bentoml"
    VLLM_DIRECT = "vllm_direct"
    TOGETHER = "together"


class ServerlessGpuTier(StrEnum):
    """NVIDIA GPU hardware accelerators supported for serverless inference."""

    T4 = "T4"
    A10G = "A10G"
    L4 = "L4"
    A100_40GB = "A100_40GB"
    A100_80GB = "A100_80GB"
    H100 = "H100"


# Hourly benchmark rates for provisioned 24/7 dedicated GPUs vs serverless active seconds
GPU_HOURLY_RATES: dict[str, float] = {
    ServerlessGpuTier.T4: 0.55,
    ServerlessGpuTier.A10G: 1.00,
    ServerlessGpuTier.L4: 0.80,
    ServerlessGpuTier.A100_40GB: 3.67,
    ServerlessGpuTier.A100_80GB: 4.50,
    ServerlessGpuTier.H100: 6.95,
}


class LoraAdapterMetadata(BaseModel):
    """Metadata describing a fine-tuned LoRA adapter scoped to a tenant."""

    adapter_id: str = Field(..., description="Unique UUID or slug identifier for the LoRA adapter")
    tenant_id: str = Field(..., description="Tenant owning this fine-tuned adapter")
    name: str = Field(..., description="Human-readable name of the adapter")
    base_model: str = Field(
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        description="Foundational base model this adapter is compiled against",
    )
    artifact_uri: str = Field(
        ...,
        description="S3, MinIO, or Hugging Face URI storing adapter_model.safetensors and adapter_config.json",
    )
    rank: int = Field(default=16, description="LoRA rank dimension (r)")
    alpha: float = Field(default=32.0, description="LoRA scaling factor (alpha)")
    target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"],
        description="Attention / MLP projection layers targeted by the LoRA adapter",
    )
    is_active: bool = Field(
        default=False,
        description="Whether this adapter is currently hot-activated for tenant inference",
    )
    adapter_type: str = Field(
        default="llm",
        description="Type of adapter: 'llm' for generative weights or 'embedding' for vector residual weights",
    )
    created_at: str = Field(default="", description="ISO timestamp of adapter creation")
    description: str = Field(default="", description="Operational notes and fine-tuning domain context")


class ServerlessDeploymentStatus(BaseModel):
    """Operational status of the serverless GPU serving cluster."""

    provider: ServerlessProviderType
    cluster_status: str = "ready"  # "ready", "cold", "scaling_up", "scaling_down", "unhealthy"
    active_containers: int = 0
    min_containers: int = 0
    max_containers: int = 5
    scaledown_window_sec: int = 300
    base_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    gpu_tier: ServerlessGpuTier = ServerlessGpuTier.A10G
    loaded_lora_count: int = 0
    last_active_timestamp: str | None = None
    last_boot_latency_ms: int | None = None
    endpoint_url: str | None = None


class WarmBootMetrics(BaseModel):
    """Telemetry captured during container warm-up or cold-start invocation."""

    is_cold_boot: bool = False
    handshake_latency_ms: int = 0
    inference_ttft_ms: int = 0
    total_latency_ms: int = 0
    container_id: str | None = None
    provider: ServerlessProviderType = ServerlessProviderType.MODAL


class ServerlessCostComparison(BaseModel):
    """Empirical cost savings calculation of serverless scale-to-zero vs dedicated 24/7 GPU."""

    dedicated_monthly_cost_usd: float
    serverless_monthly_cost_usd: float
    monthly_savings_usd: float
    savings_percentage: float
    active_hours: float
    idle_hours_saved: float
    gpu_tier: ServerlessGpuTier = ServerlessGpuTier.A10G


class ServerlessGpuClientProtocol(ABC):
    """Port for communicating with serverless GPU clusters and vLLM runtimes."""

    @abstractmethod
    async def check_deployment_status(self) -> ServerlessDeploymentStatus:
        """Query cluster state, active replicas, and loaded adapters."""
        pass

    @abstractmethod
    async def probe_cold_start(self) -> WarmBootMetrics:
        """Execute a lightweight probe to measure cold-start / warm-boot latency."""
        pass

    @abstractmethod
    async def execute_serverless_completion(
        self,
        request: InferenceRequest,
        configuration: dict[str, Any],
        lora_adapter: LoraAdapterMetadata | None = None,
    ) -> InferenceResponse:
        """Execute synchronous inference dispatching to the serverless container."""
        pass

    @abstractmethod
    async def execute_serverless_stream(
        self,
        request: InferenceRequest,
        configuration: dict[str, Any],
        lora_adapter: LoraAdapterMetadata | None = None,
    ) -> Any:
        """Execute streaming inference, yielding SSE delta tokens."""
        pass

    @abstractmethod
    def calculate_cost_savings(
        self,
        active_compute_seconds: float,
        gpu_tier: ServerlessGpuTier = ServerlessGpuTier.A10G,
    ) -> ServerlessCostComparison:
        """Calculate real-world dollar savings achieved through scale-to-zero."""
        pass


class TenantLoraRegistryProtocol(ABC):
    """Port for persisting and resolving tenant-specific LoRA adapters."""

    @abstractmethod
    async def register_adapter(
        self, tenant_id: str, adapter: LoraAdapterMetadata
    ) -> LoraAdapterMetadata:
        """Register a new fine-tuned LoRA adapter for a tenant."""
        pass

    @abstractmethod
    async def get_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> LoraAdapterMetadata | None:
        """Retrieve a LoRA adapter by ID, scoped strictly to tenant."""
        pass

    @abstractmethod
    async def list_adapters(
        self, tenant_id: str, adapter_type: str | None = None
    ) -> list[LoraAdapterMetadata]:
        """List all LoRA adapters registered for a tenant."""
        pass

    @abstractmethod
    async def activate_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> LoraAdapterMetadata:
        """Hot-activate a LoRA adapter for a tenant, deactivating existing ones of same type."""
        pass

    @abstractmethod
    async def deactivate_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> bool:
        """Deactivate a specified LoRA adapter."""
        pass

    @abstractmethod
    async def delete_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> bool:
        """Delete an adapter record for a tenant."""
        pass

    @abstractmethod
    async def get_active_adapter(
        self, tenant_id: str, adapter_type: str = "llm"
    ) -> LoraAdapterMetadata | None:
        """Fetch the currently active adapter for the tenant."""
        pass
