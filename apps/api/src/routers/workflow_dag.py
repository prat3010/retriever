"""FastAPI Router for Visual DAG Workflow Canvas & Agentic Graph Composer (M126).

Provides tenant-scoped endpoints to:
1. Validate & compile declarative DAG workflows with Kahn's topological sort and cycle detection.
2. Execute multi-step DAG workflows stage-by-stage with token cost attribution and telemetry.
3. Fetch out-of-the-box enterprise workflow templates.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.abstractions.workflow_dag import (
    DAGCompilerResult,
    DAGExecutionResult,
    WorkflowDAGGraph,
)
from src.domain.workflow.dag_compiler import (
    CyclicWorkflowError,
    DAGWorkflowCompiler,
    InvalidWorkflowGraphError,
)
from src.domain.workflow.dag_executor import DAGWorkflowExecutor
from src.domain.workflow.templates import (
    get_template_by_id,
    list_enterprise_templates,
)

logger = logging.getLogger("api")

router = APIRouter(
    prefix="/v1/tenants/{tenantId}/workflows/dag",
    tags=["Visual DAG Workflows"],
)

_compiler = DAGWorkflowCompiler()


def _get_executor() -> DAGWorkflowExecutor:
    """Instantiate executor wiring real hybrid search and LLM inference if available."""
    async def _retrieval_wrapper(tenant_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            from src.domain.abstractions.retrieval import SearchQuery
            sq = SearchQuery(text=query, limit=limit)
            res = await container.search_service.search(tenant_id, sq)
            return [
                {
                    "chunk_id": doc.document_id,
                    "content": doc.content,
                    "score": round(float(doc.score), 3),
                    "meta_data": doc.meta_data,
                }
                for doc in res.documents
            ]
        except Exception as e:
            logger.warning("Dynamic search execution failed: %s", e)
            return []

    async def _llm_wrapper(prompt: str, model: str, system_prompt: str) -> str:
        try:
            from src.domain.abstractions.inference import InferenceRequest
            inf_req = InferenceRequest(prompt=prompt, system_prompt=system_prompt, model=model)
            res = await container.inference_service.infer(inf_req)
            return res.text
        except Exception as e:
            logger.warning("Dynamic LLM execution failed: %s", e)
            return ""

    return DAGWorkflowExecutor(
        compiler=_compiler,
        retrieval_fn=_retrieval_wrapper,
        llm_fn=_llm_wrapper,
    )


class ExecuteDAGRequest(BaseModel):
    """Payload to trigger execution of a declarative DAG workflow."""

    graph: WorkflowDAGGraph
    input_payload: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/compile",
    response_model=DAGCompilerResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def compile_workflow_dag(
    tenantId: str,
    graph: WorkflowDAGGraph,
) -> DAGCompilerResult:
    """Compile and validate a declarative DAG, verifying topological stages and detecting cycles."""
    return _compiler.compile(graph, raise_on_error=False)


@router.post(
    "/execute",
    response_model=DAGExecutionResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def execute_workflow_dag(
    tenantId: str,
    body: ExecuteDAGRequest,
) -> DAGExecutionResult:
    """Execute a compiled DAG workflow stage-by-stage with step auditing and token cost attribution."""
    executor = _get_executor()
    try:
        return await executor.execute(
            tenant_id=tenantId,
            graph=body.graph,
            initial_input=body.input_payload,
        )
    except CyclicWorkflowError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cyclic dependency detected: {err}",
        ) from err
    except InvalidWorkflowGraphError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow graph: {err}",
        ) from err
    except TenantIsolationViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error("DAG execution failed for tenant %s: %s", tenantId, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DAG execution error: {err}",
        ) from err


@router.get(
    "/templates",
    response_model=list[WorkflowDAGGraph],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def get_enterprise_workflow_templates(
    tenantId: str,
) -> list[WorkflowDAGGraph]:
    """List pre-configured enterprise workflow templates for instant visual loading."""
    return list_enterprise_templates()


@router.get(
    "/templates/{templateId}",
    response_model=WorkflowDAGGraph,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def get_enterprise_workflow_template_by_id(
    tenantId: str,
    templateId: str,
) -> WorkflowDAGGraph:
    """Retrieve full declarative specification of an enterprise workflow template."""
    tpl = get_template_by_id(templateId)
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{templateId}' not found.",
        )
    return tpl
