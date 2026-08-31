from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class EvalQuestion(BaseModel):
    question_id: str = ""
    dataset_id: str = ""
    question: str
    ground_truth_answer: str
    relevant_chunk_ids: list[str] = Field(default_factory=list)


class EvalDataset(BaseModel):
    dataset_id: str = ""
    tenant_id: str
    name: str
    description: str = ""
    question_count: int = 0
    created_at: str = ""


class RagasScores(BaseModel):
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0


class DeepEvalScores(BaseModel):
    hallucination: float = 0.0
    toxicity: float = 0.0
    bias: float = 0.0


class SearchMetrics(BaseModel):
    ndcg_at_10: float = 0.0
    mrr: float = 0.0
    hit_rate_at_10: float = 0.0


class EvalRunResultScores(BaseModel):
    ragas: RagasScores = Field(default_factory=RagasScores)
    deepeval: DeepEvalScores = Field(default_factory=DeepEvalScores)
    search_metrics: SearchMetrics = Field(default_factory=SearchMetrics)


class EvalRunResult(BaseModel):
    result_id: str = ""
    run_id: str = ""
    question_id: str = ""
    generated_answer: str = ""
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    scores: EvalRunResultScores = Field(default_factory=EvalRunResultScores)
    latency_ms: int = 0


class AggregateScores(BaseModel):
    ragas: RagasScores = Field(default_factory=RagasScores)
    deepeval: DeepEvalScores = Field(default_factory=DeepEvalScores)
    search_metrics: SearchMetrics = Field(default_factory=SearchMetrics)


class EvalRun(BaseModel):
    run_id: str = ""
    tenant_id: str
    dataset_id: str
    status: str = "pending"
    trigger: str = "manual"
    aggregate_scores: AggregateScores = Field(default_factory=AggregateScores)
    question_count: int = 0
    completed_count: int = 0
    created_at: str = ""
    completed_at: str | None = None


class EvalDatasetRepository(ABC):

    @abstractmethod
    async def create_dataset(self, dataset: EvalDataset) -> EvalDataset:
        pass

    @abstractmethod
    async def get_dataset(self, tenant_id: str, dataset_id: str) -> EvalDataset | None:
        pass

    @abstractmethod
    async def list_datasets(self, tenant_id: str) -> list[EvalDataset]:
        pass

    @abstractmethod
    async def delete_dataset(self, tenant_id: str, dataset_id: str) -> bool:
        pass

    @abstractmethod
    async def add_question(self, question: EvalQuestion) -> EvalQuestion:
        pass

    @abstractmethod
    async def list_questions(self, dataset_id: str) -> list[EvalQuestion]:
        pass

    @abstractmethod
    async def delete_question(self, dataset_id: str, question_id: str) -> bool:
        pass


class EvalRunRepository(ABC):

    @abstractmethod
    async def create_run(self, run: EvalRun) -> EvalRun:
        pass

    @abstractmethod
    async def get_run(self, tenant_id: str, run_id: str) -> EvalRun | None:
        pass

    @abstractmethod
    async def list_runs(self, tenant_id: str, limit: int = 20) -> list[EvalRun]:
        pass

    @abstractmethod
    async def update_run_status(self, run_id: str, status: str, aggregate_scores: dict[str, Any] | None = None) -> None:
        pass

    @abstractmethod
    async def add_result(self, result: EvalRunResult) -> EvalRunResult:
        pass

    @abstractmethod
    async def list_results(self, run_id: str) -> list[EvalRunResult]:
        pass

    @abstractmethod
    async def increment_completed(self, run_id: str) -> None:
        pass


class NliClassification(BaseModel):
    """Classification of a single claim against premise contexts."""

    claim: str
    premise: str = ""
    entailment_prob: float = 0.0
    contradiction_prob: float = 0.0
    neutral_prob: float = 1.0
    status: str = "neutral"  # "entailment" | "contradiction" | "neutral"


class NliEvaluationResult(BaseModel):
    """Aggregate semantic NLI evaluation result across claims."""

    total_claims: int
    entailed_claims: int
    contradicted_claims: int
    neutral_claims: int
    faithfulness_score: float
    hallucination_index: float
    classifications: list[NliClassification] = Field(default_factory=list)


class SlmClaimAnalysis(BaseModel):
    """Detailed evidence reasoning for an individual claim by SLM judge."""

    claim: str
    status: str  # "supported" | "unsupported" | "contradicted"
    evidence_span: str = ""
    confidence: float = 1.0
    rationale: str = ""


class SlmJudgeResult(BaseModel):
    """Structured verdict and reasoning from SLM-as-a-judge."""

    verdict: str  # "PASS" | "FAIL" | "PARTIAL"
    faithfulness_score: float
    claim_analyses: list[SlmClaimAnalysis] = Field(default_factory=list)
    reasoning: str = ""
    latency_ms: float = 0.0


class BaseNliEvaluator(ABC):
    """Abstract port for Natural Language Inference evaluation."""

    @abstractmethod
    def evaluate_claims(
        self, claims: list[str], contexts: list[str]
    ) -> NliEvaluationResult:
        """Evaluate claim-premise semantic entailment and contradiction."""
        pass


class BaseSlmJudge(ABC):
    """Abstract port for Small Language Model judge reasoning."""

    @abstractmethod
    async def judge_response(
        self, query: str, answer: str, contexts: list[str], llm_provider: Any = None
    ) -> SlmJudgeResult:
        """Evaluate factual grounding and return structured JSON verdict."""
        pass


class SyntheticQuestionCandidate(BaseModel):
    """Synthesized golden test question paired with ground truth and source chunk IDs."""

    question: str
    ground_truth_answer: str
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    archetype: str = "factual"  # "factual" | "multi_hop" | "conditional"
    confidence_score: float = 1.0


class RegressionGateThresholds(BaseModel):
    """Strict quality gating thresholds for CI/CD pipeline blocking."""

    min_faithfulness: float = 0.90
    min_context_precision: float = 0.85
    min_answer_relevancy: float = 0.85
    max_hallucination: float = 0.10


class RegressionGateReport(BaseModel):
    """Evaluation gate report with verdict, metrics deltas, and markdown summary."""

    passed: bool
    scores: dict[str, float] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)
    violations: list[str] = Field(default_factory=list)
    summary_markdown: str = ""
    timestamp: str = ""


class BaseSyntheticDatasetGenerator(ABC):
    """Abstract port for synthesizing benchmark datasets from document chunks."""

    @abstractmethod
    async def synthesize_from_chunks(
        self, chunks: list[dict[str, Any]], count_per_chunk: int = 2
    ) -> list[SyntheticQuestionCandidate]:
        """Synthesize high-coverage Q&A pairs from text chunks."""
        pass


class BaseRegressionGate(ABC):
    """Abstract port for automated CI/CD regression gating."""

    @abstractmethod
    def evaluate_gate(
        self, aggregate_scores: AggregateScores, thresholds: RegressionGateThresholds | None = None
    ) -> RegressionGateReport:
        """Evaluate aggregate scores against thresholds and produce a CI gate report."""
        pass


