"""DSPy Prompt Compilation Domain Abstractions (Ports & Models).

Defines pure domain entities, compilation contracts, and repository protocols
for DSPy declarative prompt optimization and metric-driven teleprompter compilation.
Contains ZERO infrastructure or framework imports (no fastapi, no sqlalchemy, no dspy).
"""

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field


class FewShotDemonstration(BaseModel):
    """An optimized few-shot exemplar synthesized or selected by the teleprompter."""

    question: str
    context: str
    thought: str | None = None
    answer: str
    score: float = 1.0


class CompiledPromptProgram(BaseModel):
    """A compiled, metric-optimized prompt program for a tenant."""

    program_id: str
    tenant_id: str
    name: str = "rag_cot_optimized"
    signature_name: str = "RAGAnswerSignature"
    optimizer: str = "BootstrapFewShot"
    dataset_id: str | None = None
    baseline_score: float = 0.0
    compiled_score: float = 0.0
    improvement_pct: float = 0.0
    metric_name: str = "faithfulness_and_relevancy"
    compiled_instruction: str = ""
    few_shot_demos: list[FewShotDemonstration] = Field(default_factory=list)
    is_active: bool = False
    created_at: str = ""


class PromptCompilationRequest(BaseModel):
    """Parameters passed to trigger automated teleprompter prompt compilation."""

    tenant_id: str
    dataset_id: str | None = None
    name: str = "rag_cot_optimized"
    optimizer: Literal["BootstrapFewShot", "MIPROv2", "RandomSearch"] = "BootstrapFewShot"
    max_demos: int = Field(default=4, ge=1, le=10)
    metric_target: Literal["faithfulness", "relevancy", "composite"] = "composite"


class PromptCompilationResult(BaseModel):
    """Outcome of an automated prompt compilation cycle."""

    program_id: str
    tenant_id: str
    name: str
    optimizer: str
    baseline_score: float
    compiled_score: float
    improvement_pct: float
    demos_count: int
    compiled_instruction: str
    few_shot_demos: list[FewShotDemonstration] = Field(default_factory=list)
    is_active: bool = False


# ── Abstract Protocols (Ports) ─────────────────────────────────────────────


class DSPyCompilerProtocol(ABC):
    """Port for declarative prompt compilation & teleprompter optimization."""

    @abstractmethod
    async def compile_prompt(
        self,
        request: PromptCompilationRequest,
        train_examples: list[dict[str, Any]],
        val_examples: list[dict[str, Any]],
    ) -> PromptCompilationResult:
        """Execute teleprompter optimization against train/validation splits."""
        pass


class CompiledPromptRepositoryProtocol(ABC):
    """Port for versioned persistence of compiled prompt programs."""

    @abstractmethod
    async def save_program(self, program: CompiledPromptProgram) -> None:
        """Persist or update a compiled prompt program with tenant scoping."""
        pass

    @abstractmethod
    async def get_program(
        self, tenant_id: str, program_id: str
    ) -> CompiledPromptProgram | None:
        """Retrieve a specific compiled prompt program by ID."""
        pass

    @abstractmethod
    async def get_active_program(
        self, tenant_id: str
    ) -> CompiledPromptProgram | None:
        """Retrieve the currently active compiled prompt program for a tenant."""
        pass

    @abstractmethod
    async def list_programs(
        self, tenant_id: str
    ) -> list[CompiledPromptProgram]:
        """List all compiled prompt programs for a tenant."""
        pass

    @abstractmethod
    async def activate_program(
        self, tenant_id: str, program_id: str
    ) -> bool:
        """Set a program as active and deactivate any previous active program."""
        pass

    @abstractmethod
    async def deactivate_program(
        self, tenant_id: str, program_id: str
    ) -> bool:
        """Deactivate a compiled program, reverting tenant to default template."""
        pass

    @abstractmethod
    async def delete_program(
        self, tenant_id: str, program_id: str
    ) -> bool:
        """Delete a compiled program."""
        pass
