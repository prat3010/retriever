"""FastAPI Router for Serverless GPU Serving & LoRA Pipeline (M96).

Provides administrative and tenant-scoped endpoints for serverless GPU cluster
observability, cold-start probing, scale-to-zero cost calculations, and
multi-tenant dynamic LoRA adapter lifecycle management.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.serverless_gpu import (
    LoraAdapterMetadata,
    ServerlessCostComparison,
    ServerlessDeploymentStatus,
    ServerlessGpuTier,
    WarmBootMetrics,
)

# Admin Serverless Management Router
admin_router = APIRouter(
    prefix="/v1/admin/serverless",
    tags=["serverless", "gpu"],
    dependencies=[Depends(verify_admin_key)],
)

# Tenant LoRA Registry Router
tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/lora-adapters",
    tags=["serverless", "lora"],
    dependencies=[Depends(verify_tenant_or_admin)],
)


class RegisterLoraAdapterPayload(BaseModel):
    """Payload for registering a new fine-tuned LoRA adapter."""

    name: str = Field(..., min_length=2, max_length=255, description="Adapter display name")
    base_model: str = Field(
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        description="Base foundational model the adapter targets",
    )
    artifact_uri: str = Field(
        ...,
        description="S3, MinIO, or Hugging Face URI storing weights",
    )
    rank: int = Field(default=16, ge=1, le=128, description="LoRA rank dimension (r)")
    alpha: float = Field(default=32.0, ge=1.0, description="LoRA scaling factor")
    target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"],
        description="Attention projection modules",
    )
    adapter_type: str = Field(
        default="llm",
        description="Type of adapter ('llm' or 'embedding')",
    )
    description: str = Field(default="", description="Domain notes / fine-tuning tags")
    activate_immediately: bool = Field(
        default=False,
        description="Whether to activate immediately after registration",
    )


# --- Admin Serverless Endpoints ---


@admin_router.get("/status", response_model=ServerlessDeploymentStatus)
async def get_serverless_deployment_status() -> ServerlessDeploymentStatus:
    """Retrieve operational status, active containers, and scale-to-zero telemetry."""
    client = container.serverless_gpu_client
    return await client.check_deployment_status()


@admin_router.post("/probe", response_model=WarmBootMetrics)
async def probe_serverless_cold_start() -> WarmBootMetrics:
    """Execute reachability probe to measure handshake, TTFT, and cold-start latency."""
    client = container.serverless_gpu_client
    return await client.probe_cold_start()


@admin_router.get("/cost-savings", response_model=ServerlessCostComparison)
async def get_serverless_cost_savings(
    active_compute_hours: float = Query(
        default=25.0, ge=0.0, le=720.0, description="Estimated active compute hours per month"
    ),
    gpu_tier: ServerlessGpuTier = Query(
        default=ServerlessGpuTier.A10G, description="Target GPU accelerator tier"
    ),
) -> ServerlessCostComparison:
    """Calculate empirical cost savings comparing serverless scale-to-zero against 24/7 dedicated GPUs."""
    client = container.serverless_gpu_client
    active_seconds = active_compute_hours * 3600.0
    return client.calculate_cost_savings(active_seconds, gpu_tier=gpu_tier)


# --- Tenant LoRA Registry Endpoints ---


@tenant_router.get("", response_model=list[LoraAdapterMetadata])
async def list_tenant_lora_adapters(
    tenantId: str,
    adapter_type: str | None = Query(default=None, description="Filter by 'llm' or 'embedding'"),
) -> list[LoraAdapterMetadata]:
    """List all fine-tuned LoRA adapters registered for the specified tenant."""
    repo = container.tenant_lora_repository
    return await repo.list_adapters(tenantId, adapter_type=adapter_type)


@tenant_router.post("", response_model=LoraAdapterMetadata, status_code=status.HTTP_201_CREATED)
async def register_tenant_lora_adapter(
    tenantId: str, payload: RegisterLoraAdapterPayload
) -> LoraAdapterMetadata:
    """Register a new fine-tuned LoRA adapter for the specified tenant."""
    repo = container.tenant_lora_repository
    adapter_id = str(uuid.uuid4())
    metadata = LoraAdapterMetadata(
        adapter_id=adapter_id,
        tenant_id=tenantId,
        name=payload.name,
        base_model=payload.base_model,
        artifact_uri=payload.artifact_uri,
        rank=payload.rank,
        alpha=payload.alpha,
        target_modules=payload.target_modules,
        adapter_type=payload.adapter_type,
        description=payload.description,
        is_active=payload.activate_immediately,
    )

    created = await repo.register_adapter(tenantId, metadata)
    if payload.activate_immediately:
        created = await repo.activate_adapter(tenantId, created.adapter_id)
    return created


@tenant_router.get("/active", response_model=LoraAdapterMetadata | None)
async def get_tenant_active_lora_adapter(
    tenantId: str,
    adapter_type: str = Query(default="llm", description="Adapter type ('llm' or 'embedding')"),
) -> LoraAdapterMetadata | None:
    """Retrieve the currently active LoRA adapter for the tenant."""
    repo = container.tenant_lora_repository
    return await repo.get_active_adapter(tenantId, adapter_type=adapter_type)


@tenant_router.get("/{adapterId}", response_model=LoraAdapterMetadata)
async def get_tenant_lora_adapter(
    tenantId: str, adapterId: str
) -> LoraAdapterMetadata:
    """Retrieve metadata for a specific LoRA adapter."""
    repo = container.tenant_lora_repository
    adapter = await repo.get_adapter(tenantId, adapterId)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LoRA adapter '{adapterId}' not found for tenant '{tenantId}'",
        )
    return adapter


@tenant_router.post("/{adapterId}/activate", response_model=LoraAdapterMetadata)
async def activate_tenant_lora_adapter(
    tenantId: str, adapterId: str
) -> LoraAdapterMetadata:
    """Hot-activate a fine-tuned LoRA adapter for tenant inference."""
    repo = container.tenant_lora_repository
    try:
        return await repo.activate_adapter(tenantId, adapterId)
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LoRA adapter '{adapterId}' not found for tenant '{tenantId}'",
        ) from err


@tenant_router.post("/{adapterId}/deactivate", response_model=dict[str, Any])
async def deactivate_tenant_lora_adapter(
    tenantId: str, adapterId: str
) -> dict[str, Any]:
    """Deactivate a specified LoRA adapter."""
    repo = container.tenant_lora_repository
    success = await repo.deactivate_adapter(tenantId, adapterId)
    return {"tenant_id": tenantId, "adapter_id": adapterId, "deactivated": success}


@tenant_router.delete("/{adapterId}", response_model=dict[str, Any])
async def delete_tenant_lora_adapter(
    tenantId: str, adapterId: str
) -> dict[str, Any]:
    """Delete a LoRA adapter record for the tenant."""
    repo = container.tenant_lora_repository
    deleted = await repo.delete_adapter(tenantId, adapterId)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LoRA adapter '{adapterId}' not found for tenant '{tenantId}'",
        )
    return {"tenant_id": tenantId, "adapter_id": adapterId, "deleted": True}
