"""FastAPI Router for DSPy Prompt Compilation & Program Optimization.

Provides REST APIs for automated teleprompter prompt compilation,
metric inspection, and hot-activation in production RAG inference.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.container import container
from src.domain.abstractions.exceptions import (
    TenantIsolationViolationError,
)
from src.domain.inference.dspy_abstractions import (
    CompiledPromptProgram,
    PromptCompilationRequest,
    PromptCompilationResult,
)

router = APIRouter(
    prefix="/v1/tenants/{tenantId}/prompts",
    tags=["prompts", "dspy", "cognitive"],
    dependencies=[Depends(verify_admin_key)],
)


class CompilePromptApiPayload(BaseModel):
    name: str = "rag_cot_optimized"
    dataset_id: str | None = None
    optimizer: str = Field(default="BootstrapFewShot")
    max_demos: int = Field(default=4, ge=1, le=10)
    metric_target: str = Field(default="composite")


@router.post("/compile", response_model=PromptCompilationResult)
async def compile_prompt(
    tenantId: str,
    payload: CompilePromptApiPayload,
) -> PromptCompilationResult:
    """Run automated teleprompter optimization for a tenant's prompt program."""
    try:
        # Load examples from evaluation dataset if specified
        train_examples: list[dict[str, Any]] = []
        val_examples: list[dict[str, Any]] = []

        if payload.dataset_id and hasattr(container, "eval_dataset_repo"):
            try:
                eval_repo = container.eval_dataset_repo
                # Try fetching questions for this dataset
                questions = await eval_repo.list_questions(payload.dataset_id)
                if questions:
                    for q in questions:
                        # Extract document chunks if available
                        ex = {
                            "question": q.question,
                            "context": f"Relevant background for answering: {q.question}",
                            "ground_truth_answer": q.ground_truth_answer,
                        }
                        train_examples.append(ex)
                    val_examples = list(train_examples)
            except Exception:
                pass

        req = PromptCompilationRequest(
            tenant_id=tenantId,
            dataset_id=payload.dataset_id,
            name=payload.name,
            optimizer=payload.optimizer,  # type: ignore
            max_demos=payload.max_demos,
            metric_target=payload.metric_target,  # type: ignore
        )

        compiler = container.dspy_compiler
        result = await compiler.compile_prompt(req, train_examples, val_examples)

        # Persist compiled program to repository
        compiled_program = CompiledPromptProgram(
            program_id=result.program_id,
            tenant_id=tenantId,
            name=result.name,
            signature_name="RAGAnswerSignature",
            optimizer=result.optimizer,
            dataset_id=payload.dataset_id,
            baseline_score=result.baseline_score,
            compiled_score=result.compiled_score,
            improvement_pct=result.improvement_pct,
            metric_name=payload.metric_target,
            compiled_instruction=result.compiled_instruction,
            few_shot_demos=result.few_shot_demos,
            is_active=False,
        )

        repo = container.compiled_prompt_repo
        await repo.save_program(compiled_program)

        return result

    except TenantIsolationViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt compilation failed: {exc}",
        ) from exc


@router.get("/compiled", response_model=list[CompiledPromptProgram])
async def list_compiled_prompts(
    tenantId: str,
) -> list[CompiledPromptProgram]:
    """List all compiled DSPy prompt programs for a tenant."""
    try:
        repo = container.compiled_prompt_repo
        return await repo.list_programs(tenantId)
    except TenantIsolationViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/compiled/active", response_model=CompiledPromptProgram | None)
async def get_active_compiled_prompt(
    tenantId: str,
) -> CompiledPromptProgram | None:
    """Fetch the currently active compiled prompt program for a tenant."""
    try:
        repo = container.compiled_prompt_repo
        return await repo.get_active_program(tenantId)
    except TenantIsolationViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/compiled/{programId}/activate", response_model=CompiledPromptProgram)
async def activate_compiled_prompt(
    tenantId: str,
    programId: str,
) -> CompiledPromptProgram:
    """Activate a compiled DSPy program in production for active tenant chat."""
    try:
        repo = container.compiled_prompt_repo
        success = await repo.activate_program(tenantId, programId)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Compiled program {programId} not found for tenant {tenantId}",
            )
        program = await repo.get_program(tenantId, programId)
        if not program:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
        return program
    except HTTPException:
        raise
    except TenantIsolationViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/compiled/{programId}/deactivate", response_model=CompiledPromptProgram)
async def deactivate_compiled_prompt(
    tenantId: str,
    programId: str,
) -> CompiledPromptProgram:
    """Deactivate a compiled DSPy program, reverting to default handcrafted template."""
    try:
        repo = container.compiled_prompt_repo
        await repo.deactivate_program(tenantId, programId)
        program = await repo.get_program(tenantId, programId)
        if not program:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
        return program
    except HTTPException:
        raise
    except TenantIsolationViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/compiled/{programId}")
async def delete_compiled_prompt(
    tenantId: str,
    programId: str,
) -> dict[str, Any]:
    """Delete a compiled prompt program."""
    try:
        repo = container.compiled_prompt_repo
        success = await repo.delete_program(tenantId, programId)
        return {"success": success, "deleted_program_id": programId}
    except TenantIsolationViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
