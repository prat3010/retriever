"""FastAPI REST router for Continuous Benchmarking & Statistical Regression Gatekeeper (Battery #37)."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from src.container import container
from src.domain.abstractions.benchmark_gatekeeper import (
    BenchmarkItemSample,
    BenchmarkMathSimulationRequest,
    BenchmarkMathSimulationResponse,
    BenchmarkRun,
    BenchmarkSuite,
    GateEvaluationResult,
    GatePolicy,
)

logger = logging.getLogger("retriever.api.benchmarks")

router = APIRouter(tags=["benchmarks"])


class CreateBenchmarkSuiteRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(default="")
    k_cutoff: int = Field(default=10, ge=1, le=50)
    gate_policy: GatePolicy | None = None


class TriggerBenchmarkRunRequest(BaseModel):
    suite_id: str
    checkpoint_or_commit: str = Field(..., min_length=1, max_length=100)
    is_baseline: bool = False
    samples: list[BenchmarkItemSample] | None = None


class EvaluateGateRequest(BaseModel):
    suite_id: str
    candidate_run_id: str
    baseline_run_id: str | None = None


@router.get(
    "/v1/benchmarks/health",
    summary="Benchmark Gatekeeper Health Check",
)
def benchmark_health() -> dict[str, Any]:
    """Verify operational health of Platform Battery #37."""
    return {
        "status": "healthy",
        "battery": "autonomous_benchmark_gatekeeper",
        "battery_id": 37,
        "scipy_engine_available": True,
        "mathematical_engines": [
            "ndcg_at_k",
            "mean_reciprocal_rank",
            "welch_satterthwaite_ttest",
            "rag_triad_groundedness",
        ],
    }


@router.get(
    "/v1/tenants/{tenant_id}/benchmarks/suites",
    response_model=list[BenchmarkSuite],
    summary="List Benchmark Suites",
)
def list_benchmark_suites(
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> list[BenchmarkSuite]:
    """Retrieve all configured benchmark suites for a tenant."""
    adapter = container.benchmark_gatekeeper_adapter
    return adapter.list_suites(tenant_id)


@router.post(
    "/v1/tenants/{tenant_id}/benchmarks/suites",
    response_model=BenchmarkSuite,
    status_code=status.HTTP_201_CREATED,
    summary="Create Benchmark Suite",
)
def create_benchmark_suite(
    payload: CreateBenchmarkSuiteRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> BenchmarkSuite:
    """Register a new benchmark suite with customized SLA regression gates."""
    adapter = container.benchmark_gatekeeper_adapter
    return adapter.create_suite(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        k_cutoff=payload.k_cutoff,
        gate_policy=payload.gate_policy,
    )


@router.get(
    "/v1/tenants/{tenant_id}/benchmarks/runs",
    response_model=list[BenchmarkRun],
    summary="List Benchmark Runs",
)
def list_benchmark_runs(
    tenant_id: str = Path(..., description="Tenant identifier"),
    suite_id: str | None = Query(default=None, description="Optional filter by suite ID"),
) -> list[BenchmarkRun]:
    """Retrieve historical benchmark runs and aggregate summaries."""
    adapter = container.benchmark_gatekeeper_adapter
    return adapter.list_runs(tenant_id, suite_id)


@router.post(
    "/v1/tenants/{tenant_id}/benchmarks/runs",
    response_model=BenchmarkRun,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Benchmark Run",
)
def trigger_benchmark_run(
    payload: TriggerBenchmarkRunRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> BenchmarkRun:
    """Execute or ingest benchmark evaluation samples for a checkpoint or commit."""
    adapter = container.benchmark_gatekeeper_adapter
    try:
        return adapter.trigger_run(
            tenant_id=tenant_id,
            suite_id=payload.suite_id,
            checkpoint_or_commit=payload.checkpoint_or_commit,
            is_baseline=payload.is_baseline,
            samples=payload.samples,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.get(
    "/v1/tenants/{tenant_id}/benchmarks/runs/{run_id}",
    response_model=BenchmarkRun,
    summary="Get Benchmark Run Details",
)
def get_benchmark_run(
    tenant_id: str = Path(..., description="Tenant identifier"),
    run_id: str = Path(..., description="Run identifier"),
) -> BenchmarkRun:
    """Fetch complete benchmark run including item-level evaluation samples."""
    adapter = container.benchmark_gatekeeper_adapter
    run = adapter.get_run(tenant_id, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Benchmark run '{run_id}' not found.")
    return run


@router.post(
    "/v1/tenants/{tenant_id}/benchmarks/evaluate-gate",
    response_model=GateEvaluationResult,
    summary="Evaluate Regression Gate",
)
def evaluate_regression_gate(
    payload: EvaluateGateRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> GateEvaluationResult:
    """Evaluate candidate run against baseline using Two-Sample Welch's t-test and GatePolicy."""
    adapter = container.benchmark_gatekeeper_adapter
    try:
        return adapter.evaluate_gate(
            tenant_id=tenant_id,
            suite_id=payload.suite_id,
            candidate_run_id=payload.candidate_run_id,
            baseline_run_id=payload.baseline_run_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/v1/benchmarks/math/simulate",
    response_model=BenchmarkMathSimulationResponse,
    summary="Simulate Statistical Regression Gate",
)
def simulate_benchmark_math(
    request: BenchmarkMathSimulationRequest,
) -> BenchmarkMathSimulationResponse:
    """Evaluate Two-Sample Welch's t-test, degrees of freedom, p-value and gate verdict."""
    adapter = container.benchmark_gatekeeper_adapter
    return adapter.simulate_benchmark_math(request)
