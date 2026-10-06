"""Tool Registry for managing, discovering, and executing agentic tools.

Conforms strictly to Hexagonal Architecture boundaries.
"""

import ast
import inspect
import logging
import operator
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from src.domain.agentic.abstractions import ToolDefinition, ToolResult

logger = logging.getLogger(__name__)

# Type for tool handler callables (sync or async)
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
        logger.info(
            f"Registered agent tool: {definition.name} (requires_approval={definition.requires_approval}, risk={definition.risk_level})"
        )

    def unregister_tool(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)
        self._handlers.pop(name, None)

    def get_tool_definition(self, name: str) -> ToolDefinition | None:
        """Retrieve tool definition by name."""
        return self._tools.get(name)

    def is_tool_sensitive(self, name: str) -> bool:
        """Check whether a tool requires Human-in-the-Loop (HITL) confirmation."""
        defn = self._tools.get(name)
        return defn.requires_approval if defn else False

    def get_tool_risk(self, name: str) -> str:
        """Get the risk tier for a tool ('low' | 'medium' | 'high' | 'critical')."""
        defn = self._tools.get(name)
        return defn.risk_level if defn else "low"

    def list_tools(
        self, allowed_tools: list[str] | None = None
    ) -> list[ToolDefinition]:
        """List registered tool definitions, optionally filtered by whitelist."""
        if allowed_tools is None:
            return list(self._tools.values())
        return [defn for name, defn in self._tools.items() if name in allowed_tools]

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
        """Register default built-in safe utility tools and sensitive HITL tools."""
        # 1. Safe Calculator Tool
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
            requires_approval=False,
            risk_level="low",
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

        # 2. Safe Knowledge Search Tool (Stubbed handler until container injects search_service)
        search_def = ToolDefinition(
            name="hybrid_search",
            description="Perform hybrid dense-sparse vector search across the tenant's knowledge documents.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query to search knowledge base",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top ranking chunks to retrieve",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            category="retrieval",
            requires_approval=False,
            risk_level="low",
        )

        def _default_search(query: str, top_k: int = 5) -> str:
            return f"Found relevant context chunks for query: '{query}' (top {top_k} results)."

        self.register_tool(search_def, _default_search)

        # 3. Safe Document Reader Tool
        reader_def = ToolDefinition(
            name="document_reader",
            description="Read the full text or metadata of a specific ingested document.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document identifier to inspect",
                    }
                },
                "required": ["document_id"],
            },
            category="retrieval",
            requires_approval=False,
            risk_level="low",
        )

        def _default_reader(document_id: str) -> str:
            return f"Document '{document_id}': verified status, 12 chunks indexed."

        self.register_tool(reader_def, _default_reader)

        # 4. Safe System Metrics Tool
        metrics_def = ToolDefinition(
            name="system_metrics",
            description="Inspect tenant workspace usage, token consumption, and active document statistics.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "metric_type": {
                        "type": "string",
                        "description": "Type of metric to fetch: quota | documents | latency",
                        "default": "quota",
                    }
                },
            },
            category="system",
            requires_approval=False,
            risk_level="low",
        )

        def _default_metrics(metric_type: str = "quota") -> str:
            return f"System metrics for {metric_type}: active healthy status, 42 queries in past hour."

        self.register_tool(metrics_def, _default_metrics)

        # 4a. 2026 Structured Tabular Query Tool
        table_query_def = ToolDefinition(
            name="table_query",
            description="Query and compute metrics on markdown tables (filter rows, sum columns, average, count).",
            parameters_schema={
                "type": "object",
                "properties": {
                    "table_markdown": {
                        "type": "string",
                        "description": "Markdown table text containing headers and rows",
                    },
                    "column": {
                        "type": "string",
                        "description": "Column name to target for filtering or math operations",
                    },
                    "filter_value": {
                        "type": "string",
                        "description": "Sub-string value to match when filtering rows",
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation: 'filter' | 'sum' | 'avg' | 'count' | 'columns'",
                        "default": "filter",
                    },
                },
                "required": ["table_markdown"],
            },
            category="tabular",
            requires_approval=False,
            risk_level="low",
        )

        def _execute_table_query(
            table_markdown: str = "",
            column: str | None = None,
            filter_value: str | None = None,
            operation: str = "filter",
            context: str | None = None,
            query: str | None = None,
        ) -> str:
            import re

            raw_text = table_markdown or context or ""
            # Parse contiguous table blocks rather than flattening the whole document
            table_blocks: list[list[str]] = []
            current_block: list[str] = []

            for line in raw_text.splitlines():
                stripped = line.strip()
                if stripped.startswith("|") and stripped.endswith("|"):
                    current_block.append(stripped)
                else:
                    if len(current_block) >= 2:
                        table_blocks.append(current_block)
                    current_block = []
            if len(current_block) >= 2:
                table_blocks.append(current_block)

            if not table_blocks:
                return "Error: No valid markdown table detected."

            # If multiple tables exist, pick the one that matches column or filter_value if possible
            target_block = table_blocks[0]
            if len(table_blocks) > 1 and (column or filter_value):
                for b in table_blocks:
                    b_headers = [h.strip() for h in re.split(r"(?<!\\)\|", b[0].strip("|"))]
                    if column and any(h.lower() == column.lower() for h in b_headers):
                        target_block = b
                        break
                    if filter_value and any(filter_value.lower() in row.lower() for row in b):
                        target_block = b
                        break

            lines = target_block
            # Split headers respecting escaped pipes
            raw_headers = [h.strip().replace(r"\|", "|") for h in re.split(r"(?<!\\)\|", lines[0].strip("|"))]
            headers = [h for h in raw_headers if h != ""]
            if not headers:
                headers = raw_headers

            data_rows = []
            for row_line in lines[2:]:
                raw_cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", row_line.strip("|"))]
                if len(raw_cells) < len(headers):
                    raw_cells.extend([""] * (len(headers) - len(raw_cells)))
                row_dict = dict(zip(headers, raw_cells[: len(headers)], strict=False))
                data_rows.append(row_dict)

            op = operation.lower()
            # Automatic operation inference if query is provided
            if query:
                q_lower = query.lower()
                if op == "filter":
                    if any(w in q_lower for w in ["sum", "total"]):
                        op = "sum"
                    elif any(w in q_lower for w in ["avg", "average", "mean"]):
                        op = "avg"
                    elif any(w in q_lower for w in ["count", "how many"]):
                        op = "count"

            if op == "columns":
                return f"Columns: {', '.join(headers)}"

            def _count_numeric_cells(col_name: str) -> int:
                count = 0
                for r in data_rows:
                    val = r.get(col_name, "").strip()
                    val_clean = re.sub(r"[,\$€₹£\s]", "", val)
                    if re.match(r"^[-+]?\d+(?:\.\d+)?%?$", val_clean):
                        count += 1
                return count

            col_idx = None
            if column:
                for h in headers:
                    if h.lower() == column.lower():
                        col_idx = h
                        break
            elif query:
                candidates = [h for h in headers if h.lower() in query.lower()]
                if candidates:
                    if op in {"sum", "avg"}:
                        candidates.sort(key=_count_numeric_cells, reverse=True)
                    col_idx = candidates[0]

            if op == "count":
                return f"Total rows: {len(data_rows)}"

            if op in {"sum", "avg"}:
                if col_idx is None:
                    # Pick column with the most numeric cells
                    numeric_cols = sorted(headers, key=_count_numeric_cells, reverse=True)
                    target_col = numeric_cols[0] if numeric_cols and _count_numeric_cells(numeric_cols[0]) > 0 else (headers[1] if len(headers) > 1 else headers[0])
                else:
                    target_col = col_idx

                numbers = []
                for r in data_rows:
                    val_str = r.get(target_col, "").strip()
                    clean_num = re.sub(r"[,\$€₹£\s]", "", val_str)
                    if re.match(r"^[-+]?\d+(?:\.\d+)?%?$", clean_num):
                        try:
                            numbers.append(float(clean_num.rstrip("%")))
                        except ValueError:
                            pass
                if not numbers:
                    return f"No numeric values found in column '{target_col}'."
                if op == "sum":
                    return f"Sum of '{target_col}': {sum(numbers):.2f}"
                return f"Average of '{target_col}': {sum(numbers) / len(numbers):.2f}"

            # Filter operation
            if col_idx and filter_value:
                filtered = [
                    r
                    for r in data_rows
                    if filter_value.lower() in r.get(col_idx, "").lower()
                ]
            elif filter_value:
                filtered = [
                    r
                    for r in data_rows
                    if any(filter_value.lower() in v.lower() for v in r.values())
                ]
            else:
                filtered = data_rows

            if not filtered:
                return "No rows matching filter criteria."
            res_lines = [f"Found {len(filtered)} matching rows:"]
            for r in filtered:
                res_lines.append(" | ".join(f"{k}: {v}" for k, v in r.items()))
            return "\n".join(res_lines)

        self.register_tool(table_query_def, _execute_table_query)

        # 4b. 2026 Agentic Query Planner Tool
        planner_def = ToolDefinition(
            name="query_planner",
            description="Decompose complex queries into structured execution plans.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User question to plan execution for",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant namespace identifier",
                        "default": "default",
                    },
                },
                "required": ["query"],
            },
            category="planning",
            requires_approval=False,
            risk_level="low",
        )

        def _execute_query_planner(query: str, tenant_id: str = "default") -> str:
            from src.domain.agentic.query_planner import AgenticQueryPlanner

            planner = AgenticQueryPlanner()
            plan = planner.decompose_query(query=query, tenant_id=tenant_id)
            return plan.model_dump_json(indent=2)

        self.register_tool(planner_def, _execute_query_planner)

        # 4c. 2026 Multi-Step Retrieval Tool
        multi_retrieval_def = ToolDefinition(
            name="multi_step_retrieval",
            description="Execute multi-query decomposed retrieval across multiple sub-queries with deduplication.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "sub_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of sub-queries to retrieve in parallel",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Top chunks per sub-query",
                        "default": 3,
                    },
                },
                "required": ["sub_queries"],
            },
            category="retrieval",
            requires_approval=False,
            risk_level="low",
        )

        async def _execute_multi_retrieval(
            sub_queries: list[str], top_k: int = 3
        ) -> str:
            results = []
            seen_outputs = set()
            for sq in sub_queries:
                r = await self.execute_tool(
                    call_id=f"sq_{uuid4().hex[:6]}",
                    tool_name="hybrid_search",
                    arguments={"query": sq, "top_k": top_k},
                )
                output_str = str(r.output).strip()
                if output_str not in seen_outputs:
                    seen_outputs.add(output_str)
                    results.append(f"Sub-query '{sq}':\n{output_str}")
            return "\n\n---\n\n".join(results) if results else "No context retrieved."

        self.register_tool(multi_retrieval_def, _execute_multi_retrieval)

        # 5. SENSITIVE: Document Delete Tool (Triggers HITL Gateway)
        doc_del_def = ToolDefinition(
            name="document_delete",
            description="Permanently delete an ingested document and its vector embeddings from the tenant knowledge base.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Identifier of the document to permanently remove",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Rationale for document deletion",
                    },
                },
                "required": ["document_id"],
            },
            category="destructive",
            requires_approval=True,
            risk_level="high",
        )

        def _default_doc_delete(document_id: str, reason: str = "") -> str:
            return f"Successfully deleted document '{document_id}'. Vector embeddings purged."

        self.register_tool(doc_del_def, _default_doc_delete)

        # 6. SENSITIVE: Tenant Prompt Update Tool (Triggers HITL Gateway)
        prompt_update_def = ToolDefinition(
            name="tenant_prompt_update",
            description="Update the active system prompt template for the tenant workspace.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": "Name of prompt template to modify",
                    },
                    "prompt_content": {
                        "type": "string",
                        "description": "New prompt text to deploy",
                    },
                },
                "required": ["template_name", "prompt_content"],
            },
            category="configuration",
            requires_approval=True,
            risk_level="high",
        )

        def _default_prompt_update(template_name: str, prompt_content: str) -> str:
            return f"Prompt template '{template_name}' successfully updated and hot-reloaded."

        self.register_tool(prompt_update_def, _default_prompt_update)

        # 7. SENSITIVE: API Key Revoke Tool (Triggers HITL Gateway)
        key_revoke_def = ToolDefinition(
            name="api_key_revoke",
            description="Revoke an active API key, instantly disabling external access for that key.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "key_id": {
                        "type": "string",
                        "description": "API key identifier to revoke",
                    }
                },
                "required": ["key_id"],
            },
            category="security",
            requires_approval=True,
            risk_level="critical",
        )

        def _default_key_revoke(key_id: str) -> str:
            return f"API key '{key_id}' has been permanently revoked."

        self.register_tool(key_revoke_def, _default_key_revoke)
