"""LangGraph Cyclic Agentic Orchestration Adapter.

Implements stateful cyclic reasoning graphs, Human-in-the-Loop (HITL) approval gates,
and persistent checkpointing conforming to Hexagonal Architecture.
"""

import json
import logging
import time
from typing import Any, TypedDict
from uuid import uuid4

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentGraphEngineProtocol,
    AgentStep,
    HITLApprovalDecision,
    HITLApprovalRequest,
    StateCheckpointerProtocol,
    ThreadCheckpoint,
    ToolCall,
    ToolResult,
)
from src.domain.agentic.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# State schema for the agent computation graph
class GraphState(TypedDict, total=False):
    tenant_id: str
    thread_id: str
    prompt: str
    messages: list[dict[str, str]]
    steps: list[dict[str, Any]]
    step_count: int
    max_steps: int
    allowed_tools: list[str] | None
    pending_approval: dict[str, Any] | None
    final_answer: str
    status: str  # "running" | "waiting_approval" | "completed" | "rejected" | "error"
    active_checkpoint_id: str | None
    execution_time_ms: float
    current_calls: list[dict[str, Any]]
    latest_tool_results: list[dict[str, Any]]


AGENTIC_PROMPT_TEMPLATE = """You are an autonomous AI Agent operating inside the Retriever platform.
Your task is to accomplish the user's objective using multi-turn reasoning and available tools.

Available Tools:
{tools_schema}

OPERATIONAL INSTRUCTIONS:
1. Break down the user prompt into clear, actionable steps.
2. In each turn, return strictly valid JSON matching this schema:
{{
  "thought": "Your internal chain-of-thought planning for this step",
  "tool_calls": [
    {{
      "tool_name": "name_of_tool",
      "arguments": {{ ... }}
    }}
  ],
  "final_answer": "Your comprehensive final answer if no more tools are required, otherwise null"
}}
3. If the objective is satisfied, set "final_answer" to your response and leave "tool_calls" empty.
4. Output raw valid JSON without markdown formatting.
"""


class LangGraphOrchestrator(AgentGraphEngineProtocol):
    """Concrete orchestrator powering cyclic agent workflows with HITL state gates."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        tool_registry: ToolRegistry,
        checkpointer: StateCheckpointerProtocol,
    ) -> None:
        self.llm = llm_provider
        self.tools = tool_registry
        self.checkpointer = checkpointer
        self._compiled_graph = self._build_langgraph_graph()

    def _build_langgraph_graph(self) -> Any:
        """Construct the LangGraph StateGraph topology with cyclic and conditional edges."""
        try:
            from langgraph.graph import END, START, StateGraph

            builder = StateGraph(GraphState)

            # Register graph nodes
            builder.add_node("reasoner", self._reasoner_node)
            builder.add_node("hitl_gate", self._hitl_gate_node)
            builder.add_node("tool_executor", self._tool_executor_node)
            builder.add_node("synthesizer", self._synthesizer_node)

            # Entry edge
            builder.add_edge(START, "reasoner")

            # Conditional routing after reasoning
            builder.add_conditional_edges(
                "reasoner",
                self._route_after_reasoner,
                {
                    "hitl_gate": "hitl_gate",
                    "tool_executor": "tool_executor",
                    "synthesizer": "synthesizer",
                },
            )

            # HITL Gate halts graph execution (pauses for external human response)
            builder.add_edge("hitl_gate", END)

            # Tool Executor cycles back to Reasoner (Iterative cyclic reflection loop)
            builder.add_edge("tool_executor", "reasoner")

            # Synthesizer finishes the run
            builder.add_edge("synthesizer", END)

            logger.info("Successfully compiled LangGraph StateGraph topology.")
            return builder.compile()
        except ImportError:
            logger.info("langgraph package not directly available; using resilient cyclic graph engine.")
            return None

    # ── Graph Node Callbacks ─────────────────────────────────────────────────

    async def _reasoner_node(self, state: GraphState) -> GraphState:
        """Reasoner Node: Consults LLM to evaluate conversation context and plan next actions."""
        step_idx = state.get("step_count", 0)
        max_steps = state.get("max_steps", 10)

        # Check if max steps exceeded
        if step_idx >= max_steps:
            state["status"] = "completed"
            if not state.get("final_answer"):
                state["final_answer"] = (
                    f"Agent reached maximum reasoning step limit ({max_steps}) without further action."
                )
            return state

        # Prepare system instructions with tool schemas
        available_tools = self.tools.list_tools(state.get("allowed_tools"))
        tools_json_str = json.dumps([t.model_dump() for t in available_tools], indent=2)
        system_prompt = AGENTIC_PROMPT_TEMPLATE.format(tools_schema=tools_json_str)

        # Reconstruct chat messages
        llm_messages = [ChatMessage(role="system", content=system_prompt)]
        for msg in state.get("messages", []):
            llm_messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

        # Append latest tool observations or human rejection feedback if present
        latest_results = state.get("latest_tool_results", [])
        if latest_results:
            summary = json.dumps(latest_results, indent=2)
            llm_messages.append(
                ChatMessage(
                    role="user",
                    content=f"Tool Execution Observations:\n{summary}\n\nContinue reasoning or provide final_answer.",
                )
            )

        try:
            inference_resp = await self.llm.generate(
                InferenceRequest(
                    messages=llm_messages,
                    temperature=0.1,
                    max_tokens=1500,
                )
            )
            raw_text = inference_resp.content.strip()

            # Clean markdown code blocks if emitted
            cleaned = raw_text
            if cleaned.startswith("```json"):
                cleaned = cleaned.strip("`").removeprefix("json").strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned.strip("`").strip()

            parsed = json.loads(cleaned)
            thought = parsed.get("thought", raw_text)
            parsed_calls = parsed.get("tool_calls", [])
            final_ans = parsed.get("final_answer") or ""

        except Exception as err:
            logger.debug(f"JSON parse fallback in reasoner node ({err})")
            thought = raw_text if "raw_text" in locals() else f"Reasoning error: {err!s}"
            parsed_calls = []
            final_ans = thought

        # Store parsed calls into state
        state["current_calls"] = parsed_calls
        if final_ans:
            state["final_answer"] = final_ans

        # Append assistant reasoning to chat messages
        state.setdefault("messages", []).append(
            {"role": "assistant", "content": json.dumps({"thought": thought, "tool_calls": parsed_calls, "final_answer": final_ans})}
        )

        # Record step thought
        step_record = {
            "step_index": step_idx,
            "thought": thought,
            "tool_calls": [
                {
                    "call_id": f"call_{uuid4().hex[:8]}",
                    "tool_name": c.get("tool_name", ""),
                    "arguments": c.get("arguments", {}),
                }
                for c in parsed_calls
            ],
            "tool_results": [],
        }
        state.setdefault("steps", []).append(step_record)

        return state

    def _route_after_reasoner(self, state: GraphState) -> str:
        """Conditional Router: Inspects tool calls and routes to HITL Gate, Tool Executor, or Synthesizer."""
        final_answer = state.get("final_answer", "")
        calls = state.get("current_calls", [])
        step_idx = state.get("step_count", 0)
        max_steps = state.get("max_steps", 10)

        if step_idx >= max_steps:
            return "synthesizer"

        if final_answer and not calls:
            return "synthesizer"

        if not calls:
            return "synthesizer"

        # Check if ANY candidate tool is marked sensitive (requires human approval)
        for call in calls:
            tool_name = call.get("tool_name", "")
            if self.tools.is_tool_sensitive(tool_name):
                return "hitl_gate"

        return "tool_executor"

    async def _hitl_gate_node(self, state: GraphState) -> GraphState:
        """HITL Gate Node: Halts execution before sensitive operations and generates approval request."""
        calls = state.get("current_calls", [])
        sensitive_call = next(
            (c for c in calls if self.tools.is_tool_sensitive(c.get("tool_name", ""))),
            calls[0] if calls else {},
        )

        tool_name = sensitive_call.get("tool_name", "unknown_tool")
        arguments = sensitive_call.get("arguments", {})
        risk_level = self.tools.get_tool_risk(tool_name)
        action_id = f"act_{uuid4().hex[:8]}"

        approval_req = {
            "action_id": action_id,
            "thread_id": state["thread_id"],
            "tenant_id": state["tenant_id"],
            "tool_name": tool_name,
            "arguments": arguments,
            "risk_level": risk_level,
            "description": f"Execute sensitive operation '{tool_name}' on tenant {state['tenant_id']}",
            "status": "pending",
            "created_at": time.time(),
        }

        state["pending_approval"] = approval_req
        state["status"] = "waiting_approval"

        # Save checkpoint before halting
        chk_id = f"chk_{state['thread_id']}_step{state.get('step_count', 0)}_hitl"
        state["active_checkpoint_id"] = chk_id
        checkpoint = ThreadCheckpoint(
            checkpoint_id=chk_id,
            thread_id=state["thread_id"],
            tenant_id=state["tenant_id"],
            node_name="hitl_gate",
            step_index=state.get("step_count", 0),
            state_snapshot=dict(state),
            created_at=time.time(),
        )
        await self.checkpointer.save_checkpoint(checkpoint)
        logger.info(
            f"HITL Gate halted thread '{state['thread_id']}' on sensitive tool '{tool_name}' (action_id={action_id})"
        )

        return state

    async def _tool_executor_node(self, state: GraphState) -> GraphState:
        """Tool Executor Node: Executes safe tools and produces structured observations."""
        calls = state.get("current_calls", [])
        latest_steps = state.get("steps", [])
        active_step = latest_steps[-1] if latest_steps else None

        executed_results = []
        tool_call_objs = active_step.get("tool_calls", []) if active_step else []

        for idx, call_data in enumerate(calls):
            call_id = tool_call_objs[idx]["call_id"] if idx < len(tool_call_objs) else f"call_{uuid4().hex[:8]}"
            tool_name = call_data.get("tool_name", "")
            args = call_data.get("arguments", {})

            res = await self.tools.execute_tool(
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
            )
            result_dict = res.model_dump()
            executed_results.append(result_dict)
            if active_step:
                active_step.setdefault("tool_results", []).append(result_dict)

        state["latest_tool_results"] = executed_results
        state["current_calls"] = []
        state["step_count"] = state.get("step_count", 0) + 1

        # Save iterative checkpoint
        chk_id = f"chk_{state['thread_id']}_step{state['step_count']}"
        state["active_checkpoint_id"] = chk_id
        checkpoint = ThreadCheckpoint(
            checkpoint_id=chk_id,
            thread_id=state["thread_id"],
            tenant_id=state["tenant_id"],
            node_name="tool_executor",
            step_index=state["step_count"],
            state_snapshot=dict(state),
            created_at=time.time(),
        )
        await self.checkpointer.save_checkpoint(checkpoint)

        return state

    async def _synthesizer_node(self, state: GraphState) -> GraphState:
        """Synthesizer Node: Finalizes agent response and wraps execution."""
        state["status"] = "completed"
        if not state.get("final_answer"):
            steps = state.get("steps", [])
            state["final_answer"] = steps[-1].get("thought", "Task completed.") if steps else "Workflow completed."

        chk_id = f"chk_{state['thread_id']}_step{state.get('step_count', 0)}_final"
        state["active_checkpoint_id"] = chk_id
        checkpoint = ThreadCheckpoint(
            checkpoint_id=chk_id,
            thread_id=state["thread_id"],
            tenant_id=state["tenant_id"],
            node_name="synthesizer",
            step_index=state.get("step_count", 0),
            state_snapshot=dict(state),
            created_at=time.time(),
        )
        await self.checkpointer.save_checkpoint(checkpoint)
        return state

    # ── Orchestrator Public API ──────────────────────────────────────────────

    async def execute_workflow(
        self, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Execute a multi-step agentic graph workflow."""
        start_time = time.monotonic()
        thread_id = request.thread_id or f"thr_{uuid4().hex[:12]}"

        # Initialize graph state
        initial_state: GraphState = {
            "tenant_id": request.tenant_id,
            "thread_id": thread_id,
            "prompt": request.prompt,
            "messages": [{"role": "user", "content": request.prompt}],
            "steps": [],
            "step_count": 0,
            "max_steps": request.max_steps,
            "allowed_tools": request.allowed_tools,
            "pending_approval": None,
            "final_answer": "",
            "status": "running",
            "active_checkpoint_id": None,
            "current_calls": [],
            "latest_tool_results": [],
        }

        # Run via compiled LangGraph if active, or via internal cyclic loop
        final_state = await self._run_cyclic_graph(initial_state)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return self._format_result(final_state, elapsed_ms)

    async def resume_workflow(
        self,
        tenant_id: str,
        thread_id: str,
        decision: HITLApprovalDecision,
    ) -> AgentExecutionResult:
        """Resume an interrupted thread with a human approval or rejection decision."""
        start_time = time.monotonic()
        latest_chk = await self.checkpointer.get_latest_checkpoint(
            tenant_id=tenant_id, thread_id=thread_id
        )
        if not latest_chk:
            raise ValueError(f"No checkpoint found for thread '{thread_id}' in tenant '{tenant_id}'.")

        state: GraphState = dict(latest_chk.state_snapshot)  # type: ignore
        pending = state.get("pending_approval")
        if not pending or state.get("status") != "waiting_approval":
            raise ValueError(f"Thread '{thread_id}' is not in a 'waiting_approval' state.")

        if pending.get("action_id") != decision.action_id:
            raise ValueError(
                f"Action ID mismatch: active '{pending.get('action_id')}' vs submitted '{decision.action_id}'."
            )

        # Process human decision
        if decision.decision == "approve":
            target_args = decision.modified_arguments or pending.get("arguments", {})
            tool_name = pending.get("tool_name", "")
            call_id = f"call_hitl_{uuid4().hex[:6]}"

            # Execute approved tool
            res = await self.tools.execute_tool(
                call_id=call_id,
                tool_name=tool_name,
                arguments=target_args,
            )
            tool_result = res.model_dump()

            # Record step
            steps = state.setdefault("steps", [])
            if steps:
                steps[-1].setdefault("tool_results", []).append(tool_result)

            state["latest_tool_results"] = [tool_result]
            state["pending_approval"] = None
            state["status"] = "running"
            state["step_count"] = state.get("step_count", 0) + 1

        else:  # decision.decision == "reject"
            reject_msg = f"Action '{pending.get('tool_name')}' was REJECTED by human operator. Rationale: {decision.comment or 'Operation declined'}"
            tool_result = {
                "call_id": f"call_rej_{uuid4().hex[:6]}",
                "tool_name": pending.get("tool_name", "unknown"),
                "output": reject_msg,
                "is_error": True,
            }
            steps = state.setdefault("steps", [])
            if steps:
                steps[-1].setdefault("tool_results", []).append(tool_result)

            state["latest_tool_results"] = [tool_result]
            state["pending_approval"] = None
            state["status"] = "running"
            state["step_count"] = state.get("step_count", 0) + 1

        # Save resume checkpoint
        resume_chk_id = f"chk_{thread_id}_step{state['step_count']}_resumed"
        state["active_checkpoint_id"] = resume_chk_id
        await self.checkpointer.save_checkpoint(
            ThreadCheckpoint(
                checkpoint_id=resume_chk_id,
                thread_id=thread_id,
                tenant_id=tenant_id,
                node_name="hitl_resume",
                step_index=state["step_count"],
                state_snapshot=dict(state),
                created_at=time.time(),
            )
        )

        # Continue cyclic graph execution from Reasoner
        resumed_state = await self._run_cyclic_graph(state)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return self._format_result(resumed_state, elapsed_ms)

    # ── Resilient Cyclic Loop Runner ─────────────────────────────────────────

    async def _run_cyclic_graph(self, state: GraphState) -> GraphState:
        """Run the cyclic state machine until a terminal condition or HITL gate is reached."""
        max_steps = state.get("max_steps", 10)

        while state.get("step_count", 0) < max_steps:
            # 1. Reasoner Node
            state = await self._reasoner_node(state)

            # 2. Evaluate next route
            next_route = self._route_after_reasoner(state)

            if next_route == "hitl_gate":
                state = await self._hitl_gate_node(state)
                # Pauses execution; returns state with status='waiting_approval'
                return state

            elif next_route == "tool_executor":
                state = await self._tool_executor_node(state)
                # Cycles back to Reasoner node next iteration

            elif next_route == "synthesizer":
                state = await self._synthesizer_node(state)
                return state

        # If loop exited on step limit:
        if state.get("status") != "waiting_approval":
            state = await self._synthesizer_node(state)

        return state

    def _format_result(
        self, state: GraphState, elapsed_ms: float
    ) -> AgentExecutionResult:
        """Format GraphState into the API AgentExecutionResult response model."""
        raw_steps = state.get("steps", [])
        agent_steps: list[AgentStep] = []

        for s in raw_steps:
            calls = [
                ToolCall(
                    call_id=c.get("call_id", ""),
                    tool_name=c.get("tool_name", ""),
                    arguments=c.get("arguments", {}),
                )
                for c in s.get("tool_calls", [])
            ]
            results = [
                ToolResult(
                    call_id=r.get("call_id", ""),
                    tool_name=r.get("tool_name", ""),
                    output=r.get("output", ""),
                    is_error=r.get("is_error", False),
                )
                for r in s.get("tool_results", [])
            ]
            agent_steps.append(
                AgentStep(
                    step_index=s.get("step_index", 0),
                    thought=s.get("thought", ""),
                    tool_calls=calls,
                    tool_results=results,
                )
            )

        pending_req = None
        if state.get("pending_approval"):
            p = state["pending_approval"]
            pending_req = HITLApprovalRequest(
                action_id=p["action_id"],
                thread_id=p["thread_id"],
                tenant_id=p["tenant_id"],
                tool_name=p["tool_name"],
                arguments=p.get("arguments", {}),
                risk_level=p.get("risk_level", "high"),
                description=p.get("description", ""),
                status=p.get("status", "pending"),
                created_at=p.get("created_at", time.time()),
            )

        return AgentExecutionResult(
            tenant_id=state["tenant_id"],
            thread_id=state["thread_id"],
            prompt=state.get("prompt", ""),
            final_answer=state.get("final_answer", ""),
            status=state.get("status", "completed"),
            steps=agent_steps,
            pending_approval=pending_req,
            checkpoint_id=state.get("active_checkpoint_id"),
            total_steps=len(agent_steps),
            execution_time_ms=round(elapsed_ms, 2),
        )
