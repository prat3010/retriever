"""FastAPI Router for NVIDIA NeMo Guardrails & Multi-Turn Conversational Safety (M94).

Provides tenant-scoped and administrative REST APIs for managing Colang flows,
fast-path input validation, output factual grounding, live flow testing,
and real-time safety violation telemetry.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.abstractions.guardrails import (
    GuardrailCheckResult,
    GuardrailExecutionMode,
    GuardrailRule,
    TenantGuardrailsConfig,
)

# Global Guardrails Router (templates & admin)
router = APIRouter(
    prefix="/v1/guardrails",
    tags=["guardrails", "safety"],
)

# Tenant-Scoped Guardrails Router
tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/guardrails",
    tags=["guardrails", "safety"],
)


class UpdateGuardrailsConfigPayload(BaseModel):
    """Payload for updating tenant guardrails configuration."""

    mode: GuardrailExecutionMode | None = None
    colang_script: str | None = None
    rules: list[GuardrailRule] | None = None
    pii_redaction_enabled: bool | None = None
    competitor_shield_enabled: bool | None = None
    competitor_names: list[str] | None = None
    brand_tone: str | None = None
    grounding_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    fallback_response: str | None = None


class ValidateInputPayload(BaseModel):
    """Payload for evaluating a query through input guardrails."""

    query: str
    conversation_history: list[dict[str, str]] | None = None


class ValidateOutputPayload(BaseModel):
    """Payload for evaluating assistant response through output grounding guardrails."""

    query: str
    generated_response: str
    retrieved_contexts: list[str] = Field(default_factory=list)


class TestFlowPayload(BaseModel):
    """Payload for testing an interactive prompt against Colang flows."""

    query: str
    custom_colang: str | None = None


# ── Global Endpoints ─────────────────────────────────────────────────────────

@router.get("/templates")
async def get_guardrail_templates() -> dict[str, Any]:
    """Retrieve pre-packaged enterprise Colang flow templates."""
    service = container.nemo_guardrail_service
    return service.get_templates()


@router.get("/overview", dependencies=[Depends(verify_admin_key)])
async def get_global_guardrails_overview() -> dict[str, Any]:
    """Admin endpoint returning global guardrail engine status and battery info."""
    battery_service = container.battery_service
    platform_batteries = battery_service.get_platform_batteries()
    nemo_battery = next(
        (b for b in platform_batteries.batteries if b.id == "nemo_conversational_guardrails"),
        None,
    )
    return {
        "engine": "NVIDIA NeMo Guardrails (Colang Runtime)",
        "version": "v0.79.0 (Milestone 94)",
        "battery_status": nemo_battery.status.value if nemo_battery else "active",
        "supported_modes": [m.value for m in GuardrailExecutionMode],
        "fast_path_latency": "<20ms",
        "grounding_latency": "~80ms",
    }


# ── Tenant-Scoped Endpoints ──────────────────────────────────────────────────

@tenant_router.get("/config", response_model=TenantGuardrailsConfig)
async def get_tenant_guardrails_config(tenantId: str) -> TenantGuardrailsConfig:
    """Retrieve active guardrail configuration and Colang flows for a tenant."""
    service = container.nemo_guardrail_service
    return service.get_tenant_config(tenantId)


@tenant_router.put(
    "/config",
    response_model=TenantGuardrailsConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def update_tenant_guardrails_config(
    tenantId: str, payload: UpdateGuardrailsConfigPayload
) -> TenantGuardrailsConfig:
    """Update Colang flows, execution mode, or safety constraints for a tenant."""
    service = container.nemo_guardrail_service
    updates = payload.model_dump(exclude_unset=True)
    return service.update_tenant_config(tenantId, updates)


@tenant_router.post("/validate-input", response_model=GuardrailCheckResult)
async def validate_query_input(
    tenantId: str, payload: ValidateInputPayload
) -> GuardrailCheckResult:
    """Execute fast-path and Colang input screening on a candidate query."""
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query string cannot be empty.",
        )
    service = container.nemo_guardrail_service
    return await service.evaluate_input(
        tenant_id=tenantId,
        query=payload.query,
        conversation_history=payload.conversation_history,
    )


@tenant_router.post("/validate-output", response_model=GuardrailCheckResult)
async def validate_response_output(
    tenantId: str, payload: ValidateOutputPayload
) -> GuardrailCheckResult:
    """Evaluate generated assistant response for factual context grounding."""
    service = container.nemo_guardrail_service
    return await service.evaluate_output(
        tenant_id=tenantId,
        query=payload.query,
        generated_response=payload.generated_response,
        retrieved_contexts=payload.retrieved_contexts,
    )


@tenant_router.post("/test-flow", response_model=GuardrailCheckResult)
async def test_colang_flow(
    tenantId: str, payload: TestFlowPayload
) -> GuardrailCheckResult:
    """Test a prompt in the sandbox against active or draft Colang rules."""
    service = container.nemo_guardrail_service
    return await service.test_flow(
        tenant_id=tenantId,
        query=payload.query,
        custom_colang=payload.custom_colang,
    )


@tenant_router.get("/telemetry")
async def get_tenant_guardrail_telemetry(tenantId: str) -> dict[str, Any]:
    """Retrieve safety violation logs and audit metrics for a tenant."""
    service = container.nemo_guardrail_service
    return service.get_telemetry(tenantId)
