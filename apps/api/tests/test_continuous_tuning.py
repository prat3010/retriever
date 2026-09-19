"""Tests for Continuous DPO / ORPO Preference Fine-Tuning Pipeline (M120).

Validates:
- Authentic DPO loss, implicit reward margins, and Bradley-Terry scaling.
- Authentic ORPO odds ratio log-likelihood calculation without reference models.
- Preference sample harvesting, prompt deduplication, and auto-trigger threshold dispatch.
- Training convergence telemetry steps and evaluation gating.
- Hot-swappable LoRA adapter promotion and 1-click atomic rollback.
- Strict multi-tenant isolation across preference samples and jobs.
- FastAPI endpoints and Battery #35 catalog registration.
- Hexagonal architecture boundary compliance.
"""

import ast
import math
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.tuning.continuous_tuning_adapter import (
    ContinuousTuningAdapter,
    calculate_dpo_loss,
    calculate_orpo_loss,
)
from src.domain.abstractions.dpo_orpo_tuning import (
    PreferencePair,
    TuningHyperparameters,
    TuningJobStatus,
    TuningObjective,
)
from src.domain.batteries.battery_service import BatteryCategory, BatteryService
from src.main import app


@pytest.fixture
def tuning_adapter() -> ContinuousTuningAdapter:
    return ContinuousTuningAdapter()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_dpo_mathematical_loss_calculation() -> None:
    """Verify authentic DPO loss and implicit reward calculation."""
    # When winning probability is much higher than reference and losing is lower:
    loss, rew_w, rew_l, margin = calculate_dpo_loss(
        beta=0.1,
        pi_theta_w=0.85,
        pi_ref_w=0.50,
        pi_theta_l=0.15,
        pi_ref_l=0.50,
    )

    # rew_w = 0.1 * ln(0.85 / 0.50) = 0.1 * 0.5306 = ~0.0531
    # rew_l = 0.1 * ln(0.15 / 0.50) = 0.1 * -1.204 = ~-0.1204
    # margin = rew_w - rew_l = 0.0531 - (-0.1204) = ~0.1735
    assert margin > 0.15
    assert rew_w > 0.0
    assert rew_l < 0.0
    assert loss > 0.0

    # Under symmetric policy (theta == ref), margin should be 0.0 and loss = -ln(0.5) = ln(2) = ~0.693
    sym_loss, _, _, sym_margin = calculate_dpo_loss(
        beta=0.1,
        pi_theta_w=0.50,
        pi_ref_w=0.50,
        pi_theta_l=0.50,
        pi_ref_l=0.50,
    )
    assert abs(sym_margin) < 1e-6
    assert abs(sym_loss - math.log(2.0)) < 1e-4


def test_orpo_mathematical_loss_calculation() -> None:
    """Verify authentic ORPO odds ratio log-likelihood and composite loss."""
    loss, odds_w, odds_l, odds_ratio = calculate_orpo_loss(
        lambda_val=0.1,
        p_w=0.80,
        p_l=0.20,
    )

    # odds_w = 0.80 / 0.20 = 4.0
    # odds_l = 0.20 / 0.80 = 0.25
    # odds_ratio = 4.0 / 0.25 = 16.0
    assert abs(odds_w - 4.0) < 1e-4
    assert abs(odds_l - 0.25) < 1e-4
    assert abs(odds_ratio - 16.0) < 1e-3
    assert loss > 0.0


def test_preference_harvest_and_deduplication(tuning_adapter: ContinuousTuningAdapter) -> None:
    """Ensure preference pairs are ingested and deduplicated by prompt."""
    tenant_id = "tn_dpo_test_1"
    pair1 = PreferencePair(
        pair_id="pair_001",
        tenant_id=tenant_id,
        prompt="Explain vector search",
        winning_response="Vector search matches semantic embeddings.",
        losing_response="Vector search does string matching.",
        feedback_rating=1,
        tags=["semantic"],
        is_verified=True,
        created_at=datetime.now(UTC).isoformat(),
    )

    stored1 = tuning_adapter.harvest_preference_pair(tenant_id, pair1)
    assert stored1.pair_id == "pair_001"

    pairs, total = tuning_adapter.list_preference_pairs(tenant_id)
    assert total == 1
    assert len(pairs) == 1

    # Ingest duplicate prompt with updated winning response
    pair2 = PreferencePair(
        pair_id="pair_002",
        tenant_id=tenant_id,
        prompt="Explain vector search",  # Same prompt
        winning_response="Vector search uses approximate nearest neighbors.",
        losing_response="Vector search is just SQL LIKE queries.",
        feedback_rating=1,
        tags=["semantic", "updated"],
        is_verified=True,
        created_at=datetime.now(UTC).isoformat(),
    )

    stored2 = tuning_adapter.harvest_preference_pair(tenant_id, pair2)
    assert stored2.winning_response == "Vector search uses approximate nearest neighbors."

    # Total buffer should remain 1 due to prompt deduplication
    _, total_after = tuning_adapter.list_preference_pairs(tenant_id)
    assert total_after == 1


def test_preference_auto_trigger_threshold(tuning_adapter: ContinuousTuningAdapter) -> None:
    """Verify automated fine-tuning trigger when harvest buffer reaches threshold."""
    tenant_id = "tn_auto_trigger"
    config = tuning_adapter.get_tuning_config(tenant_id)
    config.hyperparameters.auto_trigger_threshold = 3
    config.auto_train_enabled = True
    tuning_adapter.update_tuning_config(tenant_id, config)

    # Ingest 3 distinct pairs
    for i in range(3):
        pair = PreferencePair(
            pair_id=f"pair_auto_{i}",
            tenant_id=tenant_id,
            prompt=f"Prompt {i}",
            winning_response=f"Winning answer {i}",
            losing_response=f"Losing answer {i}",
            feedback_rating=1,
            is_verified=True,
            created_at=datetime.now(UTC).isoformat(),
        )
        tuning_adapter.harvest_preference_pair(tenant_id, pair)

    # A job should have automatically been dispatched
    jobs = tuning_adapter.list_tuning_jobs(tenant_id)
    assert len(jobs) >= 1
    assert jobs[0].status == TuningJobStatus.COMPLETED


def test_tuning_job_convergence_and_loss_history(tuning_adapter: ContinuousTuningAdapter) -> None:
    """Verify step loss convergence history and evaluation gate."""
    tenant_id = "tn_convergence"
    job = tuning_adapter.trigger_tuning_job(
        tenant_id,
        objective=TuningObjective.DPO,
        hyperparams=TuningHyperparameters(epochs=2, beta=0.1),
    )

    assert job.status == TuningJobStatus.COMPLETED
    assert len(job.loss_history) == 10  # 2 epochs * 5 steps

    # Loss should trend downwards and accuracy should trend upwards
    first_step = job.loss_history[0]
    last_step = job.loss_history[-1]
    assert last_step.accuracy > first_step.accuracy
    assert last_step.reward_margin > first_step.reward_margin
    assert job.evaluation is not None
    assert job.evaluation.passed is True
    assert job.evaluation.validation_accuracy >= 0.75


def test_adapter_promotion_and_atomic_rollback(tuning_adapter: ContinuousTuningAdapter) -> None:
    """Verify hot-swapping LoRA adapter into active serving and 1-click rollback."""
    tenant_id = "tn_governance"
    config = tuning_adapter.get_tuning_config(tenant_id)
    baseline_adapter = config.active_adapter_id

    # Trigger job
    job = tuning_adapter.trigger_tuning_job(tenant_id, objective=TuningObjective.ORPO)
    assert job.output_adapter_id != baseline_adapter

    # Promote
    promoted_config = tuning_adapter.promote_adapter(tenant_id, job.job_id)
    assert promoted_config.active_adapter_id == job.output_adapter_id

    # Roll back
    rolled_back_config = tuning_adapter.rollback_adapter(tenant_id)
    assert rolled_back_config.active_adapter_id == baseline_adapter


def test_multi_tenant_isolation(tuning_adapter: ContinuousTuningAdapter) -> None:
    """Ensure preference datasets and tuning jobs are strictly isolated by tenant."""
    tenant_a = "tn_corp_alpha"
    tenant_b = "tn_corp_beta"

    pair_a = PreferencePair(
        pair_id="pair_a_1",
        tenant_id=tenant_a,
        prompt="Alpha secret policy",
        winning_response="Alpha answer",
        losing_response="Generic answer",
        created_at=datetime.now(UTC).isoformat(),
    )
    tuning_adapter.harvest_preference_pair(tenant_a, pair_a)

    _pairs_a, total_a = tuning_adapter.list_preference_pairs(tenant_a)
    pairs_b, total_b = tuning_adapter.list_preference_pairs(tenant_b)

    assert total_a == 1
    assert total_b == 0
    assert len(pairs_b) == 0


def test_fastapi_tuning_endpoints(client: TestClient) -> None:
    """Verify REST API routes for continuous tuning."""
    tenant_id = "tn_rest_test"

    # 1. Health Probe
    res = client.get("/v1/tuning/health")
    assert res.status_code == 200
    data = res.json()
    assert data["battery_id"] == "continuous_preference_tuning"
    assert data["status"] == "healthy"
    assert "dpo" in data["supported_objectives"]

    # 2. Config GET & PUT
    res_cfg = client.get(f"/v1/tenants/{tenant_id}/tuning/config")
    assert res_cfg.status_code == 200
    cfg = res_cfg.json()
    assert cfg["tenant_id"] == tenant_id

    cfg["hyperparameters"]["auto_trigger_threshold"] = 25
    res_put = client.put(f"/v1/tenants/{tenant_id}/tuning/config", json=cfg)
    assert res_put.status_code == 200
    assert res_put.json()["hyperparameters"]["auto_trigger_threshold"] == 25

    # 3. Ingest Preference Pair
    pair_payload = {
        "prompt": "How do we handle SLA breaches?",
        "winning_response": "We credit 10% on monthly invoice.",
        "losing_response": "We don't do anything.",
        "feedback_rating": 1,
        "tags": ["sla", "commercial"],
    }
    res_pair = client.post(f"/v1/tenants/{tenant_id}/tuning/pairs", json=pair_payload)
    assert res_pair.status_code == 201
    created_pair = res_pair.json()
    assert created_pair["prompt"] == pair_payload["prompt"]

    # 4. List Pairs
    res_list = client.get(f"/v1/tenants/{tenant_id}/tuning/pairs")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 5. Trigger Job
    job_payload = {"objective": "dpo"}
    res_job = client.post(f"/v1/tenants/{tenant_id}/tuning/jobs", json=job_payload)
    assert res_job.status_code == 201
    job_data = res_job.json()
    assert job_data["status"] == "completed"
    job_id = job_data["job_id"]

    # 6. Get Job Details
    res_job_get = client.get(f"/v1/tenants/{tenant_id}/tuning/jobs/{job_id}")
    assert res_job_get.status_code == 200
    assert len(res_job_get.json()["loss_history"]) > 0

    # 7. Promote Adapter
    res_prom = client.post(f"/v1/tenants/{tenant_id}/tuning/jobs/{job_id}/promote")
    assert res_prom.status_code == 200
    assert res_prom.json()["active_adapter_id"] == job_data["output_adapter_id"]

    # 8. Rollback
    res_roll = client.post(f"/v1/tenants/{tenant_id}/tuning/rollback")
    assert res_roll.status_code == 200

    # 9. Math Simulation Endpoint
    math_req = {
        "prompt": "Simulated query",
        "beta": 0.1,
        "lambda_orpo": 0.1,
        "pi_theta_win_prob": 0.85,
        "pi_ref_win_prob": 0.50,
        "pi_theta_lose_prob": 0.15,
        "pi_ref_lose_prob": 0.50,
    }
    res_math = client.post("/v1/tuning/math/simulate", json=math_req)
    assert res_math.status_code == 200
    math_data = res_math.json()
    assert math_data["dpo_reward_margin"] > 0
    assert math_data["orpo_odds_ratio"] > 1.0


def test_battery_35_registration() -> None:
    """Verify Battery #35 continuous_preference_tuning is cataloged."""
    battery_svc = BatteryService()
    resp = battery_svc.get_platform_batteries()

    assert resp.total_batteries >= 35
    battery = battery_svc.get_battery("continuous_preference_tuning")
    assert battery is not None
    assert battery.name == "Continuous DPO / ORPO Preference Tuning Pipeline"
    assert battery.category == BatteryCategory.ML_INTELLIGENCE
    assert battery.milestone == "M120 (v2.0.0-alpha1)"
    assert battery.health_check_endpoint == "/v1/tuning/health"


def test_continuous_tuning_architecture_boundaries() -> None:
    """Hexagonal boundary gate ensuring 0 framework imports in dpo_orpo_tuning.py."""
    source_path = Path(__file__).resolve().parent.parent / "src/domain/abstractions/dpo_orpo_tuning.py"
    assert source_path.exists(), "Domain file must exist"

    tree = ast.parse(source_path.read_text())
    prohibited = {"fastapi", "sqlalchemy", "redis", "celery", "httpx", "requests", "modal"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                root = name.name.split(".")[0]
                assert root not in prohibited, f"Prohibited import in domain: {root}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                assert root not in prohibited, f"Prohibited import in domain: {root}"
