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
