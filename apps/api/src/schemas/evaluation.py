from typing import Any

from pydantic import BaseModel, Field


class CreateEvalDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class AddEvalQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    ground_truth_answer: str = Field(...)
    relevant_chunk_ids: list[str] = Field(default_factory=list)


class BulkImportQuestionsRequest(BaseModel):
    questions: list[AddEvalQuestionRequest]


class TriggerSelfTuneRequest(BaseModel):
    """Request model for manually triggering or querying self-tuning parameter recommendations."""

    apply_changes: bool = Field(default=False, description="Whether to automatically apply recommendations to tenant config")


class SelfTuningReportDTO(BaseModel):
    """Response model representing self-tuning calculation details."""

    tenant_id: str
    status: str
    current_settings: dict[str, Any]
    recommended_settings: dict[str, Any]
    adjustments: list[str]
    average_faithfulness: float
    average_precision: float
    hallucination_index: float
    confidence_score: float


class NliEvaluateRequest(BaseModel):
    """Request model for evaluating semantic NLI claim entailment."""

    claims: list[str] = Field(..., min_length=1, description="List of atomic statements/claims to evaluate")
    contexts: list[str] = Field(default_factory=list, description="List of context chunks acting as premises")


class NliClassificationDTO(BaseModel):
    """DTO representing individual claim classification."""

    claim: str
    premise: str = ""
    entailment_prob: float
    contradiction_prob: float
    neutral_prob: float
    status: str


class NliEvaluateResponse(BaseModel):
    """Response model for semantic NLI evaluation."""

    total_claims: int
    entailed_claims: int
    contradicted_claims: int
    neutral_claims: int
    faithfulness_score: float
    hallucination_index: float
    classifications: list[NliClassificationDTO]


class SlmJudgeRequest(BaseModel):
    """Request model for SLM-as-a-judge reasoning."""

    query: str = Field(..., description="User query prompt")
    answer: str = Field(..., description="Generated answer text to evaluate")
    contexts: list[str] = Field(default_factory=list, description="Retrieved context chunks")


class SlmClaimAnalysisDTO(BaseModel):
    """DTO representing claim-by-claim verification analysis by SLM judge."""

    claim: str
    status: str
    evidence_span: str = ""
    confidence: float = 1.0
    rationale: str = ""


class SlmJudgeResponse(BaseModel):
    """Response model from structured SLM-as-a-judge reasoning."""

    verdict: str  # "PASS" | "FAIL" | "PARTIAL"
    faithfulness_score: float
    claim_analyses: list[SlmClaimAnalysisDTO]
    reasoning: str
    latency_ms: float


class SynthesizeDatasetRequest(BaseModel):
    """Request model for auto-synthesizing a golden evaluation dataset from document chunks."""

    name: str = Field(..., min_length=1, max_length=255)
    chunks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Explicit list of text chunk objects with 'chunk_id' and 'content'. If empty, fetched from tenant documents.",
    )
    count_per_chunk: int = Field(default=2, ge=1, le=5)


class SynthesizeDatasetResponse(BaseModel):
    """Response model for synthesized dataset creation."""

    dataset_id: str
    tenant_id: str
    name: str
    question_count: int
    questions: list[dict[str, Any]]
    created_at: str


class RegressionGateRequest(BaseModel):
    """Request model to evaluate CI/CD quality gate against benchmark scores."""

    faithfulness: float = Field(default=0.95, ge=0.0, le=1.0)
    context_precision: float = Field(default=0.90, ge=0.0, le=1.0)
    answer_relevancy: float = Field(default=0.90, ge=0.0, le=1.0)
    hallucination: float = Field(default=0.05, ge=0.0, le=1.0)
    thresholds: dict[str, float] = Field(default_factory=dict)


class RegressionGateResponse(BaseModel):
    """Response model representing CI/CD gate passage verdict and report."""

    passed: bool
    scores: dict[str, float]
    thresholds: dict[str, float]
    violations: list[str]
    summary_markdown: str
    timestamp: str



