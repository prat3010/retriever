"""Agentic Workflow Execution Engine.

Orchestrates stateful cyclic computation graphs, human-in-the-loop (HITL) approval
checkpoints, and time-travel state rollbacks conforming to Hexagonal Architecture.
"""

import json
import logging
import time
from uuid import uuid4

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentGraphEngineProtocol,
    AgentStep,
    HITLApprovalDecision,
    StateCheckpointerProtocol,
    ThreadCheckpoint,
    ThreadHistoryResponse,
    ToolCall,
)
from src.domain.agentic.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgenticExecutionEngine:
    """Domain service orchestrating stateful agent graph execution and thread persistence."""

    def __init__(
        self,
        graph_orchestrator: AgentGraphEngineProtocol | None = None,
        checkpointer: StateCheckpointerProtocol | None = None,
        tool_registry: ToolRegistry | None = None,
        llm_provider: LlmProvider | None = None,
    ) -> None:
        self.graph_orchestrator = graph_orchestrator
        self.checkpointer = checkpointer
        self.tools = tool_registry or ToolRegistry()
        self.llm = llm_provider

    async def execute_workflow(
        self, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Execute or initiate a stateful cyclic agent graph workflow."""
        if self.graph_orchestrator is not None:
            logger.info(
                f"Executing stateful agent workflow for tenant '{request.tenant_id}', thread '{request.thread_id or 'auto'}'"
            )
            return await self.graph_orchestrator.execute_workflow(request)

        # Legacy fallback if initialized with llm_provider directly
        return await self._execute_legacy_loop(request)

    async def resume_workflow(
        self,
        tenant_id: str,
        thread_id: str,
        decision: HITLApprovalDecision,
    ) -> AgentExecutionResult:
        """Resume an interrupted agent thread with a human approval or rejection decision."""
        if not self.graph_orchestrator:
            raise NotImplementedError("Stateful graph orchestrator not configured.")

        logger.info(
            f"Resuming agent thread '{thread_id}' for tenant '{tenant_id}' with action '{decision.action_id}' ({decision.decision})"
        )
        return await self.graph_orchestrator.resume_workflow(
            tenant_id=tenant_id,
            thread_id=thread_id,
            decision=decision,
        )

    async def get_thread_history(
        self, tenant_id: str, thread_id: str
    ) -> ThreadHistoryResponse:
        """Retrieve complete audit history of state checkpoints for time-travel debugging."""
        if not self.checkpointer:
            return ThreadHistoryResponse(
                thread_id=thread_id,
                tenant_id=tenant_id,
                total_checkpoints=0,
                checkpoints=[],
            )

        checkpoints = await self.checkpointer.list_thread_checkpoints(
            tenant_id=tenant_id, thread_id=thread_id
        )
        return ThreadHistoryResponse(
            thread_id=thread_id,
            tenant_id=tenant_id,
            total_checkpoints=len(checkpoints),
            checkpoints=checkpoints,
        )

    async def rollback_thread(
        self, tenant_id: str, thread_id: str, checkpoint_id: str, fork: bool = False
    ) -> ThreadCheckpoint:
        """Roll back thread to a prior checkpoint, pruning future state steps or branching."""
        if not self.checkpointer:
            raise NotImplementedError("Checkpointer not configured.")

        logger.info(
            f"Rolling back thread '{thread_id}' to checkpoint '{checkpoint_id}' (fork={fork})"
        )
        return await self.checkpointer.rollback_to_checkpoint(
            tenant_id=tenant_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            fork=fork,
        )

    async def _execute_legacy_loop(
        self, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Backwards-compatible lightweight ReAct tool calling execution loop."""
        start_time = time.monotonic()
        available_tools = self.tools.list_tools(request.allowed_tools)
        tools_schema_str = json.dumps(
            [t.model_dump() for t in available_tools], indent=2
        )

        system_msg = f"You are an autonomous AI Agent execution engine.\nAvailable Tools:\n{tools_schema_str}\n"
        messages = [
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=request.prompt),
        ]

        steps: list[AgentStep] = []
        final_answer = ""

        if not self.llm:
            raise ValueError("LlmProvider must be provided for agentic execution.")

        for step_idx in range(request.max_steps):
            try:
                response = await self.llm.generate(
                    InferenceRequest(messages=messages, temperature=0.1, max_tokens=1000)
                )
                raw_text = response.content.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text.strip("`").removeprefix("json").strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text.strip("`").strip()

                try:
                    parsed = json.loads(raw_text)
                    thought = parsed.get("thought", raw_text)
                    parsed_calls = parsed.get("tool_calls", [])
                    final_answer = parsed.get("final_answer", "") or ""
                except Exception:
                    thought = raw_text
                    parsed_calls = []
                    final_answer = raw_text

                tool_calls: list[ToolCall] = []
                for pc in parsed_calls:
                    call_id = f"call_{uuid4().hex[:8]}"
                    tool_calls.append(
                        ToolCall(
                            call_id=call_id,
                            tool_name=pc.get("tool_name", ""),
                            arguments=pc.get("arguments", {}),
                        )
                    )

                tool_results = []
                for tc in tool_calls:
                    res = await self.tools.execute_tool(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        arguments=tc.arguments,
                    )
                    tool_results.append(res)

                steps.append(
                    AgentStep(
                        step_index=step_idx,
                        thought=thought,
                        tool_calls=tool_calls,
                        tool_results=tool_results,
                    )
                )

                if final_answer and not tool_calls:
                    break
                if not tool_calls:
                    final_answer = thought
                    break

                messages.append(ChatMessage(role="assistant", content=raw_text))
                tool_summary = json.dumps(
                    [
                        {
                            "call_id": tr.call_id,
                            "tool_name": tr.tool_name,
                            "output": tr.output,
                            "is_error": tr.is_error,
                        }
                        for tr in tool_results
                    ]
                )
                messages.append(
                    ChatMessage(
                        role="user",
                        content=f"Tool Execution Results:\n{tool_summary}\n\nContinue or provide final_answer.",
                    )
                )
            except Exception as err:
                final_answer = f"Agent workflow halted due to error: {err!s}"
                break

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return AgentExecutionResult(
            tenant_id=request.tenant_id,
            thread_id=request.thread_id or f"thr_{uuid4().hex[:12]}",
            prompt=request.prompt,
            final_answer=final_answer or "Completed agent execution loop.",
            steps=steps,
            total_steps=len(steps),
            execution_time_ms=round(elapsed_ms, 2),
        )
