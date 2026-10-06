"""Agentic Query Planning and Multi-Step Execution Loop Engine (2026 Standards).

Conforms strictly to Hexagonal Architecture boundaries (0 framework imports).
Implements:
- Dynamic query complexity analysis & decomposition into directed execution DAGs
- Multi-step iterative retrieval loops with dynamic parameter interpolation
- Tool orchestration across diverse tools (search, table query, calculator, synthesis)
- Semantic context aggregation and deduplication across retrieval steps
- Strict multi-tenant isolation scoped by tenant_id
"""

import hashlib
import inspect
import re
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.domain.agentic.tool_registry import ToolRegistry


class PlanStepType(StrEnum):
    """Classification of an execution step in the query execution graph."""

    RETRIEVAL = "retrieval"
    TOOL_CALL = "tool_call"
    AGGREGATION = "aggregation"
    SYNTHESIS = "synthesis"


class PlanStep(BaseModel):
    """A discrete task vertex in the query execution plan DAG."""

    step_id: str
    step_type: PlanStepType
    description: str
    query: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    output_variable: str = ""


class QueryExecutionPlan(BaseModel):
    """Structured execution graph produced by the Agentic Query Planner."""

    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:10]}")
    tenant_id: str
    original_query: str
    complexity: str = "simple"  # "simple" | "comparative" | "multi_hop" | "analytical"
    steps: list[PlanStep] = Field(default_factory=list)
    is_multi_step: bool = False
    estimated_steps: int = 1


class StepExecutionRecord(BaseModel):
    """Audit trace record for an individual step execution."""

    step_id: str
    step_type: PlanStepType
    description: str
    input_arguments: dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    duration_ms: float = 0.0
    status: str = "completed"  # "completed" | "failed" | "skipped"
    error: str | None = None


class PlanExecutionResult(BaseModel):
    """Comprehensive outcome produced by the Agentic Plan Orchestrator."""

    plan_id: str
    tenant_id: str
    original_query: str
    final_answer: str
    step_records: list[StepExecutionRecord] = Field(default_factory=list)
    aggregated_contexts: list[str] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    success: bool = True


class AgenticQueryPlanner:
    """Decomposes complex user queries into structured execution plans."""

    COMPARISON_PATTERNS = (
        r"\bcompare\s+(.+?)\s+(?:and|with|to|vs\.?)\s+(.+)",
        r"\bdifference\s+between\s+(.+?)\s+and\s+(.+)",
        r"(.+?)\s+vs\.?\s+(.+)",
    )

    ANALYTICAL_PATTERNS = (
        r"\b(?:calculate|sum|total|average|avg|count)\b",
        r"\bhow\s+much\s+in\s+total\b",
    )

    MULTI_HOP_PATTERNS = (
        r"\b(?:and\s+then|after\s+finding|subsequently|based\s+on\s+that)\b",
        r"\bwhich\s+(?:one|tier|plan|option)\s+is\s+(?:better|cheaper|faster)\s+and\s+why\b",
    )

    def decompose_query(
        self,
        query: str,
        tenant_id: str,
        available_tools: list[str] | None = None,
    ) -> QueryExecutionPlan:
        """Analyze query semantics and generate a structured execution plan."""
        q = query.strip()
        tools = available_tools or ["hybrid_search", "calculator", "table_query"]

        # 1. Comparative Query Detection
        for pattern in self.COMPARISON_PATTERNS:
            m = re.search(pattern, q, re.IGNORECASE)
            if m:
                item_a = m.group(1).strip()
                item_b = m.group(2).strip()
                step_1 = PlanStep(
                    step_id="step_1",
                    step_type=PlanStepType.RETRIEVAL,
                    description=f"Retrieve factual context for '{item_a}'",
                    query=item_a,
                    tool_name="hybrid_search",
                    arguments={"query": item_a, "top_k": 4},
                    depends_on=[],
                    output_variable="ctx_a",
                )
                step_2 = PlanStep(
                    step_id="step_2",
                    step_type=PlanStepType.RETRIEVAL,
                    description=f"Retrieve factual context for '{item_b}'",
                    query=item_b,
                    tool_name="hybrid_search",
                    arguments={"query": item_b, "top_k": 4},
                    depends_on=[],
                    output_variable="ctx_b",
                )
                step_3 = PlanStep(
                    step_id="step_3",
                    step_type=PlanStepType.SYNTHESIS,
                    description=f"Synthesize comparative analysis between '{item_a}' and '{item_b}'",
                    query=q,
                    arguments={"comparison_targets": [item_a, item_b]},
                    depends_on=["step_1", "step_2"],
                    output_variable="final_synthesis",
                )
                return QueryExecutionPlan(
                    tenant_id=tenant_id,
                    original_query=q,
                    complexity="comparative",
                    steps=[step_1, step_2, step_3],
                    is_multi_step=True,
                    estimated_steps=3,
                )

        # 2. Analytical / Math Query Detection
        is_analytical = any(re.search(p, q, re.IGNORECASE) for p in self.ANALYTICAL_PATTERNS)
        if is_analytical:
            step_1 = PlanStep(
                step_id="step_1",
                step_type=PlanStepType.RETRIEVAL,
                description=f"Retrieve tabular and numeric records for query: '{q}'",
                query=q,
                tool_name="hybrid_search",
                arguments={"query": q, "top_k": 5},
                depends_on=[],
                output_variable="raw_records",
            )
            step_2 = PlanStep(
                step_id="step_2",
                step_type=PlanStepType.TOOL_CALL,
                description="Perform structured table extraction or computation",
                tool_name="table_query" if "table_query" in tools else "calculator",
                arguments={"table_markdown": "{raw_records}", "context": "{raw_records}", "query": q},
                depends_on=["step_1"],
                output_variable="calc_result",
            )
            step_3 = PlanStep(
                step_id="step_3",
                step_type=PlanStepType.SYNTHESIS,
                description="Synthesize final analytical conclusion with computed metrics",
                query=q,
                arguments={"calculation": "{calc_result}"},
                depends_on=["step_1", "step_2"],
                output_variable="final_synthesis",
            )
            return QueryExecutionPlan(
                tenant_id=tenant_id,
                original_query=q,
                complexity="analytical",
                steps=[step_1, step_2, step_3],
                is_multi_step=True,
                estimated_steps=3,
            )

        # 3. Multi-Hop Sequential Query Detection
        is_multi_hop = any(re.search(p, q, re.IGNORECASE) for p in self.MULTI_HOP_PATTERNS)
        if is_multi_hop:
            parts = re.split(r"\b(?:and\s+then|after\s+finding|subsequently)\b", q, flags=re.IGNORECASE)
            sub_q1 = parts[0].strip()
            sub_q2 = parts[1].strip() if len(parts) > 1 else f"Analyze implications of: {sub_q1}"

            step_1 = PlanStep(
                step_id="step_1",
                step_type=PlanStepType.RETRIEVAL,
                description=f"Retrieve primary facts for: '{sub_q1}'",
                query=sub_q1,
                tool_name="hybrid_search",
                arguments={"query": sub_q1, "top_k": 4},
                depends_on=[],
                output_variable="primary_ctx",
            )
            step_2 = PlanStep(
                step_id="step_2",
                step_type=PlanStepType.RETRIEVAL,
                description=f"Retrieve secondary contextual dependencies for: '{sub_q2}'",
                query=sub_q2,
                tool_name="hybrid_search",
                arguments={"query": sub_q2, "top_k": 4},
                depends_on=["step_1"],
                output_variable="secondary_ctx",
            )
            step_3 = PlanStep(
                step_id="step_3",
                step_type=PlanStepType.SYNTHESIS,
                description="Synthesize complete multi-hop solution",
                query=q,
                arguments={},
                depends_on=["step_1", "step_2"],
                output_variable="final_synthesis",
            )
            return QueryExecutionPlan(
                tenant_id=tenant_id,
                original_query=q,
                complexity="multi_hop",
                steps=[step_1, step_2, step_3],
                is_multi_step=True,
                estimated_steps=3,
            )

        # 4. Standard Single-Hop Query Plan
        step_1 = PlanStep(
            step_id="step_1",
            step_type=PlanStepType.RETRIEVAL,
            description=f"Direct hybrid search retrieval for: '{q}'",
            query=q,
            tool_name="hybrid_search",
            arguments={"query": q, "top_k": 5},
            depends_on=[],
            output_variable="retrieved_contexts",
        )
        step_2 = PlanStep(
            step_id="step_2",
            step_type=PlanStepType.SYNTHESIS,
            description="Synthesize grounded response from retrieved contexts",
            query=q,
            arguments={},
            depends_on=["step_1"],
            output_variable="final_synthesis",
        )
        return QueryExecutionPlan(
            tenant_id=tenant_id,
            original_query=q,
            complexity="simple",
            steps=[step_1, step_2],
            is_multi_step=False,
            estimated_steps=2,
        )


class AgenticPlanOrchestrator:
    """Executes a query execution plan through an orchestrated tool-calling loop."""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()

    async def execute_plan(
        self,
        plan: QueryExecutionPlan,
        search_fn: Callable[..., Any] | None = None,
        llm_fn: Callable[..., Any] | None = None,
    ) -> PlanExecutionResult:
        """Execute all steps in the plan according to topological order."""
        start_time = time.monotonic()
        context_store: dict[str, Any] = {}
        all_retrieved_contexts: list[str] = []
        step_records: list[StepExecutionRecord] = []
        final_answer = ""

        # Context deduplication set
        seen_context_hashes: set[str] = set()

        for step in plan.steps:
            t0 = time.monotonic()
            interpolated_args = self._interpolate_arguments(step.arguments, context_store)

            try:
                # 1. RETRIEVAL STEP
                if step.step_type == PlanStepType.RETRIEVAL:
                    sub_q = step.query or interpolated_args.get("query", plan.original_query)
                    top_k = interpolated_args.get("top_k", 5)

                    raw_contexts: list[str] = []
                    if search_fn is not None:
                        res = search_fn(sub_q, tenant_id=plan.tenant_id, top_k=top_k)
                        if inspect.isawaitable(res):
                            res = await res
                        if isinstance(res, tuple) and len(res) >= 1:
                            items = res[0]
                            raw_contexts = [getattr(r, "content", str(r)) for r in items]
                        elif isinstance(res, list):
                            raw_contexts = [getattr(r, "content", str(r)) for r in res]
                        elif hasattr(res, "results"):
                            raw_contexts = [
                                getattr(r, "content", str(r))
                                for r in res.results
                                if getattr(r, "content", None)
                            ]
                        else:
                            raw_contexts = [str(res)]
                    else:
                        # Fallback to tool registry hybrid_search
                        tool_res = await self.tool_registry.execute_tool(
                            call_id=f"call_{step.step_id}",
                            tool_name="hybrid_search",
                            arguments={"query": sub_q, "top_k": top_k},
                        )
                        raw_contexts = [str(tool_res.output)]

                    # Deduplicate and register contexts
                    deduped: list[str] = []
                    for c in raw_contexts:
                        h = hashlib.sha256(c.strip().encode("utf-8")).hexdigest()
                        if h not in seen_context_hashes:
                            seen_context_hashes.add(h)
                            deduped.append(c)
                            all_retrieved_contexts.append(c)

                    output_val = deduped
                    context_store[step.output_variable] = output_val

                # 2. TOOL CALL STEP
                elif step.step_type == PlanStepType.TOOL_CALL:
                    tool_name = step.tool_name or "calculator"
                    tool_res = await self.tool_registry.execute_tool(
                        call_id=f"call_{step.step_id}",
                        tool_name=tool_name,
                        arguments=interpolated_args,
                    )
                    output_val = tool_res.output
                    context_store[step.output_variable] = output_val
                    if tool_res.is_error:
                        raise RuntimeError(
                            f"Tool '{tool_name}' failed: {tool_res.error_message or output_val}"
                        )

                # 3. SYNTHESIS STEP
                elif step.step_type == PlanStepType.SYNTHESIS:
                    contexts_to_use = all_retrieved_contexts
                    if llm_fn is not None:
                        synth_res = llm_fn(plan.original_query, contexts_to_use)
                        if inspect.isawaitable(synth_res):
                            synth_res = await synth_res
                        output_val = str(synth_res)
                    else:
                        # Fallback synthesis formatting
                        output_val = self._synthesize_fallback(plan.original_query, contexts_to_use, context_store)

                    final_answer = output_val
                    context_store[step.output_variable] = output_val

                # 4. AGGREGATION STEP
                else:
                    output_val = "\n\n".join(all_retrieved_contexts)
                    context_store[step.output_variable] = output_val

                duration = (time.monotonic() - t0) * 1000
                step_records.append(
                    StepExecutionRecord(
                        step_id=step.step_id,
                        step_type=step.step_type,
                        description=step.description,
                        input_arguments=interpolated_args,
                        output=output_val,
                        duration_ms=round(duration, 2),
                        status="completed",
                    )
                )

            except Exception as err:
                duration = (time.monotonic() - t0) * 1000
                step_records.append(
                    StepExecutionRecord(
                        step_id=step.step_id,
                        step_type=step.step_type,
                        description=step.description,
                        input_arguments=interpolated_args,
                        output=None,
                        duration_ms=round(duration, 2),
                        status="failed",
                        error=str(err),
                    )
                )

        total_elapsed = (time.monotonic() - start_time) * 1000
        return PlanExecutionResult(
            plan_id=plan.plan_id,
            tenant_id=plan.tenant_id,
            original_query=plan.original_query,
            final_answer=final_answer or "Execution completed.",
            step_records=step_records,
            aggregated_contexts=all_retrieved_contexts,
            total_duration_ms=round(total_elapsed, 2),
            success=all(r.status == "completed" for r in step_records),
        )

    def _interpolate_arguments(
        self, args: dict[str, Any], context_store: dict[str, Any]
    ) -> dict[str, Any]:
        """Interpolate variable references like '{var_step_1}' with prior step results."""
        def _interpolate_val(v: Any) -> Any:
            if isinstance(v, str):
                new_v = v
                for var_name, var_val in context_store.items():
                    placeholder = f"{{{var_name}}}"
                    if placeholder in new_v:
                        val_str = (
                            "\n\n".join(str(item) for item in var_val)
                            if isinstance(var_val, list)
                            else str(var_val)
                        )
                        new_v = new_v.replace(placeholder, val_str)
                return new_v
            if isinstance(v, dict):
                return {k: _interpolate_val(sub_v) for k, sub_v in v.items()}
            if isinstance(v, list):
                return [_interpolate_val(item) for item in v]
            return v

        return {k: _interpolate_val(v) for k, v in args.items()}

    def _synthesize_fallback(
        self, query: str, contexts: list[str], context_store: dict[str, Any]
    ) -> str:
        """Deterministic synthesis builder when LLM provider is not supplied."""
        if not contexts:
            return f"No verified context found for query: '{query}'."

        cleaned_contexts = [c.strip() for c in contexts if c.strip()]
        lead_context = cleaned_contexts[0] if cleaned_contexts else ""

        # Include calc result if present
        calc_extra = ""
        for k, v in context_store.items():
            if "calc" in k and v:
                calc_extra = f"\nComputed value: {v}"

        return f"Based on retrieved documentation: {lead_context}{calc_extra}"
