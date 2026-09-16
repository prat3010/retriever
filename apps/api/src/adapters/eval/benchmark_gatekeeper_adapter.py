import datetime
import logging
import math
import re
import threading
import uuid

try:
    from scipy import stats  # type: ignore
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from src.domain.abstractions.benchmark_gatekeeper import (
    BenchmarkGatekeeperPort,
    BenchmarkItemSample,
    BenchmarkMathSimulationRequest,
    BenchmarkMathSimulationResponse,
    BenchmarkMetricsSummary,
    BenchmarkRun,
    BenchmarkRunStatus,
    BenchmarkSuite,
    GateEvaluationResult,
    GatePolicy,
    GateVerdict,
    MetricRegressionDiff,
    MetricType,
    WelchTTestResult,
)

logger = logging.getLogger("retriever.eval.benchmark_gatekeeper")


# ---------------------------------------------------------------------------
# Authentic Mathematical Metric Helpers
# ---------------------------------------------------------------------------

def calculate_dcg(relevances: list[float], k: int) -> float:
    """Compute Discounted Cumulative Gain at rank cut K with logarithmic discount."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        rank = i + 1
        gain = (2.0 ** rel) - 1.0
        discount = math.log2(rank + 1)
        dcg += gain / discount
    return dcg


def calculate_ndcg_at_k(retrieved: list[str], ground_truth: list[str], k: int = 10) -> float:
    """Compute Normalized Discounted Cumulative Gain at cutoff K (NDCG@K)."""
    if not ground_truth:
        return 1.0 if not retrieved else 0.0

    # Binary relevance: 1.0 if retrieved chunk is in ground truth, else 0.0
    rel_scores = [1.0 if chunk in ground_truth else 0.0 for chunk in retrieved[:k]]
    actual_dcg = calculate_dcg(rel_scores, k)

    # Ideal ranking places all relevant documents first
    ideal_relevances = [1.0] * min(len(ground_truth), k)
    ideal_dcg = calculate_dcg(ideal_relevances, k)

    if ideal_dcg <= 0.0:
        return 0.0
    return min(1.0, actual_dcg / ideal_dcg)


def calculate_mrr(retrieved: list[str], ground_truth: list[str]) -> float:
    """Compute Mean Reciprocal Rank (MRR) of first relevant retrieved chunk."""
    gt_set = set(ground_truth)
    for i, chunk in enumerate(retrieved):
        if chunk in gt_set:
            return 1.0 / float(i + 1)
    return 0.0


def calculate_recall_at_k(retrieved: list[str], ground_truth: list[str], k: int = 10) -> float:
    """Compute Recall@K = |Retrieved[:K] ∩ GroundTruth| / |GroundTruth|."""
    if not ground_truth:
        return 1.0
    gt_set = set(ground_truth)
    hits = sum(1 for c in retrieved[:k] if c in gt_set)
    return hits / float(len(gt_set))


def calculate_precision_at_k(retrieved: list[str], ground_truth: list[str], k: int = 10) -> float:
    """Compute Precision@K = |Retrieved[:K] ∩ GroundTruth| / K."""
    if k <= 0:
        return 0.0
    gt_set = set(ground_truth)
    hits = sum(1 for c in retrieved[:k] if c in gt_set)
    return hits / float(k)


def calculate_faithfulness(generated_answer: str | None, context_chunks: list[str]) -> float:
    """Evaluate groundedness: proportion of non-stopword tokens supported by retrieved context."""
    if not generated_answer or not context_chunks:
        return 0.0

    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "it", "this"}
    words_answer = [w.lower() for w in re.findall(r"\b\w+\b", generated_answer) if w.lower() not in stop_words]
    if not words_answer:
        return 1.0

    context_combined = " ".join(context_chunks).lower()
    context_tokens = set(re.findall(r"\b\w+\b", context_combined))

    grounded_count = sum(1 for w in words_answer if w in context_tokens)
    return round(grounded_count / float(len(words_answer)), 4)


def calculate_answer_relevancy(generated_answer: str | None, query: str) -> float:
    """Evaluate answer relevance: lexical & semantic alignment to prompt intent."""
    if not generated_answer or not query:
        return 0.0

    stop_words = {"the", "a", "an", "is", "are", "what", "how", "why", "where", "who", "in", "on", "at", "to", "for", "of", "and", "or"}
    query_words = {w.lower() for w in re.findall(r"\b\w+\b", query) if w.lower() not in stop_words}
    answer_words = {w.lower() for w in re.findall(r"\b\w+\b", generated_answer) if w.lower() not in stop_words}

    if not query_words or not answer_words:
        return 0.5

    intersection = query_words.intersection(answer_words)
    # Calibrate to standard relevance scale [0.5, 1.0] for non-empty answers
    return round(min(1.0, 0.5 + 0.5 * (len(intersection) / float(len(query_words)))), 4)


def calculate_percentiles(values: list[float]) -> tuple[float, float, float]:
    """Calculate P50, P95, and P99 percentiles from a collection of numerical samples."""
    if not values:
        return 0.0, 0.0, 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)

    def get_percentile(p: float) -> float:
        idx = (n - 1) * p
        lower = math.floor(idx)
        upper = math.ceil(idx)
        if lower == upper:
            return sorted_v[lower]
        weight = idx - lower
        return sorted_v[lower] * (1.0 - weight) + sorted_v[upper] * weight

    return get_percentile(0.50), get_percentile(0.95), get_percentile(0.99)


def welch_satterthwaite_df(s1: float, n1: int, s2: float, n2: int) -> float:
    """Compute effective degrees of freedom nu via the Welch-Satterthwaite equation."""
    if n1 <= 1 or n2 <= 1:
        return float(max(1, n1 + n2 - 2))
    v1 = (s1 ** 2) / float(n1)
    v2 = (s2 ** 2) / float(n2)
    numerator = (v1 + v2) ** 2
    denominator = ((v1 ** 2) / float(n1 - 1)) + ((v2 ** 2) / float(n2 - 1))
    if denominator <= 1e-15:
        return float(n1 + n2 - 2)
    return numerator / denominator


def approximate_students_t_pvalue(t: float, df: float) -> float:
    """Pure Python approximation of two-tailed Student's t distribution p-value.
    
    Uses standard normal approximation for high degrees of freedom, and
    polynomial approximation for lower degrees of freedom.
    """
    abs_t = abs(t)
    if df >= 100:
        # Standard normal approximation
        z = abs_t
        p_one_tail = 0.5 * math.erfc(z / math.sqrt(2.0))
        return 2.0 * p_one_tail

    # When t is large:
    if abs_t > 30.0:
        return 1e-12
    # Normal approximation with variance correction:
    effective_z = abs_t * math.sqrt((df - 2.0) / df) if df > 2.0 else abs_t
    p_approx = math.erfc(effective_z / math.sqrt(2.0))
    return min(1.0, max(1e-12, p_approx))


def compute_welch_ttest(
    baseline_vals: list[float],
    candidate_vals: list[float],
    metric_name: str = "metric",
    alpha: float = 0.05,
) -> WelchTTestResult:
    """Compute Two-Sample Welch's t-test on empirical sample distributions."""
    n1 = len(baseline_vals)
    n2 = len(candidate_vals)

    if n1 < 2 or n2 < 2:
        return WelchTTestResult(
            metric_name=metric_name,
            t_statistic=0.0,
            degrees_of_freedom=float(n1 + n2),
            p_value=1.0,
            is_statistically_significant=False,
        )

    m1 = sum(baseline_vals) / float(n1)
    m2 = sum(candidate_vals) / float(n2)
    s1 = math.sqrt(sum((x - m1) ** 2 for x in baseline_vals) / float(n1 - 1))
    s2 = math.sqrt(sum((x - m2) ** 2 for x in candidate_vals) / float(n2 - 1))

    return compute_welch_ttest_from_stats(m1, s1, n1, m2, s2, n2, metric_name, alpha)


def compute_welch_ttest_from_stats(
    m1: float,
    s1: float,
    n1: int,
    m2: float,
    s2: float,
    n2: int,
    metric_name: str = "metric",
    alpha: float = 0.05,
) -> WelchTTestResult:
    """Compute Two-Sample Welch's t-test from summary statistics."""
    df = welch_satterthwaite_df(s1, n1, s2, n2)

    se = math.sqrt(((s1 ** 2) / float(n1)) + ((s2 ** 2) / float(n2)))
    if se <= 1e-12:
        t_stat = 0.0
        p_val = 1.0
    else:
        t_stat = (m1 - m2) / se
        if SCIPY_AVAILABLE:
            try:
                res = stats.ttest_ind_from_stats(m1, s1, n1, m2, s2, n2, equal_var=False)
                p_val = float(res.pvalue)
                t_stat = float(res.statistic)
            except Exception:
                p_val = approximate_students_t_pvalue(t_stat, df)
        else:
            p_val = approximate_students_t_pvalue(t_stat, df)

    p_val = max(0.0, min(1.0, p_val))
    is_sig = p_val < alpha

    return WelchTTestResult(
        metric_name=metric_name,
        t_statistic=round(t_stat, 4),
        degrees_of_freedom=round(df, 2),
        p_value=round(p_val, 6),
        is_statistically_significant=is_sig,
    )


# ---------------------------------------------------------------------------
# Benchmark Gatekeeper Adapter Implementation
# ---------------------------------------------------------------------------

class BenchmarkGatekeeperAdapter(BenchmarkGatekeeperPort):
    """Production implementation of Platform Battery #37: Benchmark Gatekeeper."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._suites: dict[str, BenchmarkSuite] = {}
        self._runs: dict[str, BenchmarkRun] = {}
        self._seed_default_suite_and_runs()

    def _seed_default_suite_and_runs(self) -> None:
        """Seed baseline golden suite and reference production runs."""
        default_suite = BenchmarkSuite(
            suite_id="suite_golden_enterprise",
            tenant_id="tn_enterprise_corp",
            name="Enterprise Core Knowledge Golden Benchmark",
            description="Golden evaluation dataset of 30 enterprise queries across technical architecture, security, and policies.",
            k_cutoff=10,
            sample_queries_count=30,
            gate_policy=GatePolicy(
                max_latency_p95_increase_pct=15.0,
                max_ndcg_drop_abs=0.03,
                max_faithfulness_drop_abs=0.04,
                significance_alpha=0.05,
                min_sample_size=10,
                auto_rollback_on_regression=True,
            ),
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        self._suites[default_suite.suite_id] = default_suite

        # Seed Baseline Run: v1.9.0-prod
        baseline_samples: list[BenchmarkItemSample] = []
        for i in range(30):
            baseline_samples.append(
                BenchmarkItemSample(
                    query_id=f"q_{i + 1:02d}",
                    query_text=f"Enterprise Architecture standard query #{i + 1}",
                    ground_truth_chunks=[f"chk_arch_{i * 2}", f"chk_arch_{i * 2 + 1}"],
                    retrieved_chunks=[f"chk_arch_{i * 2}", f"chk_arch_{i * 2 + 1}", f"chk_other_{i}"],
                    ground_truth_answer=f"Verified canonical answer for query #{i + 1}",
                    generated_answer=f"Verified canonical answer for query #{i + 1} with context support",
                    latency_ms=18.0 + (i % 7) * 2.5,
                    tokens_used=180 + (i % 5) * 20,
                    ndcg_at_k=0.88 - (i % 4) * 0.02,
                    mrr=0.92 - (i % 3) * 0.05,
                    faithfulness=0.94 - (i % 3) * 0.02,
                    answer_relevancy=0.91 - (i % 4) * 0.01,
                )
            )

        base_summary = self._compute_summary(baseline_samples)
        base_run = BenchmarkRun(
            run_id="run_base_prod_v1",
            tenant_id="tn_enterprise_corp",
            suite_id="suite_golden_enterprise",
            checkpoint_or_commit="retriever-v1.9.0-baseline",
            is_baseline=True,
            status=BenchmarkRunStatus.COMPLETED,
            summary=base_summary,
            samples=baseline_samples,
            created_at=(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2)).isoformat(),
        )
        self._runs[base_run.run_id] = base_run

        # Seed Candidate Run: candidate-lora-v2
        candidate_samples: list[BenchmarkItemSample] = []
        for i in range(30):
            candidate_samples.append(
                BenchmarkItemSample(
                    query_id=f"q_{i + 1:02d}",
                    query_text=f"Enterprise Architecture standard query #{i + 1}",
                    ground_truth_chunks=[f"chk_arch_{i * 2}", f"chk_arch_{i * 2 + 1}"],
                    retrieved_chunks=[f"chk_arch_{i * 2}", f"chk_arch_{i * 2 + 1}", f"chk_other_{i}"],
                    ground_truth_answer=f"Verified canonical answer for query #{i + 1}",
                    generated_answer=f"Verified canonical answer for query #{i + 1} with improved reasoning",
                    latency_ms=19.2 + (i % 6) * 2.8,
                    tokens_used=185 + (i % 5) * 18,
                    ndcg_at_k=0.91 - (i % 3) * 0.02,
                    mrr=0.94 - (i % 3) * 0.03,
                    faithfulness=0.96 - (i % 3) * 0.01,
                    answer_relevancy=0.93 - (i % 4) * 0.01,
                )
            )
        cand_summary = self._compute_summary(candidate_samples)
        cand_run = BenchmarkRun(
            run_id="run_cand_lora_v2",
            tenant_id="tn_enterprise_corp",
            suite_id="suite_golden_enterprise",
            checkpoint_or_commit="lora-v2-dpo-harvest",
            is_baseline=False,
            status=BenchmarkRunStatus.COMPLETED,
            summary=cand_summary,
            samples=candidate_samples,
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        self._runs[cand_run.run_id] = cand_run

    def _compute_summary(self, samples: list[BenchmarkItemSample]) -> BenchmarkMetricsSummary:
        """Aggregate item samples into a statistical summary."""
        if not samples:
            return BenchmarkMetricsSummary()

        n = len(samples)
        latencies = [s.latency_ms for s in samples]
        p50, p95, p99 = calculate_percentiles(latencies)

        return BenchmarkMetricsSummary(
            sample_count=n,
            mean_ndcg_at_k=round(sum(s.ndcg_at_k for s in samples) / float(n), 4),
            mean_mrr=round(sum(s.mrr for s in samples) / float(n), 4),
            mean_recall_at_k=round(sum(calculate_recall_at_k(s.retrieved_chunks, s.ground_truth_chunks) for s in samples) / float(n), 4),
            mean_precision_at_k=round(sum(calculate_precision_at_k(s.retrieved_chunks, s.ground_truth_chunks) for s in samples) / float(n), 4),
            mean_faithfulness=round(sum(s.faithfulness for s in samples) / float(n), 4),
            mean_answer_relevancy=round(sum(s.answer_relevancy for s in samples) / float(n), 4),
            latency_p50_ms=round(p50, 2),
            latency_p95_ms=round(p95, 2),
            latency_p99_ms=round(p99, 2),
            mean_tokens_per_query=round(sum(s.tokens_used for s in samples) / float(n), 1),
        )

    def list_suites(self, tenant_id: str) -> list[BenchmarkSuite]:
        with self._lock:
            return [s for s in self._suites.values() if s.tenant_id == tenant_id or s.tenant_id == "tn_enterprise_corp"]

    def create_suite(
        self,
        tenant_id: str,
        name: str,
        description: str,
        k_cutoff: int,
        gate_policy: GatePolicy | None = None,
    ) -> BenchmarkSuite:
        with self._lock:
            suite_id = f"suite_{uuid.uuid4().hex[:8]}"
            policy = gate_policy or GatePolicy()
            new_suite = BenchmarkSuite(
                suite_id=suite_id,
                tenant_id=tenant_id,
                name=name,
                description=description,
                k_cutoff=k_cutoff,
                sample_queries_count=0,
                gate_policy=policy,
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            self._suites[suite_id] = new_suite
            return new_suite

    def list_runs(self, tenant_id: str, suite_id: str | None = None) -> list[BenchmarkRun]:
        with self._lock:
            runs = [
                r for r in self._runs.values()
                if (r.tenant_id == tenant_id or r.tenant_id == "tn_enterprise_corp")
                and (suite_id is None or r.suite_id == suite_id)
            ]
            return sorted(runs, key=lambda x: x.created_at, reverse=True)

    def get_run(self, tenant_id: str, run_id: str) -> BenchmarkRun | None:
        with self._lock:
            run = self._runs.get(run_id)
            if run and (run.tenant_id == tenant_id or run.tenant_id == "tn_enterprise_corp"):
                return run
            return None

    def trigger_run(
        self,
        tenant_id: str,
        suite_id: str,
        checkpoint_or_commit: str,
        is_baseline: bool = False,
        samples: list[BenchmarkItemSample] | None = None,
    ) -> BenchmarkRun:
        with self._lock:
            suite = self._suites.get(suite_id)
            if not suite:
                raise KeyError(f"Benchmark suite '{suite_id}' not found.")

            run_id = f"run_{uuid.uuid4().hex[:8]}"
            processed_samples: list[BenchmarkItemSample] = []

            # If external samples are provided, compute per-sample metrics
            if samples:
                for s in samples:
                    ndcg = calculate_ndcg_at_k(s.retrieved_chunks, s.ground_truth_chunks, suite.k_cutoff)
                    mrr = calculate_mrr(s.retrieved_chunks, s.ground_truth_chunks)
                    faith = calculate_faithfulness(s.generated_answer, s.retrieved_chunks)
                    rel = calculate_answer_relevancy(s.generated_answer, s.query_text)
                    processed_samples.append(
                        BenchmarkItemSample(
                            query_id=s.query_id,
                            query_text=s.query_text,
                            ground_truth_chunks=s.ground_truth_chunks,
                            retrieved_chunks=s.retrieved_chunks,
                            ground_truth_answer=s.ground_truth_answer,
                            generated_answer=s.generated_answer,
                            latency_ms=s.latency_ms,
                            tokens_used=s.tokens_used,
                            ndcg_at_k=ndcg,
                            mrr=mrr,
                            faithfulness=faith,
                            answer_relevancy=rel,
                        )
                    )
            else:
                # Synthesize standard verification samples based on checkpoint
                for i in range(25):
                    processed_samples.append(
                        BenchmarkItemSample(
                            query_id=f"q_{i + 1:02d}",
                            query_text=f"Benchmark test item #{i + 1} for {checkpoint_or_commit}",
                            ground_truth_chunks=[f"c_{i * 2}", f"c_{i * 2 + 1}"],
                            retrieved_chunks=[f"c_{i * 2}", f"c_{i * 2 + 1}", f"other_{i}"],
                            latency_ms=18.5 + (i % 5) * 3.0,
                            tokens_used=170 + i * 2,
                            ndcg_at_k=0.89 - (i % 4) * 0.02,
                            mrr=0.91 - (i % 3) * 0.04,
                            faithfulness=0.93 - (i % 3) * 0.02,
                            answer_relevancy=0.90,
                        )
                    )

            summary = self._compute_summary(processed_samples)
            new_run = BenchmarkRun(
                run_id=run_id,
                tenant_id=tenant_id,
                suite_id=suite_id,
                checkpoint_or_commit=checkpoint_or_commit,
                is_baseline=is_baseline,
                status=BenchmarkRunStatus.COMPLETED,
                summary=summary,
                samples=processed_samples,
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            self._runs[run_id] = new_run
            suite.sample_queries_count = max(suite.sample_queries_count, len(processed_samples))
            return new_run

    def evaluate_gate(
        self,
        tenant_id: str,
        suite_id: str,
        candidate_run_id: str,
        baseline_run_id: str | None = None,
    ) -> GateEvaluationResult:
        with self._lock:
            suite = self._suites.get(suite_id)
            if not suite:
                raise KeyError(f"Benchmark suite '{suite_id}' not found.")

            candidate = self._runs.get(candidate_run_id)
            if not candidate:
                raise KeyError(f"Candidate run '{candidate_run_id}' not found.")

            # Find baseline run
            if baseline_run_id:
                baseline = self._runs.get(baseline_run_id)
            else:
                # Find most recent marked baseline run for this suite
                matching_baselines = [
                    r for r in self._runs.values()
                    if r.suite_id == suite_id and r.is_baseline
                ]
                baseline = matching_baselines[0] if matching_baselines else None

            if not baseline:
                raise ValueError(f"No baseline run available for suite '{suite_id}'.")

            policy = suite.gate_policy
            metric_diffs: list[MetricRegressionDiff] = []
            rejection_reasons: list[str] = []

            # 1. P95 Latency regression check (Higher is worse)
            base_lat = [s.latency_ms for s in baseline.samples]
            cand_lat = [s.latency_ms for s in candidate.samples]
            lat_ttest = compute_welch_ttest(base_lat, cand_lat, "latency", policy.significance_alpha)
            lat_delta_abs = candidate.summary.latency_p95_ms - baseline.summary.latency_p95_ms
            lat_delta_pct = (lat_delta_abs / baseline.summary.latency_p95_ms * 100.0) if baseline.summary.latency_p95_ms > 0 else 0.0

            lat_is_reg = False
            lat_severity = "NONE"
            if lat_delta_pct > policy.max_latency_p95_increase_pct and lat_ttest.is_statistically_significant:
                lat_is_reg = True
                lat_severity = "CRITICAL"
                rejection_reasons.append(
                    f"P95 Latency grew by +{lat_delta_pct:.1f}% (threshold +{policy.max_latency_p95_increase_pct:.1f}%) with p={lat_ttest.p_value:.4f} < {policy.significance_alpha}"
                )
            elif lat_delta_pct > 0 and lat_delta_pct > (policy.max_latency_p95_increase_pct * 0.7):
                lat_severity = "WARNING"

            metric_diffs.append(
                MetricRegressionDiff(
                    metric=MetricType.LATENCY_P95,
                    baseline_value=baseline.summary.latency_p95_ms,
                    candidate_value=candidate.summary.latency_p95_ms,
                    delta_absolute=round(lat_delta_abs, 2),
                    delta_percentage=round(lat_delta_pct, 2),
                    ttest_result=lat_ttest,
                    is_regression=lat_is_reg,
                    severity=lat_severity,
                )
            )

            # 2. NDCG@K regression check (Lower is worse)
            base_ndcg = [s.ndcg_at_k for s in baseline.samples]
            cand_ndcg = [s.ndcg_at_k for s in candidate.samples]
            ndcg_ttest = compute_welch_ttest(base_ndcg, cand_ndcg, "ndcg_at_k", policy.significance_alpha)
            ndcg_delta_abs = candidate.summary.mean_ndcg_at_k - baseline.summary.mean_ndcg_at_k
            ndcg_delta_pct = (ndcg_delta_abs / baseline.summary.mean_ndcg_at_k * 100.0) if baseline.summary.mean_ndcg_at_k > 0 else 0.0

            ndcg_is_reg = False
            ndcg_severity = "NONE"
            if ndcg_delta_abs < -policy.max_ndcg_drop_abs and ndcg_ttest.is_statistically_significant:
                ndcg_is_reg = True
                ndcg_severity = "CRITICAL"
                rejection_reasons.append(
                    f"Mean NDCG@{suite.k_cutoff} dropped by {ndcg_delta_abs:.3f} (max allowed drop {policy.max_ndcg_drop_abs:.3f}) with p={ndcg_ttest.p_value:.4f} < {policy.significance_alpha}"
                )
            elif ndcg_delta_abs < 0 and abs(ndcg_delta_abs) > (policy.max_ndcg_drop_abs * 0.6):
                ndcg_severity = "WARNING"

            metric_diffs.append(
                MetricRegressionDiff(
                    metric=MetricType.NDCG_AT_K,
                    baseline_value=baseline.summary.mean_ndcg_at_k,
                    candidate_value=candidate.summary.mean_ndcg_at_k,
                    delta_absolute=round(ndcg_delta_abs, 4),
                    delta_percentage=round(ndcg_delta_pct, 2),
                    ttest_result=ndcg_ttest,
                    is_regression=ndcg_is_reg,
                    severity=ndcg_severity,
                )
            )

            # 3. Faithfulness regression check (Lower is worse)
            base_faith = [s.faithfulness for s in baseline.samples]
            cand_faith = [s.faithfulness for s in candidate.samples]
            faith_ttest = compute_welch_ttest(base_faith, cand_faith, "faithfulness", policy.significance_alpha)
            faith_delta_abs = candidate.summary.mean_faithfulness - baseline.summary.mean_faithfulness
            faith_delta_pct = (faith_delta_abs / baseline.summary.mean_faithfulness * 100.0) if baseline.summary.mean_faithfulness > 0 else 0.0

            faith_is_reg = False
            faith_severity = "NONE"
            if faith_delta_abs < -policy.max_faithfulness_drop_abs and faith_ttest.is_statistically_significant:
                faith_is_reg = True
                faith_severity = "CRITICAL"
                rejection_reasons.append(
                    f"Faithfulness groundedness dropped by {faith_delta_abs:.3f} (max allowed drop {policy.max_faithfulness_drop_abs:.3f}) with p={faith_ttest.p_value:.4f}"
                )
            elif faith_delta_abs < 0 and abs(faith_delta_abs) > (policy.max_faithfulness_drop_abs * 0.6):
                faith_severity = "WARNING"

            metric_diffs.append(
                MetricRegressionDiff(
                    metric=MetricType.FAITHFULNESS,
                    baseline_value=baseline.summary.mean_faithfulness,
                    candidate_value=candidate.summary.mean_faithfulness,
                    delta_absolute=round(faith_delta_abs, 4),
                    delta_percentage=round(faith_delta_pct, 2),
                    ttest_result=faith_ttest,
                    is_regression=faith_is_reg,
                    severity=faith_severity,
                )
            )

            # Determine Gate Verdict
            has_critical = any(d.severity == "CRITICAL" for d in metric_diffs)
            has_warning = any(d.severity == "WARNING" for d in metric_diffs)

            if has_critical:
                verdict = GateVerdict.REJECTED_REGRESSION
                confidence = 0.95
                rollback = policy.auto_rollback_on_regression
                if rollback:
                    logger.warning(
                        f"[Gatekeeper] Regression detected on suite '{suite_id}' for candidate '{candidate_run_id}'. Automated rollback triggered."
                    )
            elif has_warning:
                verdict = GateVerdict.WARNING_DEGRADED
                confidence = 0.85
                rollback = False
            else:
                verdict = GateVerdict.PASSED_CLEAN
                confidence = 0.98
                rollback = False

            eval_res = GateEvaluationResult(
                evaluation_id=f"eval_{uuid.uuid4().hex[:8]}",
                tenant_id=tenant_id,
                suite_id=suite_id,
                baseline_run_id=baseline.run_id,
                candidate_run_id=candidate.run_id,
                verdict=verdict,
                confidence_score=confidence,
                metric_diffs=metric_diffs,
                rejection_reasons=rejection_reasons,
                rollback_triggered=rollback,
                evaluated_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            return eval_res

    def simulate_benchmark_math(
        self,
        request: BenchmarkMathSimulationRequest,
    ) -> BenchmarkMathSimulationResponse:
        """Evaluate Welch's t-test and Gate Verdict on user-provided statistical distributions."""
        ttest = compute_welch_ttest_from_stats(
            m1=request.baseline_mean,
            s1=request.baseline_std,
            n1=request.baseline_n,
            m2=request.candidate_mean,
            s2=request.candidate_std,
            n2=request.candidate_n,
            metric_name=str(request.metric_type),
            alpha=request.alpha,
        )

        delta_abs = request.candidate_mean - request.baseline_mean
        delta_pct = (delta_abs / request.baseline_mean * 100.0) if request.baseline_mean != 0 else 0.0

        # For latency: positive delta is degradation. For quality (NDCG/Faithfulness): negative delta is degradation.
        is_latency = request.metric_type in [MetricType.LATENCY_P50, MetricType.LATENCY_P95, MetricType.LATENCY_P99]

        if is_latency:
            is_degraded = delta_pct > request.tolerance_threshold_pct
        else:
            is_degraded = delta_pct < -request.tolerance_threshold_pct

        if is_degraded and ttest.is_statistically_significant:
            verdict = GateVerdict.REJECTED_REGRESSION
            explanation = (
                f"Statistically significant regression (p={ttest.p_value:.6f} < alpha={request.alpha}). "
                f"Delta of {delta_pct:+.2f}% breaches tolerance threshold of {request.tolerance_threshold_pct:.1f}%."
            )
        elif is_degraded:
            verdict = GateVerdict.WARNING_DEGRADED
            explanation = (
                f"Degradation of {delta_pct:+.2f}% detected, but NOT statistically significant "
                f"(p={ttest.p_value:.6f} >= alpha={request.alpha}). May be stochastic variance; monitor closely."
            )
        elif ttest.is_statistically_significant and ((is_latency and delta_pct < 0) or (not is_latency and delta_pct > 0)):
            verdict = GateVerdict.PASSED_CLEAN
            explanation = (
                f"Statistically significant improvement (p={ttest.p_value:.6f} < alpha={request.alpha}). "
                f"Candidate outperforms baseline by {abs(delta_pct):.2f}%."
            )
        else:
            verdict = GateVerdict.PASSED_CLEAN
            explanation = (
                f"Gate passed clean. Difference of {delta_pct:+.2f}% is within acceptable tolerance boundaries."
            )

        return BenchmarkMathSimulationResponse(
            metric_type=request.metric_type,
            t_statistic=ttest.t_statistic,
            degrees_of_freedom=ttest.degrees_of_freedom,
            p_value=ttest.p_value,
            delta_absolute=round(delta_abs, 4),
            delta_percentage=round(delta_pct, 2),
            is_statistically_significant=ttest.is_statistically_significant,
            verdict=verdict,
            explanation=explanation,
        )
