"""Tool Registry for managing and invoking agentic tools."""

import ast
import logging
import operator
from collections.abc import Awaitable, Callable
from typing import Any

from src.domain.agentic.abstractions import ToolDefinition, ToolResult

logger = logging.getLogger(__name__)

# Type for tool handler callables (can be sync or async)
ToolHandler = Callable[..., Any | Awaitable[Any]]


class ToolRegistry:
    """Central registry for registering, discovering, and executing agentic tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._register_default_tools()

    def register_tool(
        self,
        definition: ToolDefinition,
        handler: ToolHandler,
    ) -> None:
        """Register a tool definition and its executable handler function."""
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler
        logger.info(f"Registered agent tool: {definition.name}")

    def unregister_tool(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)
        self._handlers.pop(name, None)

    def get_tool_definition(self, name: str) -> ToolDefinition | None:
        """Retrieve tool definition by name."""
        return self._tools.get(name)

    def list_tools(
        self, allowed_tools: list[str] | None = None
    ) -> list[ToolDefinition]:
        """List registered tool definitions, optionally filtered by whitelist."""
        if allowed_tools is None:
            return list(self._tools.values())
        return [
            defn for name, defn in self._tools.items() if name in allowed_tools
        ]

    async def execute_tool(
        self,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """Invoke a tool handler and format the returned result."""
        if tool_name not in self._handlers:
            return ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                output=f"Error: Tool '{tool_name}' is not registered in the tool registry.",
                is_error=True,
            )

        handler = self._handlers[tool_name]
        try:
            import inspect

            if inspect.iscoroutinefunction(handler):
                output = await handler(**arguments)
            else:
                output = handler(**arguments)

            return ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                output=output,
                is_error=False,
            )
        except Exception as err:
            logger.warning(
                f"Error executing tool '{tool_name}' ({err}).", exc_info=True
            )
            return ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                output=f"Error executing {tool_name}: {err!s}",
                is_error=True,
            )

    def _register_default_tools(self) -> None:
        """Register default built-in utility tools."""
        # 1. Calculator Tool
        calc_def = ToolDefinition(
            name="calculator",
            description="Safely evaluate mathematical expressions (e.g. '12000 + 15000 + 8000').",
            parameters_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression string to evaluate",
                    }
                },
                "required": ["expression"],
            },
            category="math",
        )

        def _safe_eval_calculator(expression: str) -> str:
            allowed_operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def _eval_node(node):
                if isinstance(node, ast.Constant) and isinstance(
                    node.value, int | float
                ):
                    return node.value
                if isinstance(node, ast.BinOp):
                    op_type = type(node.op)
                    if op_type in allowed_operators:
                        return allowed_operators[op_type](
                            _eval_node(node.left), _eval_node(node.right)
                        )
                if isinstance(node, ast.UnaryOp):
                    op_type = type(node.op)
                    if op_type in allowed_operators:
                        return allowed_operators[op_type](_eval_node(node.operand))
                raise ValueError(f"Unsupported math operation: {ast.dump(node)}")

            parsed = ast.parse(expression.strip(), mode="eval")
            res = _eval_node(parsed.body)
            return str(res)

        self.register_tool(calc_def, _safe_eval_calculator)
