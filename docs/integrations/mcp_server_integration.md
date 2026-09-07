# Model Context Protocol (MCP) Server Integration Guide

## Overview

Retriever implements the open **Model Context Protocol (MCP)** specification (2024-11-05 standard) to enable external AI coding agents (Cursor Composer, Claude Desktop, VS Code Cline / Roo Code, and Python agent loops) to natively connect to Retriever as an external knowledge and computation brain.

Through standardized JSON-RPC 2.0 messages over Server-Sent Events (SSE) and HTTP POST, external agents can:
1. Discover all exposed platform tools via `tools/list`.
2. Perform dense-sparse hybrid search (`hybrid_search`) across ingested tenant document chunks.
3. Read raw documents, chunk spans, and metadata (`document_reader`).
4. Traverse Neo4j and PostgreSQL knowledge graph triples (`graph_query`).
5. Execute sandboxed Python code in the Recursive Language Model REPL (`rlm_execute`).
6. Safely evaluate arithmetic and financial formulas (`calculator`).
7. Inspect tenant quotas, token usage, and cache health (`system_metrics`).
8. Run Llama Guard 3 safety validation and prompt guardrails (`guardrail_check`).
9. Compress context windows using LongLLMLingua token reduction (`summarize_context`).
10. Inspect all 20 platform batteries and live benchmarks (`list_batteries`, `battery_inspect`).

---

## Architectural Topology

```
┌─────────────────────────────────────────────────────────────┐
│                       External Agent                        │
│         (Cursor / Claude Desktop / VS Code Cline)           │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │ GET /v1/mcp/sse                     │ POST /v1/mcp/messages
            │ (Persistent EventStream)            │ (JSON-RPC 2.0 Payload)
            ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI MCP Server Router                   │
│                    `src/routers/mcp.py`                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Battery MCP Adapter                      │
│        `src/adapters/mcp/battery_mcp_adapter.py`            │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│ Battery #1   ││ Battery #5   ││ Battery #6   ││ Battery #12  │
│ Dense HNSW   ││ Python REPL  ││ GraphRAG     ││ Llama Guard  │
│ + BM25 Hybrid││ RLM Sandbox  ││ Topology     ││ Safety Rails │
└──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

---

## Endpoints

### 1. `GET /v1/mcp/sse`
Establishes a persistent SSE connection.
- **Headers:** `Authorization: Bearer <token>` (or query parameter `?token=<token>`).
- **Initial Event:** Emits an `endpoint` announcement event pointing to the message POST route:
  ```http
  event: endpoint
  data: /v1/mcp/messages?sessionId=e5b8e97f0a4...
  ```
- **Keepalive:** Pushes keepalive `: ping\r\n\r\n` comments every 15 seconds.

### 2. `POST /v1/mcp/messages`
Receives JSON-RPC 2.0 requests from the client.
- **Parameters:** `?sessionId=<session_id>` (optional, delivers to SSE queue)
- **Supported Methods:**
  - `initialize`: Protocol version handshake (`2024-11-05`), capabilities, server info.
  - `notifications/initialized`: Notification ack (returns HTTP 202).
  - `ping`: Liveness check (returns `{}`).
  - `tools/list`: Lists all available MCP tools and JSON schemas.
  - `tools/call`: Executes tool with given arguments.

### 3. `GET /v1/mcp/config`
Generates pre-populated client snippets for Cursor, Claude Desktop, and Cline with the active tenant ID and API key.

### 4. `GET /v1/mcp/tools`
Direct REST endpoint returning all active MCP tool declarations.

### 5. `POST /v1/mcp/test-tool`
Direct REST testing probe for executing tools without establishing a full SSE connection.

---

## Client Setup

### Cursor IDE (`.cursor/mcp.json`)
Add the following to your project's `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "retriever": {
      "url": "https://rag.prateeq.in/v1/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_RETRIEVER_API_KEY"
      }
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "retriever": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://rag.prateeq.in/v1/mcp/sse",
        "--header",
        "Authorization: Bearer YOUR_RETRIEVER_API_KEY"
      ]
    }
  }
}
```

### VS Code / Cline (`cline_mcp_settings.json`)
```json
{
  "mcpServers": {
    "retriever": {
      "url": "https://rag.prateeq.in/v1/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_RETRIEVER_API_KEY"
      }
    }
  }
}
```

### Python / LangChain
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "retriever": {
        "url": "https://rag.prateeq.in/v1/mcp/sse",
        "headers": {"Authorization": "Bearer YOUR_RETRIEVER_API_KEY"},
        "transport": "sse",
    }
})

tools = await client.get_tools()
print(f"Loaded {len(tools)} tools from Retriever Platform.")
```

---

## Security & Multi-Tenancy Invariants

1. **Strict Multi-Tenancy Isolation:** Tool executions (`tools/call`) derive `tenant_id` exclusively from the authenticated session context. Cross-tenant data leakage is strictly blocked.
2. **Local Model Invariant:** Embedding generation inside retrieval operations uses the local `nomic-embed-text` engine on the VPS, avoiding client rate limits and external egress.
3. **Hexagonal Boundary Protection:** MCP contracts in `src/domain/abstractions/mcp.py` contain zero framework dependencies.
