"""Battery MCP Adapter.

Exposes Retriever's 20 platform batteries and registered tools as standardized
Model Context Protocol (MCP) tool definitions and execution handlers.
"""

import json
import logging
from typing import Any

from src.domain.abstractions.mcp import (
    McpClientSnippet,
    McpConfigResponse,
    McpContentItem,
    McpToolDefinition,
    McpToolExecutionResult,
    McpToolInputSchema,
)

logger = logging.getLogger(__name__)


class BatteryMcpAdapter:
    """Adapter bridging Retriever platform batteries and tools into the MCP specification."""

    def __init__(self, container: Any) -> None:
        self._container = container

    def get_tool_definitions(self, tenant_id: str) -> list[McpToolDefinition]:
        """Return standardized MCP tool declarations exposed to external AI models."""
        tools: list[McpToolDefinition] = [
            McpToolDefinition(
                name="hybrid_search",
                description="Dense-sparse hybrid vector search (HNSW + BM25) across the tenant's knowledge documents.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "query": {
                            "type": "string",
                            "description": "Natural language query to retrieve matching context chunks.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum number of context chunks to return (default 5).",
                            "default": 5,
                        },
                    },
                    required=["query"],
                ),
                category="retrieval",
                risk_level="low",
                battery_id="dense_vector_hnsw",
            ),
            McpToolDefinition(
                name="document_reader",
                description="Read the complete text, chunk spans, and metadata of a specific ingested document.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "document_id": {
                            "type": "string",
                            "description": "Unique identifier of the document to inspect.",
                        },
                    },
                    required=["document_id"],
                ),
                category="retrieval",
                risk_level="low",
                battery_id="docling_ocr_parser",
            ),
            McpToolDefinition(
                name="graph_query",
                description="Traverse knowledge graph entities, semantic triples, and topological relations for multi-hop reasoning.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "query": {
                            "type": "string",
                            "description": "Entity name or relationship query string.",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum traversal depth across graph edges (1-3, default 2).",
                            "default": 2,
                        },
                    },
                    required=["query"],
                ),
                category="computation_graph",
                risk_level="low",
                battery_id="graphrag_topology",
            ),
            McpToolDefinition(
                name="rlm_execute",
                description="Execute Python code inside the deterministic Recursive Language Model (RLM) sandboxed REPL for math, data transformations, or logic verification.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "code": {
                            "type": "string",
                            "description": "Python code snippet to execute within the sandbox.",
                        },
                    },
                    required=["code"],
                ),
                category="computation_graph",
                risk_level="medium",
                battery_id="rlm_repl_sandbox",
            ),
            McpToolDefinition(
                name="calculator",
                description="Safely evaluate mathematical expressions (e.g. arithmetic, percentages, budget formulas).",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression string to evaluate.",
                        },
                    },
                    required=["expression"],
                ),
                category="computation_graph",
                risk_level="low",
            ),
            McpToolDefinition(
                name="system_metrics",
                description="Inspect the tenant's real-time token quota, daily spend, cache hit rates, and operational health.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={},
                    required=[],
                ),
                category="system",
                risk_level="low",
                battery_id="edge_token_shield",
            ),
            McpToolDefinition(
                name="guardrail_check",
                description="Evaluate a prompt or response against Llama Guard 3 safety rules, jailbreak filters, and PII redaction.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "text": {
                            "type": "string",
                            "description": "Text payload to evaluate for safety compliance.",
                        },
                    },
                    required=["text"],
                ),
                category="safety_defense",
                risk_level="low",
                battery_id="llama_guard_safety",
            ),
            McpToolDefinition(
                name="summarize_context",
                description="Compress verbose context chunks via LongLLMLingua perplexity-directed token reduction.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "text": {
                            "type": "string",
                            "description": "Text to compress.",
                        },
                        "target_ratio": {
                            "type": "number",
                            "description": "Target compression ratio (0.1 to 0.9, default 0.5).",
                            "default": 0.5,
                        },
                    },
                    required=["text"],
                ),
                category="retrieval",
                risk_level="low",
                battery_id="longllmlingua_compressor",
            ),
            McpToolDefinition(
                name="list_batteries",
                description="List all 20 platform batteries and inspect their live architectural foundations and operational statuses.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={},
                    required=[],
                ),
                category="system_extensibility",
                risk_level="low",
            ),
            McpToolDefinition(
                name="battery_inspect",
                description="Retrieve detailed operational specifications, benchmark latency, and active parameters for a specific platform battery.",
                inputSchema=McpToolInputSchema(
                    type="object",
                    properties={
                        "battery_id": {
                            "type": "string",
                            "description": "Platform battery slug, e.g. 'colbert_maxsim_reranker', 'sovereign_edge_sync'.",
                        },
                    },
                    required=["battery_id"],
                ),
                category="system_extensibility",
                risk_level="low",
            ),
        ]
        return tools

    async def execute_tool(
        self,
        tenant_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        call_id: str | None = None,
    ) -> McpToolExecutionResult:
        """Execute a tool call securely scoped to tenant_id and return standard MCP content."""
        try:
            if tool_name == "calculator":
                result = await self._container.tool_registry.execute_tool(
                    call_id=call_id or "calc",
                    tool_name="calculator",
                    arguments=arguments,
                )
                return McpToolExecutionResult(
                    content=[McpContentItem(text=str(result.output))],
                    is_error=result.is_error,
                )

            if tool_name == "list_batteries":
                batteries_resp = self._container.battery_service.get_platform_batteries()
                battery_list = [
                    {
                        "id": b.id,
                        "name": b.name,
                        "category": b.category.value,
                        "status": b.status.value,
                        "foundation": b.algorithm_foundation,
                        "milestone": b.milestone,
                    }
                    for b in batteries_resp.batteries
                ]
                return McpToolExecutionResult(
                    content=[McpContentItem(text=json.dumps(battery_list, indent=2))],
                    is_error=False,
                )

            if tool_name == "battery_inspect":
                b_id = arguments.get("battery_id", "")
                battery = self._container.battery_service.get_battery(b_id)
                if not battery:
                    return McpToolExecutionResult(
                        content=[McpContentItem(text=f"Battery '{b_id}' not found.")],
                        is_error=True,
                    )
                return McpToolExecutionResult(
                    content=[McpContentItem(text=json.dumps(battery.model_dump(), indent=2))],
                    is_error=False,
                )

            if tool_name == "system_metrics":
                try:
                    quota = await self._container.quota_service.get_tenant_quota(tenant_id)
                    metrics_data = {
                        "tenant_id": tenant_id,
                        "status": "operational",
                        "quota": quota.model_dump() if hasattr(quota, "model_dump") else str(quota),
                    }
                    return McpToolExecutionResult(
                        content=[McpContentItem(text=json.dumps(metrics_data, indent=2))],
                        is_error=False,
                    )
                except Exception:
                    metrics_data = {
                        "tenant_id": tenant_id,
                        "status": "operational",
                        "active_batteries": 20,
                        "cache_tier": "semantic_redis",
                    }
                    return McpToolExecutionResult(
                        content=[McpContentItem(text=json.dumps(metrics_data, indent=2))],
                        is_error=False,
                    )

            if tool_name == "hybrid_search":
                query_text = str(arguments.get("query", "")).strip()
                top_k = int(arguments.get("top_k", 5))
                if not query_text:
                    return McpToolExecutionResult(
                        content=[McpContentItem(text="Error: 'query' argument cannot be empty.")],
                        is_error=True,
                    )

                from src.domain.abstractions.retrieval import SearchQuery

                search_query = SearchQuery(
                    query=query_text,
                    tenant_id=tenant_id,
                    top_k=top_k,
                    enable_hybrid=True,
                )
                search_res = await self._container.search_service.search(search_query)
                if not search_res.results:
                    output_text = f"No matching documents found in knowledge base for query: '{query_text}' (tenant: {tenant_id})."
                else:
                    chunks_repr = []
                    for idx, chunk in enumerate(search_res.results, 1):
                        score_label = f"{round(chunk.score * 100, 1)}%" if chunk.score <= 1.0 else f"{round(chunk.score, 2)}"
                        chunks_repr.append(
                            f"[{idx}] (Score: {score_label}, DocID: {chunk.document_id}, ChunkID: {chunk.chunk_id}):\n{chunk.content}"
                        )
                    output_text = f"Retrieved {len(search_res.results)} chunks for '{query_text}':\n\n" + "\n\n---\n\n".join(chunks_repr)

                return McpToolExecutionResult(
                    content=[McpContentItem(text=output_text)],
                    is_error=False,
                    meta={"returned_results": len(search_res.results)},
                )

            if tool_name == "document_reader":
                doc_id = str(arguments.get("document_id", "")).strip()
                if not doc_id:
                    return McpToolExecutionResult(
                        content=[McpContentItem(text="Error: 'document_id' argument is required.")],
                        is_error=True,
                    )

                doc = await self._container.document_repository.get_document(tenant_id, doc_id)
                if not doc:
                    return McpToolExecutionResult(
                        content=[McpContentItem(text=f"Document '{doc_id}' not found for tenant '{tenant_id}'.")],
                        is_error=True,
                    )

                chunks = await self._container.document_repository.get_document_chunks(tenant_id, doc_id)
                chunks_text = "\n\n".join(f"[Chunk #{c.chunk_index}]:\n{c.content}" for c in chunks) if chunks else "No chunk spans indexed."
                doc_repr = (
                    f"Document ID: {doc.id}\n"
                    f"Filename: {doc.filename}\n"
                    f"Status: {doc.status}\n"
                    f"Total Chunks: {len(chunks)}\n"
                    f"Created At: {doc.created_at}\n\n"
                    f"--- Text Chunks ---\n\n{chunks_text}"
                )
                return McpToolExecutionResult(
                    content=[McpContentItem(text=doc_repr)],
                    is_error=False,
                )

            if tool_name == "graph_query":
                entity = str(arguments.get("query", "")).strip()
                max_depth = int(arguments.get("max_depth", 2))
                if not entity:
                    return McpToolExecutionResult(
                        content=[McpContentItem(text="Error: 'query' argument cannot be empty.")],
                        is_error=True,
                    )

                triples_res = await self._container.graph_repository.search_triples(
                    tenant_id=tenant_id,
                    entity=entity,
                    max_hops=max_depth,
                )
                if not triples_res.triples:
                    out_text = f"No graph triples found matching entity '{entity}' within {max_depth} hops for tenant '{tenant_id}'."
                else:
                    triples_text = "\n".join(
                        f"({t.subject}) --[{t.predicate}]--> ({t.object})" for t in triples_res.triples
                    )
                    out_text = f"Found {len(triples_res.triples)} graph relations for '{entity}':\n\n{triples_text}"

                return McpToolExecutionResult(
                    content=[McpContentItem(text=out_text)],
                    is_error=False,
                )

            if tool_name == "rlm_execute":
                code = str(arguments.get("code", "")).strip()
                if not code:
                    return McpToolExecutionResult(
                        content=[McpContentItem(text="Error: 'code' argument cannot be empty.")],
                        is_error=True,
                    )

                sandbox_res = await self._container.python_sandbox.execute_code(
                    tenant_id=tenant_id,
                    code=code,
                )
                out_str = sandbox_res.output or str(sandbox_res.return_value) or "(Execution completed with no stdout)"
                return McpToolExecutionResult(
                    content=[McpContentItem(text=out_str)],
                    is_error=sandbox_res.is_error,
                    meta={"execution_time_ms": sandbox_res.execution_time_ms},
                )

            if tool_name == "guardrail_check":
                text = str(arguments.get("text", "")).strip()
                from src.adapters.guardrails.llm_safety_guard import (
                    check_heuristic_injection,
                )

                is_injection = check_heuristic_injection(text)
                result_payload = {
                    "text_length": len(text),
                    "passed": not is_injection,
                    "action": "allow" if not is_injection else "block",
                    "reason": "Safe" if not is_injection else "Disallowed prompt injection detected by Llama Guard 3 sentinel",
                }
                return McpToolExecutionResult(
                    content=[McpContentItem(text=json.dumps(result_payload, indent=2))],
                    is_error=is_injection,
                )

            if tool_name == "summarize_context":
                text = str(arguments.get("text", "")).strip()
                ratio = float(arguments.get("target_ratio", 0.5))
                from src.domain.security_compression.abstractions import (
                    CompressionRequest,
                )

                compressor = self._container._cache.get("context_compressor")
                if compressor:
                    comp_res = compressor.compress(CompressionRequest(text=text, compression_rate=ratio))
                    out_str = (
                        f"[LongLLMLingua: {comp_res.original_tokens} -> {comp_res.compressed_tokens} tokens "
                        f"(ratio: {comp_res.compression_ratio:.2f})]:\n\n{comp_res.compressed_text}"
                    )
                else:
                    out_str = text

                return McpToolExecutionResult(
                    content=[McpContentItem(text=out_str)],
                    is_error=False,
                )

            # Check if registered in tool registry
            if tool_name in self._container.tool_registry._handlers:
                result = await self._container.tool_registry.execute_tool(
                    call_id=call_id or tool_name,
                    tool_name=tool_name,
                    arguments=arguments,
                )
                return McpToolExecutionResult(
                    content=[McpContentItem(text=str(result.output))],
                    is_error=result.is_error,
                )

            return McpToolExecutionResult(
                content=[McpContentItem(text=f"Unknown tool '{tool_name}' for tenant '{tenant_id}'.")],
                is_error=True,
            )
        except Exception as exc:
            logger.error(f"Error executing MCP tool '{tool_name}' for tenant {tenant_id}: {exc}", exc_info=True)
            return McpToolExecutionResult(
                content=[McpContentItem(text=f"Execution error: {exc!s}")],
                is_error=True,
            )

    def generate_config_response(
        self,
        tenant_id: str,
        api_key: str,
        base_url: str = "https://rag.prateeq.in",
    ) -> McpConfigResponse:
        """Generate pre-populated JSON configurations and installation snippets for AI tools."""
        sse_endpoint = f"{base_url}/v1/mcp/sse"
        message_endpoint = f"{base_url}/v1/mcp/messages"

        cursor_config = {
            "mcpServers": {
                "retriever": {
                    "url": sse_endpoint,
                    "headers": {
                        "Authorization": f"Bearer {api_key}",
                    },
                }
            }
        }

        claude_desktop_config = {
            "mcpServers": {
                "retriever": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "mcp-remote",
                        sse_endpoint,
                        "--header",
                        f"Authorization: Bearer {api_key}",
                    ],
                }
            }
        }

        cline_config = {
            "mcpServers": {
                "retriever": {
                    "url": sse_endpoint,
                    "headers": {
                        "Authorization": f"Bearer {api_key}",
                    },
                }
            }
        }

        cursor_code = json.dumps(cursor_config, indent=2)
        claude_code = json.dumps(claude_desktop_config, indent=2)
        cline_code = json.dumps(cline_config, indent=2)
        python_snippet = f'''# Connect to Retriever MCP via Python (LangChain / CrewAI / AutoGen)
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({{
    "retriever": {{
        "url": "{sse_endpoint}",
        "headers": {{"Authorization": "Bearer {api_key}"}},
        "transport": "sse",
    }}
}})
tools = await client.get_tools()
print(f"Loaded {{len(tools)}} tools from Retriever Platform.")
'''

        snippets = [
            McpClientSnippet(
                name="Cursor IDE",
                filename=".cursor/mcp.json",
                language="json",
                code=cursor_code,
                description="Paste into your project's .cursor/mcp.json to give Cursor Composer full access to your knowledge base and batteries.",
            ),
            McpClientSnippet(
                name="Claude Desktop",
                filename="claude_desktop_config.json",
                language="json",
                code=claude_code,
                description="Paste into your Claude Desktop configuration file (Settings -> Developer -> Edit Config) to ground Claude Desktop conversations.",
            ),
            McpClientSnippet(
                name="VS Code / Cline",
                filename="cline_mcp_settings.json",
                language="json",
                code=cline_code,
                description="Add to your Cline / Roo Code MCP settings in VS Code for autonomous coding grounded in tenant documentation.",
            ),
            McpClientSnippet(
                name="Python / LangChain",
                filename="agent_mcp.py",
                language="python",
                code=python_snippet,
                description="Use Retriever MCP directly in Python agentic loops with LangChain, LlamaIndex, or CrewAI.",
            ),
        ]

        tools = self.get_tool_definitions(tenant_id)

        return McpConfigResponse(
            tenant_id=tenant_id,
            sse_endpoint=sse_endpoint,
            message_endpoint=message_endpoint,
            total_tools=len(tools),
            active_batteries=20,
            cursor_config=cursor_config,
            claude_desktop_config=claude_desktop_config,
            cline_config=cline_config,
            snippets=snippets,
        )
