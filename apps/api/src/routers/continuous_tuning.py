"""FastAPI Router for Continuous DPO / ORPO Preference Fine-Tuning Pipeline (M120).

Exposes:
- Battery #35 operational health probe (`/v1/tuning/health`)
- Preference harvesting & dataset collection (`/v1/tenants/{tenantId}/tuning/pairs`)
- Tenant tuning configuration & auto-threshold settings (`/v1/tenants/{tenantId}/tuning/config`)
- Continuous DPO/ORPO training jobs & convergence telemetry (`/v1/tenants/{tenantId}/tuning/jobs`)
- Adapter promotion and 1-click rollback (`/v1/tenants/{tenantId}/tuning/jobs/...`)
- Interactive mathematical loss simulation endpoint (`/v1/tuning/math/simulate`)
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from src.container import container
from src.domain.abstractions.dpo_orpo_tuning import (
    ContinuousTuningConfig,
    PreferencePair,
    TuningHyperparameters,
    TuningJob,
    TuningMathSimulationResult,
    TuningObjective,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Continuous DPO/ORPO Tuning Pipeline"])


# --- Request/Response DTOs ---

class TuningHealthResponse(BaseModel):
    """Operational status and parameters for Platform Battery #35."""

    battery_id: str = "continuous_preference_tuning"
    status: str = "healthy"
    category: str = "ML_INTELLIGENCE"
    supported_objectives: list[str] = Field(default_factory=lambda: ["dpo", "orpo", "kto"])
    default_base_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    auto_trigger_threshold: int = 50
    evaluation_gate_accuracy_threshold: float = 0.75
    instant_rollback_supported: bool = True


class HarvestPreferenceRequest(BaseModel):
    """Payload for harvesting or recording a preference sample."""

    prompt: str = Field(..., min_length=3, description="User query or context prompt (x)")
    winning_response: str = Field(..., min_length=1, description="Chosen/upvoted completion (y_w)")
    losing_response: str = Field(..., min_length=1, description="Rejected/downvoted completion (y_l)")
    source_message_id: str | None = Field(default=None, description="Optional linked chat message UUID")
    feedback_rating: int = Field(default=1, description="Feedback score (+1 upvote, -1 downvote)")
    tags: list[str] = Field(default_factory=list, description="Descriptive tags (e.g. ['factual', 'concise'])")


class PreferenceListResponse(BaseModel):
    """Paginated response containing preference pairs."""

    items: list[PreferencePair]
    total: int
    limit: int
    offset: int


class TriggerJobRequest(BaseModel):
    """Payload for manually dispatching a preference fine-tuning job."""

    objective: TuningObjective = Field(default=TuningObjective.DPO, description="Alignment objective (dpo, orpo)")
    hyperparameters: TuningHyperparameters | None = Field(
        default=None, description="Optional custom hyperparameter overrides"
    )


class MathSimulationRequest(BaseModel):
    """Parameters for evaluating DPO vs ORPO mathematical formulation."""

    prompt: str = Field(default="What is your return policy?", description="Context prompt")
    beta: float = Field(default=0.1, ge=0.01, le=1.0, description="DPO temperature beta")
    lambda_orpo: float = Field(default=0.1, ge=0.01, le=1.0, description="ORPO lambda parameter")
    pi_theta_win_prob: float = Field(default=0.85, ge=0.01, le=0.99, description="P_theta(y_w | x)")
    pi_ref_win_prob: float = Field(default=0.50, ge=0.01, le=0.99, description="P_ref(y_w | x)")
    pi_theta_lose_prob: float = Field(default=0.15, ge=0.01, le=0.99, description="P_theta(y_l | x)")
    pi_ref_lose_prob: float = Field(default=0.50, ge=0.01, le=0.99, description="P_ref(y_l | x)")


# --- Route Handlers ---

@router.get(
    "/v1/tuning/health",
    response_model=TuningHealthResponse,
    summary="Battery #35 Operational Health Probe",
)
def get_tuning_health() -> TuningHealthResponse:
    """Check status of continuous tuning workers and Battery #35 capabilities."""
    return TuningHealthResponse()


@router.get(
    "/v1/tenants/{tenant_id}/tuning/config",
    response_model=ContinuousTuningConfig,
    summary="Get Tenant Continuous Tuning Configuration",
)
def get_tenant_tuning_config(
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> ContinuousTuningConfig:
    """Retrieve tenant tuning settings, active LoRA adapter ID, and harvest buffer count."""
    adapter = container.continuous_tuning_adapter
    return adapter.get_tuning_config(tenant_id)


@router.put(
    "/v1/tenants/{tenant_id}/tuning/config",
    response_model=ContinuousTuningConfig,
    summary="Update Tenant Continuous Tuning Configuration",
)
def update_tenant_tuning_config(
    config: ContinuousTuningConfig,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> ContinuousTuningConfig:
    """Persist updated auto-trigger threshold or hyperparameter settings."""
    if config.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route tenant_id '{tenant_id}' does not match body tenant_id '{config.tenant_id}'",
        )
    adapter = container.continuous_tuning_adapter
    return adapter.update_tuning_config(tenant_id, config)


@router.get(
    "/v1/tenants/{tenant_id}/tuning/pairs",
    response_model=PreferenceListResponse,
    summary="List Harvested Preference Pairs",
)
def list_preference_pairs(
    tenant_id: str = Path(..., description="Tenant identifier"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PreferenceListResponse:
    """List preference samples collected for a tenant."""
    adapter = container.continuous_tuning_adapter
    items, total = adapter.list_preference_pairs(tenant_id, limit=limit, offset=offset)
    return PreferenceListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/v1/tenants/{tenant_id}/tuning/pairs",
    response_model=PreferencePair,
    status_code=status.HTTP_201_CREATED,
    summary="Harvest or Ingest Preference Pair",
)
def harvest_preference_pair(
    req: HarvestPreferenceRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> PreferencePair:
    """Ingest a validated preference pair into tenant buffer."""
    pair = PreferencePair(
        pair_id=f"pair_{uuid.uuid4().hex[:12]}",
        tenant_id=tenant_id,
        prompt=req.prompt,
        winning_response=req.winning_response,
        losing_response=req.losing_response,
        source_message_id=req.source_message_id,
        feedback_rating=req.feedback_rating,
        tags=req.tags,
        is_verified=True,
        created_at=datetime.now(UTC).isoformat(),
    )
    adapter = container.continuous_tuning_adapter
    return adapter.harvest_preference_pair(tenant_id, pair)


@router.delete(
    "/v1/tenants/{tenant_id}/tuning/pairs/{pair_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Preference Pair",
)
def delete_preference_pair(
    tenant_id: str = Path(..., description="Tenant identifier"),
    pair_id: str = Path(..., description="Preference pair UUID"),
) -> None:
    """Remove a preference sample from the tenant's training buffer."""
    adapter = container.continuous_tuning_adapter
    success = adapter.delete_preference_pair(tenant_id, pair_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preference pair {pair_id} not found for tenant {tenant_id}",
        )


@router.post(
    "/v1/tenants/{tenant_id}/tuning/jobs",
    response_model=TuningJob,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch Continuous Preference Fine-Tuning Job",
)
def trigger_tuning_job(
    req: TriggerJobRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> TuningJob:
    """Dispatch a DPO or ORPO fine-tuning job over buffered tenant samples."""
    adapter = container.continuous_tuning_adapter
    job = adapter.trigger_tuning_job(tenant_id, objective=req.objective, hyperparams=req.hyperparameters)
    return job


@router.get(
    "/v1/tenants/{tenant_id}/tuning/jobs",
    response_model=list[TuningJob],
    summary="List Tuning Jobs History",
)
def list_tuning_jobs(
    tenant_id: str = Path(..., description="Tenant identifier"),
    limit: int = Query(20, ge=1, le=100),
) -> list[TuningJob]:
    """Retrieve history of tuning jobs executed for this tenant."""
    adapter = container.continuous_tuning_adapter
    return adapter.list_tuning_jobs(tenant_id, limit=limit)


@router.get(
    "/v1/tenants/{tenant_id}/tuning/jobs/{job_id}",
    response_model=TuningJob,
    summary="Get Tuning Job Details & Convergence Curve",
)
def get_tuning_job(
    tenant_id: str = Path(..., description="Tenant identifier"),
    job_id: str = Path(..., description="Job identifier"),
) -> TuningJob:
    """Get job progress, loss telemetry steps, and evaluation gate result."""
    adapter = container.continuous_tuning_adapter
    job = adapter.get_tuning_job(tenant_id, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tuning job {job_id} not found for tenant {tenant_id}",
        )
    return job


@router.post(
    "/v1/tenants/{tenant_id}/tuning/jobs/{job_id}/promote",
    response_model=ContinuousTuningConfig,
    summary="Promote LoRA Adapter to Active Tenant Serving",
)
def promote_tuning_job_adapter(
    tenant_id: str = Path(..., description="Tenant identifier"),
    job_id: str = Path(..., description="Job identifier"),
) -> ContinuousTuningConfig:
    """Hot-swap the completed LoRA adapter from this job into active serving."""
    adapter = container.continuous_tuning_adapter
    try:
        return adapter.promote_adapter(tenant_id, job_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/v1/tenants/{tenant_id}/tuning/rollback",
    response_model=ContinuousTuningConfig,
    summary="1-Click Atomic Rollback to Prior LoRA Adapter",
)
def rollback_adapter(
    tenant_id: str = Path(..., description="Tenant identifier"),
    target_adapter_id: str | None = Query(None, description="Specific prior adapter ID or defaults to previous"),
) -> ContinuousTuningConfig:
    """Instantly roll back tenant model serving to a prior verified checkpoint."""
    adapter = container.continuous_tuning_adapter
    return adapter.rollback_adapter(tenant_id, target_adapter_id=target_adapter_id)


@router.post(
    "/v1/tuning/math/simulate",
    response_model=TuningMathSimulationResult,
    summary="Simulate DPO vs ORPO Loss Math",
)
def simulate_tuning_math(req: MathSimulationRequest) -> TuningMathSimulationResult:
    """Calculate and compare exact DPO and ORPO loss gradients given probability inputs."""
    adapter = container.continuous_tuning_adapter
    return adapter.simulate_tuning_math(
        prompt=req.prompt,
        beta=req.beta,
        lambda_orpo=req.lambda_orpo,
        pi_theta_w=req.pi_theta_win_prob,
        pi_ref_w=req.pi_ref_win_prob,
        pi_theta_l=req.pi_theta_lose_prob,
        pi_ref_l=req.pi_ref_lose_prob,
    )
