"""Comprehensive unit and integration test suite for Platform Battery #37: Benchmark Gatekeeper."""

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from src.adapters.eval.benchmark_gatekeeper_adapter import (
    BenchmarkGatekeeperAdapter,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_percentiles,
    calculate_precision_at_k,
    calculate_recall_at_k,
    compute_welch_ttest_from_stats,
    welch_satterthwaite_df,
)
from src.domain.abstractions.benchmark_gatekeeper import (
    BenchmarkItemSample,
    GatePolicy,
    GateVerdict,
)
from src.domain.batteries.battery_service import BatteryService
from src.main import app

client = TestClient(app)


def test_ndcg_and_mrr_mathematical_precision() -> None:
    """Verify NDCG@K and MRR with known ground-truth rankings."""
    ground_truth = ["doc_A", "doc_B"]

    # 1. Perfect ranking: both relevant in first two positions
    perfect_retrieved = ["doc_A", "doc_B", "doc_C", "doc_D"]
    assert calculate_ndcg_at_k(perfect_retrieved, ground_truth, k=10) == 1.0
    assert calculate_mrr(perfect_retrieved, ground_truth) == 1.0

    # 2. Delayed first hit: first relevant doc at rank 2
    delayed_retrieved = ["doc_C", "doc_A", "doc_D", "doc_B"]
    assert calculate_mrr(delayed_retrieved, ground_truth) == 0.5
    ndcg_delayed = calculate_ndcg_at_k(delayed_retrieved, ground_truth, k=10)
    assert 0.0 < ndcg_delayed < 1.0

    # 3. Disjoint / no hits
    disjoint_retrieved = ["doc_X", "doc_Y", "doc_Z"]
    assert calculate_ndcg_at_k(disjoint_retrieved, ground_truth, k=10) == 0.0
    assert calculate_mrr(disjoint_retrieved, ground_truth) == 0.0


def test_precision_and_recall_at_k() -> None:
    """Verify Precision@K and Recall@K formulas."""
    gt = ["doc_1", "doc_2", "doc_3", "doc_4"]
    retrieved = ["doc_1", "doc_99", "doc_2", "doc_100", "doc_3"]

    # At K=5: hits = 3 (doc_1, doc_2, doc_3)
    recall = calculate_recall_at_k(retrieved, gt, k=5)
    precision = calculate_precision_at_k(retrieved, gt, k=5)

    assert recall == 3.0 / 4.0
    assert precision == 3.0 / 5.0


def test_percentiles_calculation() -> None:
    """Verify statistical percentile estimation."""
    values = [float(i) for i in range(1, 101)]
    p50, p95, p99 = calculate_percentiles(values)
    assert abs(p50 - 50.5) < 0.5
    assert abs(p95 - 95.0) < 1.0
    assert abs(p99 - 99.0) < 1.0


def test_welch_ttest_and_degrees_of_freedom() -> None:
    """Verify Welch's t-test statistic and Welch-Satterthwaite df."""
    # Baseline: mean=100, std=15, n=30
    # Candidate: mean=125, std=20, n=30
    df = welch_satterthwaite_df(s1=15.0, n1=30, s2=20.0, n2=30)
    assert abs(df - 53.78) < 0.2

    res = compute_welch_ttest_from_stats(
        m1=100.0, s1=15.0, n1=30,
        m2=125.0, s2=20.0, n2=30,
        metric_name="latency",
        alpha=0.05,
    )
    # t-stat must be negative (mean1 < mean2)
    assert res.t_statistic < -5.0
    assert res.p_value < 0.001
    assert res.is_statistically_significant is True


def test_gatekeeper_evaluation_clean_pass() -> None:
    """Ensure candidate with improved quality and latency passes clean."""
    adapter = BenchmarkGatekeeperAdapter()
    suite = adapter.create_suite(
        tenant_id="tn_test_corp",
        name="Test Suite",
        description="Unit test suite",
        k_cutoff=10,
        gate_policy=GatePolicy(
            max_latency_p95_increase_pct=10.0,
            max_ndcg_drop_abs=0.03,
            auto_rollback_on_regression=True,
        ),
    )

    # Baseline run
    base_samples = [
        BenchmarkItemSample(
            query_id=f"q_{i}",
            query_text="query",
            ground_truth_chunks=["c1"],
            retrieved_chunks=["c1", "c2"],
            latency_ms=25.0 + (i % 3),
            ndcg_at_k=0.85,
            faithfulness=0.90,
        )
        for i in range(15)
    ]
    base_run = adapter.trigger_run(
        tenant_id="tn_test_corp",
        suite_id=suite.suite_id,
        checkpoint_or_commit="v1-baseline",
        is_baseline=True,
        samples=base_samples,
    )

    # Improved candidate run (faster, higher NDCG)
    cand_samples = [
        BenchmarkItemSample(
            query_id=f"q_{i}",
            query_text="query",
            ground_truth_chunks=["c1"],
            retrieved_chunks=["c1", "c2"],
            latency_ms=20.0 + (i % 2),
            ndcg_at_k=0.92,
            faithfulness=0.95,
        )
        for i in range(15)
    ]
    cand_run = adapter.trigger_run(
        tenant_id="tn_test_corp",
        suite_id=suite.suite_id,
        checkpoint_or_commit="v2-candidate",
        is_baseline=False,
        samples=cand_samples,
    )

    eval_res = adapter.evaluate_gate(
        tenant_id="tn_test_corp",
        suite_id=suite.suite_id,
        candidate_run_id=cand_run.run_id,
        baseline_run_id=base_run.run_id,
    )

    assert eval_res.verdict == GateVerdict.PASSED_CLEAN
    assert eval_res.rollback_triggered is False
    assert len(eval_res.rejection_reasons) == 0


def test_gatekeeper_evaluation_regression_rejection_and_rollback() -> None:
    """Verify that severe latency regression triggers REJECTED_REGRESSION and automated rollback."""
    adapter = BenchmarkGatekeeperAdapter()
    suite = adapter.create_suite(
        tenant_id="tn_test_corp",
        name="Strict Latency Suite",
        description="SLA gate suite",
        k_cutoff=10,
        gate_policy=GatePolicy(
            max_latency_p95_increase_pct=15.0,
            significance_alpha=0.05,
            auto_rollback_on_regression=True,
        ),
    )

    base_samples = [
        BenchmarkItemSample(
            query_id=f"q_{i}",
            query_text="query",
            ground_truth_chunks=["c1"],
            retrieved_chunks=["c1"],
            latency_ms=15.0 + (i % 3) * 0.5,
            ndcg_at_k=0.95,
            faithfulness=0.95,
        )
        for i in range(20)
    ]
    base_run = adapter.trigger_run(
        tenant_id="tn_test_corp",
        suite_id=suite.suite_id,
        checkpoint_or_commit="v1-base",
        is_baseline=True,
        samples=base_samples,
    )

    # Regressed candidate (+80% latency surge)
    regressed_samples = [
        BenchmarkItemSample(
            query_id=f"q_{i}",
            query_text="query",
            ground_truth_chunks=["c1"],
            retrieved_chunks=["c1"],
            latency_ms=28.0 + (i % 3) * 0.5,
            ndcg_at_k=0.95,
            faithfulness=0.95,
        )
        for i in range(20)
    ]
    cand_run = adapter.trigger_run(
        tenant_id="tn_test_corp",
        suite_id=suite.suite_id,
        checkpoint_or_commit="v2-regressed",
        is_baseline=False,
        samples=regressed_samples,
    )

    eval_res = adapter.evaluate_gate(
        tenant_id="tn_test_corp",
        suite_id=suite.suite_id,
        candidate_run_id=cand_run.run_id,
        baseline_run_id=base_run.run_id,
    )

    assert eval_res.verdict == GateVerdict.REJECTED_REGRESSION
    assert eval_res.rollback_triggered is True
    assert len(eval_res.rejection_reasons) > 0


def test_fastapi_benchmark_endpoints() -> None:
    """Verify HTTP contract and serialization for all Benchmark endpoints."""
    # 1. Health check
    h_resp = client.get("/v1/benchmarks/health")
    assert h_resp.status_code == 200
    assert h_resp.json()["battery"] == "autonomous_benchmark_gatekeeper"
    assert h_resp.json()["battery_id"] == 37

    # 2. List suites
    suites_resp = client.get("/v1/tenants/tn_enterprise_corp/benchmarks/suites")
    assert suites_resp.status_code == 200
    assert len(suites_resp.json()) >= 1
    suite_id = suites_resp.json()[0]["suite_id"]

    # 3. List runs
    runs_resp = client.get(f"/v1/tenants/tn_enterprise_corp/benchmarks/runs?suite_id={suite_id}")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) >= 2

    # 4. Evaluate Gate
    base_run = next(r for r in runs if r["is_baseline"])
    cand_run = next(r for r in runs if not r["is_baseline"])

    eval_resp = client.post(
        "/v1/tenants/tn_enterprise_corp/benchmarks/evaluate-gate",
        json={
            "suite_id": suite_id,
            "candidate_run_id": cand_run["run_id"],
            "baseline_run_id": base_run["run_id"],
        },
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert "verdict" in eval_data
    assert "metric_diffs" in eval_data

    # 5. Math simulate
    sim_resp = client.post(
        "/v1/benchmarks/math/simulate",
        json={
            "metric_type": "latency_p95",
            "baseline_mean": 20.0,
            "baseline_std": 3.0,
            "baseline_n": 30,
            "candidate_mean": 28.0,
            "candidate_std": 4.0,
            "candidate_n": 30,
            "alpha": 0.05,
            "tolerance_threshold_pct": 10.0,
        },
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["verdict"] == "rejected_regression"
    assert sim_data["is_statistically_significant"] is True


def test_battery_37_registration() -> None:
    """Verify Platform Battery #37 is active in BatteryService."""
    service = BatteryService()
    batteries_resp = service.get_platform_batteries()
    battery_ids = [b.id for b in batteries_resp.batteries]

    assert "autonomous_benchmark_gatekeeper" in battery_ids
    b37 = service.get_battery("autonomous_benchmark_gatekeeper")
    assert b37 is not None
    assert b37.category.value == "ml_intelligence"
    assert b37.status.value == "active"
    assert "Welch" in b37.algorithm_foundation


def test_hexagonal_architecture_conformance() -> None:
    """Verify that domain abstraction contains no forbidden framework imports."""
    domain_file = Path("apps/api/src/domain/abstractions/benchmark_gatekeeper.py")
    assert domain_file.exists()

    tree = ast.parse(domain_file.read_text(encoding="utf-8"))
    forbidden_prefixes = ("fastapi", "sqlalchemy", "torch", "scipy", "src.adapters", "src.routers")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert not name.name.startswith(forbidden_prefixes), (
                    f"Forbidden import '{name.name}' in domain abstraction!"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith(forbidden_prefixes), (
                f"Forbidden from-import '{node.module}' in domain abstraction!"
            )
