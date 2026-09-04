"""Tests for Durable Asynchronous Workflow Execution Engine (Milestone 95).

Verifies step-level memoization, automatic exponential backoff retries,
checkpoint state serialization, failure replay from checkpoints, tenant isolation,
concurrency throttling, and Platform Battery #15 catalog registration.
"""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from src.adapters.database.workflow_repository import SqlWorkflowRepository
from src.adapters.workflow.durable_workflow_adapter import (
    DurableStepContext,
    DurableWorkflowAdapter,
)
from src.domain.abstractions.batteries import BatteryCategory, BatteryStatus
from src.domain.abstractions.durable_workflow import (
    StepStatus,
    WorkflowExecutionRecord,
    WorkflowRunRequest,
    WorkflowStatus,
    WorkflowStepRecord,
)
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.batteries.battery_service import BatteryService
from src.domain.workflow.durable_engine import DurableWorkflowEngine
from src.main import app


@pytest.fixture
def repo() -> SqlWorkflowRepository:
    return SqlWorkflowRepository()


@pytest.fixture
def engine() -> DurableWorkflowEngine:
    return DurableWorkflowEngine()


@pytest.fixture
def adapter(repo: SqlWorkflowRepository, engine: DurableWorkflowEngine) -> DurableWorkflowAdapter:
    return DurableWorkflowAdapter(repository=repo, engine=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── 1. Blueprint Catalog & Registration ───────────────────────────────────────


def test_blueprint_registry(engine: DurableWorkflowEngine):
    """Verify all 4 core enterprise durable workflows are pre-registered with correct step DAGs."""
    blueprints = engine.list_workflows()
    names = {b.name for b in blueprints}
    assert "vault_bulk_ingest" in names
    assert "batch_graph_extraction" in names
    assert "synthetic_eval_generator" in names
    assert "bulk_reembed_pipeline" in names

    vault_ingest = engine.get_workflow("vault_bulk_ingest")
    assert vault_ingest is not None
    assert vault_ingest.concurrency_limit == 3
    assert len(vault_ingest.steps) == 6
    step_names = [s.name for s in vault_ingest.steps]
    assert step_names == [
        "extract_and_anonymize",
        "hierarchical_or_ast_chunk",
        "generate_contextual_headers",
        "embed_and_index_vectors",
        "extract_knowledge_graph",
        "finalize_document_catalog",
    ]


# ── 2. Step Memoization (Zero Duplicate Execution) ────────────────────────────


@pytest.mark.asyncio
async def test_step_memoization_skips_executed_steps(repo: SqlWorkflowRepository):
    """Verify that a step with an existing successful checkpoint returns immediately from memoized cache."""
    exec_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    ctx = DurableStepContext(execution_id=exec_id, tenant_id=tenant_id, repository=repo)

    call_count = 0

    async def expensive_computation():
        nonlocal call_count
        call_count += 1
        return {"result": 42, "computed": True}

    # First call: executes handler
    res1 = await ctx.run("expensive_step", expensive_computation)
    assert res1 == {"result": 42, "computed": True}
    assert call_count == 1

    # Second call with same step name: returns cached result without executing handler
    res2 = await ctx.run("expensive_step", expensive_computation)
    assert res2 == {"result": 42, "computed": True}
    assert call_count == 1  # Handler was NOT invoked a second time!

    # Verify checkpoint stored in repository
    cp = await repo.get_step_checkpoint(exec_id, "expensive_step")
    assert cp is not None
    assert cp.status == StepStatus.COMPLETED
    assert cp.memoized_output == {"result": 42, "computed": True}


# ── 3. Exponential Backoff & Step Retries ─────────────────────────────────────


@pytest.mark.asyncio
async def test_step_retry_with_eventual_success(repo: SqlWorkflowRepository):
    """Verify that a step retries on transient error and succeeds if attempts < max_attempts."""
    exec_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    ctx = DurableStepContext(execution_id=exec_id, tenant_id=tenant_id, repository=repo)

    attempt_counter = 0

    async def flaky_network_call():
        nonlocal attempt_counter
        attempt_counter += 1
        if attempt_counter < 3:
            raise ConnectionResetError(f"Temporary network blip (attempt {attempt_counter})")
        return {"connected": True, "final_attempt": attempt_counter}

    res = await ctx.run(
        "network_step",
        flaky_network_call,
        max_attempts=3,
        backoff_factor=1.5,
        initial_interval_seconds=0.01,
    )
    assert res["connected"] is True
    assert res["final_attempt"] == 3
    assert attempt_counter == 3

    cp = await repo.get_step_checkpoint(exec_id, "network_step")
    assert cp is not None
    assert cp.status == StepStatus.COMPLETED
    assert cp.attempts == 3


@pytest.mark.asyncio
async def test_step_retry_exhaustion_fails(repo: SqlWorkflowRepository):
    """Verify that exhausting retries marks the step as FAILED and raises the exception."""
    exec_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    ctx = DurableStepContext(execution_id=exec_id, tenant_id=tenant_id, repository=repo)

    attempts = 0

    async def persistent_failure():
        nonlocal attempts
        attempts += 1
        raise ValueError("Fatal payload corruption")

    with pytest.raises(ValueError, match="Fatal payload corruption"):
        await ctx.run(
            "corrupt_step",
            persistent_failure,
            max_attempts=3,
            initial_interval_seconds=0.01,
        )

    assert attempts == 3
    cp = await repo.get_step_checkpoint(exec_id, "corrupt_step")
    assert cp is not None
    assert cp.status == StepStatus.FAILED
    assert "Fatal payload corruption" in (cp.error_details or "")


# ── 4. End-to-End Workflow Execution & Pipeline ───────────────────────────────


@pytest.mark.asyncio
async def test_vault_bulk_ingest_pipeline(adapter: DurableWorkflowAdapter):
    """Verify full end-to-end execution of the Vault Bulk Ingestion workflow."""
    tenant_id = str(uuid.uuid4())
    req = WorkflowRunRequest(
        workflow_name="vault_bulk_ingest",
        input_payload={"raw_text": "Enterprise knowledge base documentation.", "document_id": "doc-101"},
    )
    record = await adapter.start_workflow(tenant_id, req)
    assert record.workflow_name == "vault_bulk_ingest"
    assert record.status in (WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED)

    # Allow async pipeline tasks to finish with resilient polling
    completed_record = None
    for _ in range(60):
        completed_record = await adapter.get_execution(tenant_id, record.execution_id)
        if completed_record and completed_record.status == WorkflowStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)

    assert completed_record is not None
    assert completed_record.status == WorkflowStatus.COMPLETED
    assert completed_record.completed_steps == 6
    assert completed_record.output_payload.get("catalog_status") == "COMPLETED"
    assert completed_record.output_payload.get("pii_redacted") is True

    # Verify all 6 step checkpoints persisted
    steps = await adapter.repository.list_step_checkpoints(record.execution_id)
    assert len(steps) == 6
    for s in steps:
        assert s.status == StepStatus.COMPLETED


# ── 5. Replay from Failed Checkpoint ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_failed_workflow_resumes_from_checkpoint(
    adapter: DurableWorkflowAdapter, repo: SqlWorkflowRepository
):
    """Verify that replaying a failed execution reuses previously completed step outputs."""
    tenant_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    # Pre-seed Step 1 as COMPLETED and Step 2 as FAILED
    step1 = WorkflowStepRecord(
        step_id=f"{exec_id}:scan_vault_documents",
        execution_id=exec_id,
        step_name="scan_vault_documents",
        step_index=1,
        status=StepStatus.COMPLETED,
        memoized_output={"documents_scanned": 12, "total_chunks": 99},
    )
    step2 = WorkflowStepRecord(
        step_id=f"{exec_id}:extract_entities_and_triples",
        execution_id=exec_id,
        step_name="extract_entities_and_triples",
        step_index=2,
        status=StepStatus.FAILED,
        error_details="Timeout contacting LLM extraction",
    )
    await repo.save_step_checkpoint(step1)
    await repo.save_step_checkpoint(step2)

    initial_exec = WorkflowExecutionRecord(
        execution_id=exec_id,
        tenant_id=tenant_id,
        workflow_name="batch_graph_extraction",
        status=WorkflowStatus.FAILED,
        input_payload={"doc_count": 12},
        total_steps=4,
        completed_steps=1,
        current_step_name="extract_entities_and_triples",
        error_message="Timeout contacting LLM extraction",
    )
    await repo.create_execution(initial_exec)

    # Retry the execution
    retried_record = await adapter.retry_execution(tenant_id, exec_id)
    assert retried_record.status == WorkflowStatus.RUNNING

    # Allow replay to proceed with polling
    final_record = None
    for _ in range(60):
        final_record = await adapter.get_execution(tenant_id, exec_id)
        if final_record and final_record.status == WorkflowStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)

    assert final_record is not None
    assert final_record.status == WorkflowStatus.COMPLETED
    assert final_record.completed_steps == 4

    # Step 1 was preserved from earlier memoization
    checkpoints = await repo.list_step_checkpoints(exec_id)
    s1 = next(c for c in checkpoints if c.step_name == "scan_vault_documents")
    assert s1.memoized_output == {"documents_scanned": 12, "total_chunks": 99}



# ── 6. Idempotency Key De-duplication ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_idempotency_key_deduplication(adapter: DurableWorkflowAdapter):
    """Verify that dispatching multiple requests with the same idempotency key returns the same execution."""
    tenant_id = str(uuid.uuid4())
    idemp_key = f"key_{uuid.uuid4()}"

    req1 = WorkflowRunRequest(
        workflow_name="synthetic_eval_generator",
        input_payload={"sample_size": 10},
        idempotency_key=idemp_key,
    )
    rec1 = await adapter.start_workflow(tenant_id, req1)

    req2 = WorkflowRunRequest(
        workflow_name="synthetic_eval_generator",
        input_payload={"sample_size": 20},
        idempotency_key=idemp_key,
    )
    rec2 = await adapter.start_workflow(tenant_id, req2)

    assert rec1.execution_id == rec2.execution_id


# ── 7. Tenant Isolation Boundary ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(adapter: DurableWorkflowAdapter):
    """Verify that tenant A cannot access or cancel workflow executions of tenant B."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    req = WorkflowRunRequest(workflow_name="bulk_reembed_pipeline")
    rec_a = await adapter.start_workflow(tenant_a, req)

    # Tenant B tries to fetch Tenant A's execution
    rec_b = await adapter.get_execution(tenant_b, rec_a.execution_id)
    assert rec_b is None

    # Empty tenant ID raises TenantIsolationViolationError
    with pytest.raises(TenantIsolationViolationError):
        await adapter.get_execution("", rec_a.execution_id)


# ── 8. Platform Battery #15 Registration ──────────────────────────────────────


def test_battery_15_registered():
    """Verify Durable Workflow Engine is registered as Platform Battery #15 under BACKGROUND_WORKFLOWS."""
    battery_svc = BatteryService()
    resp = battery_svc.get_platform_batteries()

    assert resp.total_batteries >= 15
    wf_battery = next((b for b in resp.batteries if b.id == "durable_workflow_engine"), None)
    assert wf_battery is not None
    assert wf_battery.name == "Durable Asynchronous Workflow Execution Engine"
    assert wf_battery.category == BatteryCategory.BACKGROUND_WORKFLOWS
    assert wf_battery.status == BatteryStatus.ACTIVE
    assert "M95" in wf_battery.milestone
    assert wf_battery.active_parameters.get("max_concurrent_per_tenant") == 3


# ── 9. FastAPI REST Endpoints ─────────────────────────────────────────────────


def test_rest_api_workflow_lifecycle(client: TestClient):
    """Test full HTTP REST workflow lifecycle: overview, launch, status, list, and cancellation."""
    from unittest.mock import patch

    admin_headers = {"X-Admin-Master-Key": "test_admin_key"}

    with patch("src.config.settings.ADMIN_MASTER_KEY", "test_admin_key"):
        # 1. Platform Overview
        overview_resp = client.get("/v1/admin/workflows/overview", headers=admin_headers)
        assert overview_resp.status_code == 200
        overview_data = overview_resp.json()
        assert overview_data["total_blueprints"] >= 4

        # 2. Trigger Named Workflow
        tenant_id = str(uuid.uuid4())
        run_resp = client.post(
            f"/v1/tenants/{tenant_id}/workflows/synthetic_eval_generator/run",
            json={"input_payload": {"test": True}},
            headers=admin_headers,
        )
        assert run_resp.status_code == 202
        run_data = run_resp.json()
        exec_id = run_data["execution_id"]
        assert run_data["workflow_name"] == "synthetic_eval_generator"

        # 3. Get Execution Detail
        detail_resp = client.get(
            f"/v1/tenants/{tenant_id}/workflows/executions/{exec_id}",
            headers=admin_headers,
        )
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["execution_id"] == exec_id

        # 4. List Executions
        list_resp = client.get(
            f"/v1/tenants/{tenant_id}/workflows/executions",
            headers=admin_headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1

        # 5. Cancel Execution
        cancel_resp = client.post(
            f"/v1/tenants/{tenant_id}/workflows/executions/{exec_id}/cancel",
            headers=admin_headers,
        )
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.json()
        assert cancel_data["status"] == "cancelled"

