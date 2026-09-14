# Universal Model Context Protocol (MCP) Tool Server

**Milestone:** M103 (v0.88.0)  
**System Layer:** Tool Protocols & System Extensibility (Platform Battery #23)  
**Architecture:** JSON-RPC 2.0 Protocol + SSE & Stdio Transports + Dynamic Battery Dispatcher  

---

## 1. Executive Summary

Milestone 103 registers **Platform Battery #23 (`universal_mcp_server`)** under the `SYSTEM_EXTENSIBILITY` category.

The **Model Context Protocol (MCP)**, open-sourced by Anthropic, is the industry standard for exposing backend capabilities and tools to frontier AI models, IDEs (Claude Desktop, Cursor, Zed, Windsurf), and autonomous multi-agent orchestrators.

Milestone 103 transforms Retriever into a Universal MCP Server:
- **Exposes 20+ Platform Batteries as Standardized MCP Tools:** Allows Claude or Cursor to directly invoke hybrid search, ColBERT MaxSim reranking, Python REPL sandboxes, GraphRAG community queries, and PII redaction.
- **Dual Transports:** Supports both **Server-Sent Events (SSE)** over HTTP (`/v1/mcp/sse`) for remote web clients and standard I/O (**Stdio**) for desktop IDE integrations.
- **Strict Tenant RLS Boundary:** Every MCP request payload passes authenticated tenant credentials, preventing cross-tenant information leaks.

---

## 2. Battery Specifications & Parameters

- **Identifier:** `universal_mcp_server`
- **Category:** `SYSTEM_EXTENSIBILITY`
- **Latency Profile:** `<2ms` protocol dispatch overhead
- **Algorithm Foundation:** JSON-RPC 2.0 + Server-Sent Events (SSE) / Stdio Protocol Serialization
- **Health Check Endpoint:** `/v1/mcp`

### Exposed Tools Catalog
| Tool Name | Underlying Battery | Description |
|:---|:---|:---|
| `retriever_search` | BM25 + HNSW + ColBERT | Hybrid reciprocal rank fusion document search with citation metadata. |
| `retriever_graph_query` | Neo4j / PostgreSQL CTE | Multi-hop knowledge graph entity and relationship traversal. |
| `retriever_repl_calc` | RLM Python REPL | Sandboxed Python evaluation for math, metrics, and data aggregation. |
| `retriever_guardrails_check` | NeMo + LlamaGuard 3 | Input safety classification and prompt injection detection. |
| `retriever_compress_context` | LongLLMLingua | Context window token pruning preserving high-entropy reasoning tokens. |

---

## 3. Desktop Client Configuration (Claude Desktop / Cursor)

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "retriever": {
      "command": "python",
      "args": ["-m", "apps.api.src.adapters.mcp.battery_mcp_adapter"],
      "env": {
        "RETRIEVER_API_URL": "https://rag.prateeq.in",
        "RETRIEVER_API_KEY": "ret_live_...",
        "RETRIEVER_TENANT_ID": "00000000-0000-0000-0000-000000000001"
      }
    }
  }
}
```
