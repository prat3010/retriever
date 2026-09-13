"""Autonomous Multi-Turn ReAct Tool Loop & Self-Healing Execution Engine (M104).

Conforms strictly to Hexagonal Architecture boundaries (0 framework imports).
Implements:
- Cyclic ReAct state machine (Reasoning -> Tool Selection -> Tool Execution -> Observation -> Evaluation)
- Anti-loop signature hashing circuit breaker detecting and terminating repetitive ping-pong tool calls
- Autonomous self-healing error recovery injecting targeted diagnostic prompts to guide LLMs to self-correct
- Turn limit and wall-clock execution timeout guards
- Asynchronous generator emitting granular real-time ReAct event frames for SSE streaming
"""

import hashlib
import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from src.domain.abstractions.economic_orchestrator import (
    EconomicOrchestratorProtocol,
    ModelTier,
)
from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.abstractions.react import (
    ReActEvent,
    ReActEventType,
    ReActExecutionTrace,
    ReActLoopConfig,
    ReActLoopProtocol,
    ReActState,
)
from src.domain.agentic.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

REACT_SYSTEM_PROMPT = """You are an autonomous AI Agent operating inside the Retriever cognitive platform.
Your goal is to solve the user's task using iterative multi-turn reasoning and available tools.

Available Tools:
{tools_schema}

OPERATIONAL PROTOCOL:
1. Carefully analyze the user prompt and decompose it into logical execution steps.
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
3. When you have gathered sufficient observations to completely answer the user request, provide "final_answer" and leave "tool_calls" empty.
4. If a tool invocation returns an error or empty result, analyze why it failed and self-correct your parameters or try an alternative tool.
5. Output ONLY raw valid JSON without markdown code fences or conversational commentary outside the JSON structure.
"""


def _tool_call_signature(tool_name: str, arguments: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 fingerprint of tool call and its arguments."""
    try:
        sorted_args = json.dumps(arguments, sort_keys=True, default=str)
    except Exception:
        sorted_args = str(sorted(arguments.items()))
    payload = f"{tool_name}:{sorted_args}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ReActExecutionEngine(ReActLoopProtocol):
    """Domain engine executing multi-turn cyclic ReAct reasoning loops."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        tool_registry: ToolRegistry | None = None,
        orchestrator: EconomicOrchestratorProtocol | None = None,
    ) -> None:
        self.llm = llm_provider
        self.tools = tool_registry or ToolRegistry()
        self.orchestrator = orchestrator

    async def run_loop_stream(
        self,
        tenant_id: str,
        query: str,
        config: ReActLoopConfig | None = None,
        thread_id: str | None = None,
    ) -> AsyncGenerator[ReActEvent, None]:
        """Execute cyclic ReAct loop yielding streaming real-time event frames."""
        cfg = config or ReActLoopConfig()
        t_id = thread_id or f"react_{uuid4().hex[:12]}"
        start_time = time.monotonic()

        # Retrieve available tools
        available_tools = self.tools.list_tools(cfg.allowed_tools)
        tools_schema_str = json.dumps([t.model_dump() for t in available_tools], indent=2)
        system_msg = REACT_SYSTEM_PROMPT.format(tools_schema=tools_schema_str)

        messages = [
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=f"Tenant Workspace: {tenant_id}\n\nTask: {query}"),
        ]

        # Anti-loop signature tracker: signature -> count
        call_signatures: dict[str, int] = {}
        circuit_breaker_active = False
        final_answer: str | None = None

        # Economic Multi-Model Tracking (M105)
        current_tier = ModelTier.MID_TIER
        escalated = False
        escalation_reason = None
        mid_tier_tokens = 0
        frontier_tokens = 0
        last_step_had_error = False
        last_step_self_healing = False

        if self.orchestrator:
            complexity = self.orchestrator.classify_complexity(query, cfg.allowed_tools)
            current_tier = complexity.tier_assigned

        for step_idx in range(cfg.max_turns):
            # Check execution timeout
            elapsed_sec = time.monotonic() - start_time
            if elapsed_sec > cfg.timeout_seconds:
                logger.warning(
                    f"[ReActEngine] Thread {t_id} timed out after {elapsed_sec:.2f}s (limit: {cfg.timeout_seconds}s)"
                )
                yield ReActEvent(
                    event_id=f"ev_{uuid4().hex[:8]}",
                    event_type=ReActEventType.ERROR,
                    step_index=step_idx,
                    state=ReActState.ERROR,
                    data={"error": f"Execution timed out after {elapsed_sec:.1f}s. Formulating partial response."},
                )
                break

            # Mid-Flight Escalation Check (M105)
            if self.orchestrator and current_tier == ModelTier.MID_TIER:
                should_esc, esc_reason, esc_details = self.orchestrator.should_escalate(
                    current_tier=current_tier,
                    step_index=step_idx,
                    last_tool_error=last_step_had_error,
                    self_healing_attempted=last_step_self_healing,
                    circuit_breaker_tripped=circuit_breaker_active,
                )
                if should_esc and esc_reason:
                    current_tier = ModelTier.FRONTIER
                    escalated = True
                    escalation_reason = esc_reason
                    from_mod = getattr(self.orchestrator, "get_model_for_tier", lambda t: "gemini-2.5-flash")(ModelTier.MID_TIER)
                    to_mod = getattr(self.orchestrator, "get_model_for_tier", lambda t: "claude-3-5-sonnet")(ModelTier.FRONTIER)
                    yield ReActEvent(
                        event_id=f"ev_{uuid4().hex[:8]}",
                        event_type=ReActEventType.MODEL_ESCALATION,
                        step_index=step_idx,
                        state=ReActState.REASONING,
                        data={
                            "from_model": from_mod,
                            "to_model": to_mod,
                            "reason": esc_reason.value if hasattr(esc_reason, "value") else str(esc_reason),
                            "details": esc_details,
                        },
                    )
                    messages.append(
                        ChatMessage(
                            role="system",
                            content=f"⚡ Model Escalated to Frontier Reasoning ({to_mod}): {esc_details}",
                        )
                    )

            # 1. State: REASONING
            yield ReActEvent(
                event_id=f"ev_{uuid4().hex[:8]}",
                event_type=ReActEventType.THOUGHT,
                step_index=step_idx,
                state=ReActState.REASONING,
                data={
                    "status": "reasoning",
                    "step": step_idx + 1,
                    "max_turns": cfg.max_turns,
                    "tier": current_tier.value,
                },
            )

            try:
                inference_resp = await self.llm.generate(
                    InferenceRequest(
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1500,
                    )
                )
                raw_text = inference_resp.content.strip()
                toks = (
                    inference_resp.usage.total_tokens
                    if getattr(inference_resp, "usage", None) and inference_resp.usage.total_tokens
                    else (len(raw_text.split()) * 2 + 50)
                )
                if current_tier == ModelTier.MID_TIER:
                    mid_tier_tokens += toks
                else:
                    frontier_tokens += toks
            except Exception as llm_err:
                logger.error(f"[ReActEngine] LLM generation failure: {llm_err}", exc_info=True)
                yield ReActEvent(
                    event_id=f"ev_{uuid4().hex[:8]}",
                    event_type=ReActEventType.ERROR,
                    step_index=step_idx,
                    state=ReActState.ERROR,
                    data={"error": f"LLM inference error: {llm_err!s}"},
                )
                final_answer = f"Agent encountered an inference error: {llm_err!s}"
                break

            # Parse JSON output
            cleaned = raw_text
            if cleaned.startswith("```json"):
                cleaned = cleaned.strip("`").removeprefix("json").strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned.strip("`").strip()

            try:
                parsed = json.loads(cleaned)
                thought = parsed.get("thought", raw_text)
                tool_calls_raw = parsed.get("tool_calls", [])
                candidate_final = parsed.get("final_answer")
            except Exception:
                thought = raw_text
                tool_calls_raw = []
                candidate_final = raw_text

            # Emit extracted Thought
            yield ReActEvent(
                event_id=f"ev_{uuid4().hex[:8]}",
                event_type=ReActEventType.THOUGHT,
                step_index=step_idx,
                state=ReActState.REASONING,
                data={"thought": thought},
            )

            # If final answer provided and no more tools needed, complete
            if candidate_final and not tool_calls_raw:
                final_answer = candidate_final
                break

            if not tool_calls_raw:
                final_answer = candidate_final or thought
                break

            # 2. State: SELECTING_TOOL & Anti-Loop Circuit Breaker Check
            valid_calls = []
            for call_obj in tool_calls_raw:
                t_name = str(call_obj.get("tool_name", "")).strip()
                t_args = call_obj.get("arguments", {})
                if not t_name:
                    continue

                sig = _tool_call_signature(t_name, t_args)
                sig_count = call_signatures.get(sig, 0) + 1
                call_signatures[sig] = sig_count

                if sig_count >= cfg.anti_loop_threshold:
                    circuit_breaker_active = True
                    logger.warning(
                        f"[ReActEngine] Circuit breaker tripped for tool '{t_name}' (repeated {sig_count} times)"
                    )
                    yield ReActEvent(
                        event_id=f"ev_{uuid4().hex[:8]}",
                        event_type=ReActEventType.CIRCUIT_BREAKER,
                        step_index=step_idx,
                        state=ReActState.EVALUATING_COMPLETION,
                        data={
                            "tool_name": t_name,
                            "repeated_count": sig_count,
                            "warning": f"Tool '{t_name}' invoked {sig_count} times with identical arguments without progress.",
                        },
                    )
                    messages.append(
                        ChatMessage(
                            role="user",
                            content=(
                                f"🚨 ANTI-LOOP CIRCUIT BREAKER TRIGGERED:\n"
                                f"Tool '{t_name}' was invoked with identical parameters {sig_count} times without progress.\n"
                                f"Repeated calls are blocked. Conclude immediately or adopt an entirely different strategy."
                            ),
                        )
                    )
                    continue

                valid_calls.append((t_name, t_args))

            if not valid_calls:
                if circuit_breaker_active:
                    final_answer = candidate_final or thought
                    break
                continue

            # 3. State: EXECUTING_BATTERY & Tool Observations
            observations = []
            for t_name, t_args in valid_calls:
                call_id = f"call_{uuid4().hex[:8]}"

                yield ReActEvent(
                    event_id=f"ev_{uuid4().hex[:8]}",
                    event_type=ReActEventType.TOOL_START,
                    step_index=step_idx,
                    state=ReActState.EXECUTING_BATTERY,
                    data={"call_id": call_id, "tool_name": t_name, "arguments": t_args},
                )

                t_start = time.monotonic()
                try:
                    tool_res = await self.tools.execute_tool(
                        call_id=call_id,
                        tool_name=t_name,
                        arguments=t_args,
                    )
                    t_latency = round((time.monotonic() - t_start) * 1000, 2)
                    output_data = tool_res.output
                    is_err = tool_res.is_error
                except Exception as exec_err:
                    t_latency = round((time.monotonic() - t_start) * 1000, 2)
                    output_data = f"Exception: {exec_err!s}"
                    is_err = True

                last_step_had_error = is_err
                last_step_self_healing = is_err and cfg.self_healing_enabled

                yield ReActEvent(
                    event_id=f"ev_{uuid4().hex[:8]}",
                    event_type=ReActEventType.TOOL_DONE,
                    step_index=step_idx,
                    state=ReActState.OBSERVING_RESULT,
                    data={
                        "call_id": call_id,
                        "tool_name": t_name,
                        "output": str(output_data)[:2000],
                        "is_error": is_err,
                        "latency_ms": t_latency,
                    },
                )

                # 4. State: SELF_HEALING on failure
                if is_err and cfg.self_healing_enabled:
                    yield ReActEvent(
                        event_id=f"ev_{uuid4().hex[:8]}",
                        event_type=ReActEventType.SELF_HEALING,
                        step_index=step_idx,
                        state=ReActState.SELF_HEALING,
                        data={
                            "tool_name": t_name,
                            "error": str(output_data)[:500],
                            "recovery_action": "Injecting self-healing diagnostic prompt to guide model correction.",
                        },
                    )
                    observations.append(
                        {
                            "tool_name": t_name,
                            "status": "error",
                            "error": str(output_data),
                            "self_healing_hint": f"Analyze why '{t_name}' failed and adjust arguments or try an alternative tool.",
                        }
                    )
                else:
                    observations.append(
                        {
                            "tool_name": t_name,
                            "status": "success",
                            "output": output_data,
                        }
                    )

            # Append assistant step and tool observations to conversation
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=json.dumps({"thought": thought, "tool_calls": tool_calls_raw}),
                )
            )
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"Tool Observations:\n{json.dumps(observations, indent=2, default=str)}\n\nContinue reasoning or provide final_answer.",
                )
            )

        # Fallback if loop ended without explicit final_answer
        if not final_answer:
            final_answer = (
                candidate_final
                or thought
                or "Completed autonomous ReAct execution within configured turn constraints."
            )

        total_duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        # Record economic transaction (M105)
        if self.orchestrator:
            from_mod = getattr(self.orchestrator, "get_model_for_tier", lambda t: "gemini-2.5-flash")(ModelTier.MID_TIER)
            to_mod = getattr(self.orchestrator, "get_model_for_tier", lambda t: "claude-3-5-sonnet")(ModelTier.FRONTIER)
            self.orchestrator.record_transaction(
                tenant_id=tenant_id,
                thread_id=t_id,
                query=query,
                mid_tier_tokens=mid_tier_tokens,
                frontier_tokens=frontier_tokens,
                mid_tier_model=from_mod,
                frontier_model=to_mod,
                escalated=escalated,
                escalation_reason=escalation_reason,
            )

        yield ReActEvent(
            event_id=f"ev_{uuid4().hex[:8]}",
            event_type=ReActEventType.FINAL_ANSWER,
            step_index=step_idx,
            state=ReActState.COMPLETED,
            data={
                "thread_id": t_id,
                "final_answer": final_answer,
                "total_steps": step_idx + 1,
                "circuit_breaker_triggered": circuit_breaker_active,
                "execution_time_ms": total_duration_ms,
                "escalated": escalated,
            },
        )

    async def run_loop(
        self,
        tenant_id: str,
        query: str,
        config: ReActLoopConfig | None = None,
        thread_id: str | None = None,
    ) -> ReActExecutionTrace:
        """Execute cyclic ReAct loop and return full compiled execution trace."""
        t_id = thread_id or f"react_{uuid4().hex[:12]}"
        events: list[ReActEvent] = []
        final_ans = ""
        circuit_breaker = False
        self_healing_count = 0
        total_time_ms = 0.0

        async for ev in self.run_loop_stream(tenant_id, query, config=config, thread_id=t_id):
            events.append(ev)
            if ev.event_type == ReActEventType.SELF_HEALING:
                self_healing_count += 1
            elif ev.event_type == ReActEventType.CIRCUIT_BREAKER:
                circuit_breaker = True
            elif ev.event_type == ReActEventType.FINAL_ANSWER:
                final_ans = ev.data.get("final_answer", "")
                total_time_ms = ev.data.get("execution_time_ms", 0.0)

        return ReActExecutionTrace(
            thread_id=t_id,
            tenant_id=tenant_id,
            query=query,
            final_answer=final_ans,
            total_steps=len(events),
            self_healing_interventions=self_healing_count,
            circuit_breaker_triggered=circuit_breaker,
            execution_time_ms=total_time_ms,
            events=events,
        )
