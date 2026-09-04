"""FastAPI Router for Enterprise LLM Gateway & Smart Router (M93).

Provides administrative and tenant-scoped REST APIs for model cataloging,
live latency probing, dynamic fallback cascades, and virtual budgets.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.abstractions.gateway import (
    GatewayModelInfo,
    GatewayProbeResult,
    VirtualTenantBudget,
)

# Global Gateway Router
router = APIRouter(
    prefix="/v1/gateway",
    tags=["gateway", "llm"],
)

# Tenant-Scoped Gateway Router
tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/gateway",
    tags=["gateway", "llm"],
    dependencies=[Depends(verify_admin_key)],
)


class UpdateGatewayRoutesPayload(BaseModel):
    primary_model: str = "gemini-2.5-flash"
    fallback_models: list[str] = Field(
        default_factory=lambda: ["openai/gpt-4o-mini", "ollama/qwen2.5:14b"]
    )
    latency_sla_ms: int = 4000
    cooldown_seconds: int = 60
    daily_cost_budget: float | None = None
    monthly_cost_budget: float | None = None
    hard_limit_action: str = "warn_only"  # "warn_only", "block", "downgrade_free_model"
    free_fallback_model: str = "ollama/qwen2.5:14b"
    currency: str = "USD"


@router.get("/models", response_model=list[GatewayModelInfo])
async def list_gateway_models() -> list[GatewayModelInfo]:
    """List all available models in the enterprise gateway catalog."""
    gateway_router = container.gateway_router
    return gateway_router.list_available_models()


@router.post("/probe", response_model=list[GatewayProbeResult], dependencies=[Depends(verify_admin_key)])
async def probe_gateway_providers() -> list[GatewayProbeResult]:
    """Execute live latency and reachability probes across upstream providers."""
    gateway_router = container.gateway_router
    return await gateway_router.probe_providers()


@tenant_router.get("/routes")
async def get_tenant_gateway_routes(tenantId: str) -> dict[str, Any]:
    """Retrieve active model cascade and budget configurations for a tenant."""
    config_service = container.config_service
    tenant_config = await config_service.get_tenant_config(tenantId)
    gw = getattr(tenant_config, "gateway_settings", None)
    bg = getattr(tenant_config, "budget_settings", None)

    return {
        "tenant_id": tenantId,
        "gateway_settings": gw.model_dump() if gw else {},
        "budget_settings": bg.model_dump() if bg else {},
    }


@tenant_router.put("/routes")
async def update_tenant_gateway_routes(
    tenantId: str, payload: UpdateGatewayRoutesPayload
) -> dict[str, Any]:
    """Update dynamic fallback cascade and virtual budget limits for a tenant."""
    config_service = container.config_service
    tenant_config = await config_service.get_tenant_config(tenantId)

    if hasattr(tenant_config, "gateway_settings"):
        tenant_config.gateway_settings.primary_model = payload.primary_model
        tenant_config.gateway_settings.fallback_models = payload.fallback_models
        tenant_config.gateway_settings.latency_sla_ms = payload.latency_sla_ms
        tenant_config.gateway_settings.cooldown_seconds = payload.cooldown_seconds

    if hasattr(tenant_config, "budget_settings"):
        tenant_config.budget_settings.daily_cost_budget = payload.daily_cost_budget
        tenant_config.budget_settings.monthly_cost_budget = payload.monthly_cost_budget
        tenant_config.budget_settings.hard_limit_action = payload.hard_limit_action
        tenant_config.budget_settings.free_fallback_model = payload.free_fallback_model
        tenant_config.budget_settings.currency = payload.currency

    # Persist updated configuration
    try:
        await config_service.update_tenant_config(tenantId, tenant_config)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist gateway configuration: {exc}",
        ) from exc

    return {
        "status": "updated",
        "tenant_id": tenantId,
        "gateway_settings": tenant_config.gateway_settings.model_dump(),
        "budget_settings": tenant_config.budget_settings.model_dump(),
    }


@tenant_router.get("/budget", response_model=VirtualTenantBudget)
async def get_tenant_gateway_budget(tenantId: str) -> VirtualTenantBudget:
    """Calculate and return tenant spend metrics, remaining budget, and model cost attribution."""
    config_service = container.config_service
    budget_repo = container.budget_repo
    tenant_config = await config_service.get_tenant_config(tenantId)
    bg = getattr(tenant_config, "budget_settings", None)

    default_budget = VirtualTenantBudget(
        daily_budget=bg.daily_cost_budget if bg else None,
        monthly_budget=bg.monthly_cost_budget if bg else None,
        hard_limit_action=getattr(bg, "hard_limit_action", "warn_only") if bg else "warn_only",
        free_fallback_model=getattr(bg, "free_fallback_model", "ollama/qwen2.5:14b") if bg else "ollama/qwen2.5:14b",
        currency=getattr(bg, "currency", "USD") if bg else "USD",
    )

    return await budget_repo.get_tenant_budget(tenantId, default_budget)
