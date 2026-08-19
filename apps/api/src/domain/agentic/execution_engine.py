"""Agentic Workflow Execution Engine.

Orchestrates multi-step reasoning, tool call parsing, tool execution,
and final response synthesis in a multi-turn ReAct loop.
"""

import json
import logging
import time
from uuid import uuid4

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.agentic.abstractions import (
    AgentExecutionRequest,
    AgentExecutionResult,
    AgentStep,
    ToolCall,
)
from src.domain.agentic.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

AGENTIC_SYSTEM_PROMPT = """You are an autonomous AI Agent execution engine.
Your goal is to solve the user's task by reasoning step-by-step and invoking available tools when needed.

Available Tools:
{tools_json}

INSTRUCTIONS:
1. Break down the task into logical steps.
2. In each turn, output a JSON object matching this exact structure:
{{
  "thought": "Your step-by-step reasoning or plan",
  "tool_calls": [
    {{
      "tool_name": "name_of_tool",
      "arguments": {{ ... }}
    }}
  ],
  "final_answer": "Your final detailed answer when done, or leave null/empty if tools are still needed."
}}
3. If no more tools are needed, provide your final response in "final_answer".
4. Output strictly valid JSON without markdown wrapping.
"""


class AgenticExecutionEngine:
    """Multi-step ReAct agent execution engine."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        tool_registry: ToolRegistry,
    ) -> None:
        self.llm = llm_provider
        self.tools = tool_registry

    async def execute_workflow(
        self, request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Execute a multi-step agentic workflow loop."""
        start_time = time.monotonic()
        available_tools = self.tools.list_tools(request.allowed_tools)
        tools_schema_str = json.dumps(
            [t.model_dump() for t in available_tools], indent=2
        )

        system_msg = AGENTIC_SYSTEM_PROMPT.format(tools_json=tools_schema_str)
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=request.prompt),
        ]

        steps: list[AgentStep] = []
        final_answer = ""

        for step_idx in range(request.max_steps):
            try:
                response = await self.llm.generate(
                    InferenceRequest(
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1000,
                    )
                )
                raw_text = response.content.strip()

                # Parse JSON output from LLM
                try:
                    # Strip markdown block if present
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.strip("`").removeprefix("json").strip()
                    elif raw_text.startswith("```"):
                        raw_text = raw_text.strip("`").strip()

                    parsed = json.loads(raw_text)
                    thought = parsed.get("thought", raw_text)
                    parsed_calls = parsed.get("tool_calls", [])
                    final_answer = parsed.get("final_answer", "") or ""
                except Exception:
                    thought = raw_text
                    parsed_calls = []
                    final_answer = raw_text

                # Build ToolCall objects
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

                # Execute tool calls
                tool_results = []
                for tc in tool_calls:
                    res = await self.tools.execute_tool(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        arguments=tc.arguments,
                    )
                    tool_results.append(res)

                step_obj = AgentStep(
                    step_index=step_idx,
                    thought=thought,
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                )
                steps.append(step_obj)

                # Check termination conditions
                if final_answer and not tool_calls:
                    break

                if not tool_calls:
                    final_answer = thought
                    break

                # Prepare context for next iteration
                messages.append(ChatMessage(role="assistant", content=raw_text))
                tool_results_summary = json.dumps(
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
                        content=f"Tool Execution Results:\n{tool_results_summary}\n\nContinue or provide final_answer.",
                    )
                )

            except Exception as err:
                logger.error(
                    f"Error in agentic step {step_idx} ({err}). Terminating loop.",
                    exc_info=True,
                )
                final_answer = f"Agent workflow halted due to error: {err!s}"
                break

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return AgentExecutionResult(
            tenant_id=request.tenant_id,
            prompt=request.prompt,
            final_answer=final_answer or "Completed agent execution loop.",
            steps=steps,
            total_steps=len(steps),
            execution_time_ms=round(elapsed_ms, 2),
        )
