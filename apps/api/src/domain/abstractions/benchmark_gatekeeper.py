from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, Field


class MetricType(StrEnum):
    NDCG_AT_K = "ndcg_at_k"
    MRR = "mrr"
    RECALL_AT_K = "recall_at_k"
    PRECISION_AT_K = "precision_at_k"
    FAITHFULNESS = "faithfulness"
    ANSWER_RELEVANCY = "answer_relevancy"
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    COST_PER_1K = "cost_per_1k"


class GateVerdict(StrEnum):
    PASSED_CLEAN = "passed_clean"
    WARNING_DEGRADED = "warning_degraded"
    REJECTED_REGRESSION = "rejected_regression"


class BenchmarkRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BenchmarkItemSample(BaseModel):
    query_id: str = Field(..., description="Unique ID for test query")
    query_text: str = Field(..., description="Query input text")
    ground_truth_chunks: list[str] = Field(default_factory=list, description="IDs of ground truth relevant chunks")
    retrieved_chunks: list[str] = Field(default_factory=list, description="IDs of chunks retrieved by system")
    ground_truth_answer: str | None = None
    generated_answer: str | None = None
    latency_ms: float = Field(0.0, description="Latency of execution in milliseconds")
    tokens_used: int = Field(0, description="Tokens consumed")
    ndcg_at_k: float = Field(0.0, description="Computed NDCG at cutoff K")
    mrr: float = Field(0.0, description="Reciprocal rank of first relevant chunk")
    faithfulness: float = Field(0.0, description="Groundedness in retrieved context (0-1)")
    answer_relevancy: float = Field(0.0, description="Relevance to original prompt (0-1)")


class BenchmarkMetricsSummary(BaseModel):
    sample_count: int = 0
    mean_ndcg_at_k: float = 0.0
    mean_mrr: float = 0.0
    mean_recall_at_k: float = 0.0
    mean_precision_at_k: float = 0.0
    mean_faithfulness: float = 0.0
    mean_answer_relevancy: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    mean_tokens_per_query: float = 0.0


class WelchTTestResult(BaseModel):
    metric_name: str
    t_statistic: float
    degrees_of_freedom: float
    p_value: float
    is_statistically_significant: bool


class MetricRegressionDiff(BaseModel):
    metric: MetricType
    baseline_value: float
    candidate_value: float
    delta_absolute: float
    delta_percentage: float
    ttest_result: WelchTTestResult | None = None
    is_regression: bool
    severity: str = "NONE"  # "NONE", "WARNING", "CRITICAL"


class GatePolicy(BaseModel):
    max_latency_p95_increase_pct: float = Field(15.0, description="Maximum acceptable % increase in P95 latency")
    max_ndcg_drop_abs: float = Field(0.03, description="Maximum acceptable absolute drop in NDCG@K")
    max_faithfulness_drop_abs: float = Field(0.05, description="Maximum acceptable absolute drop in Faithfulness")
    significance_alpha: float = Field(0.05, description="p-value alpha significance threshold")
    min_sample_size: int = Field(10, description="Minimum samples required for statistical significance")
    auto_rollback_on_regression: bool = Field(True, description="Whether to trigger rollback signal on regression")


class BenchmarkSuite(BaseModel):
    suite_id: str
    tenant_id: str
    name: str
    description: str = ""
    k_cutoff: int = 10
    sample_queries_count: int = 0
    gate_policy: GatePolicy = Field(default_factory=GatePolicy)
    created_at: str


class BenchmarkRun(BaseModel):
    run_id: str
    tenant_id: str
    suite_id: str
    checkpoint_or_commit: str
    is_baseline: bool = False
    status: BenchmarkRunStatus = BenchmarkRunStatus.COMPLETED
    summary: BenchmarkMetricsSummary = Field(default_factory=BenchmarkMetricsSummary)
    samples: list[BenchmarkItemSample] = Field(default_factory=list)
    created_at: str


class GateEvaluationResult(BaseModel):
    evaluation_id: str
    tenant_id: str
    suite_id: str
    baseline_run_id: str
    candidate_run_id: str
    verdict: GateVerdict
    confidence_score: float
    metric_diffs: list[MetricRegressionDiff] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    rollback_triggered: bool = False
    evaluated_at: str


class BenchmarkMathSimulationRequest(BaseModel):
    metric_type: MetricType = MetricType.LATENCY_P95
    baseline_mean: float
    baseline_std: float
    baseline_n: int = 30
    candidate_mean: float
    candidate_std: float
    candidate_n: int = 30
    alpha: float = 0.05
    tolerance_threshold_pct: float = 10.0


class BenchmarkMathSimulationResponse(BaseModel):
    metric_type: MetricType
    t_statistic: float
    degrees_of_freedom: float
    p_value: float
    delta_absolute: float
    delta_percentage: float
    is_statistically_significant: bool
    verdict: GateVerdict
    explanation: str


class BenchmarkGatekeeperPort(ABC):
    """Abstract port for continuous benchmarking and regression gating."""

    @abstractmethod
    def list_suites(self, tenant_id: str) -> list[BenchmarkSuite]:
        """List all registered benchmark suites for a tenant."""

    @abstractmethod
    def create_suite(
        self,
        tenant_id: str,
        name: str,
        description: str,
        k_cutoff: int,
        gate_policy: GatePolicy | None = None,
    ) -> BenchmarkSuite:
        """Register a new benchmark suite."""

    @abstractmethod
    def list_runs(self, tenant_id: str, suite_id: str | None = None) -> list[BenchmarkRun]:
        """List historical benchmark runs."""

    @abstractmethod
    def get_run(self, tenant_id: str, run_id: str) -> BenchmarkRun | None:
        """Retrieve a benchmark run by ID."""

    @abstractmethod
    def trigger_run(
        self,
        tenant_id: str,
        suite_id: str,
        checkpoint_or_commit: str,
        is_baseline: bool = False,
        samples: list[BenchmarkItemSample] | None = None,
    ) -> BenchmarkRun:
        """Execute or record a benchmark run."""

    @abstractmethod
    def evaluate_gate(
        self,
        tenant_id: str,
        suite_id: str,
        candidate_run_id: str,
        baseline_run_id: str | None = None,
    ) -> GateEvaluationResult:
        """Evaluate candidate run against baseline using Welch's t-test and GatePolicy."""

    @abstractmethod
    def simulate_benchmark_math(
        self,
        request: BenchmarkMathSimulationRequest,
    ) -> BenchmarkMathSimulationResponse:
        """Evaluate Welch's t-test and regression gating on user-supplied distribution parameters."""
