# @prat3010/retriever-mcp
### Universal Model Context Protocol (MCP) Server for the Retriever Cognitive Engine

This package is the official **Agent-Native Interface** for the Retriever platform. It exposes administrative tenant provisioning, document ingestion, vector searching, and Battery #38 Graph-of-Thought planning directly to AI coding assistants (Antigravity, Claude Desktop, Cursor, Zed) via standard I/O (stdio).

---

## 1. Features & Capabilities

- **Zero-GUI Tenant Provisioning:** AI agents can provision workspaces (`retriever_create_tenant`) and generate scoped client API keys (`retriever_issue_api_key`) instantly.
- **Direct Lore & Document Ingestion:** Push raw markdown, lore codices, and rulebooks directly into the tenant's vector database (`retriever_ingest_text`, `retriever_upload_file`).
- **Cognitive & Reasoning Superpowers:** Perform hybrid dense vector + BM25 searches with cited context chunks (`retriever_hybrid_search`) and execute multi-branch Graph-of-Thought reasoning DAGs (`retriever_got_plan`).
- **Zero-Wipe Invariant (Built-in Security):** Destructive operations (`delete_tenant`, `wipe_vectors`) are **intentionally omitted** from the tool palette. Deletions remain strictly confined to the manual Web Admin Dashboard (`https://admin.rag.prateeq.in`) to prevent prompt-injection exploits or accidental deletions.

---

## 2. Tools Reference Catalog

| Tool Name | Privilege | Description | Inputs |
|:---|:---:|:---|:---|
| `retriever_create_tenant` | **Admin** | Provision a new tenant workspace | `name: string`, `tier?: "standard"\|"premium"\|"enterprise"` |
| `retriever_list_tenants` | **Admin** | List registered tenants, creation dates, and statuses | `limit?: number`, `search?: string` |
| `retriever_inspect_tenant` | **Admin** | View tenant details and tier | `tenant_id: string` |
| `retriever_issue_api_key` | **Admin** | Generate a scoped client API key (`ret_live_...`) | `tenant_id: string`, `name: string`, `role?: "client"\|"admin"` |
| `retriever_ingest_text` | **Tenant / Write** | Ingest raw markdown text into tenant vector database | `tenant_id: string`, `filename: string`, `content: string`, `tags?: string[]` |
| `retriever_upload_file` | **Tenant / Write** | Ingest a local filesystem document (Markdown, PDF, TXT) | `tenant_id: string`, `file_path: string` |
| `retriever_list_documents` | **Tenant / Read** | List indexed documents, chunk counts, and statuses | `tenant_id: string`, `limit?: number` |
| `retriever_hybrid_search` | **Tenant / Read** | Query knowledge via dense vector + BM25 with citations | `tenant_id: string`, `query: string`, `top_k?: number` |
| `retriever_got_plan` | **Tenant / AI** | Execute Battery #38 Graph-of-Thought narrative branching | `tenant_id: string`, `prompt: string`, `branching_factor?: number` |

---

## 3. Configuration & Registration

### A. Registering in Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "retriever": {
      "command": "node",
      "args": ["/Users/prateeksharma/Developer/retriever/packages/retriever-mcp/dist/index.js"],
      "env": {
        "RETRIEVER_API_URL": "https://rag.prateeq.in",
        "RETRIEVER_ADMIN_MASTER_KEY": "your-admin-master-key",
        "RETRIEVER_API_KEY": "ret_live_...",
        "RETRIEVER_TENANT_ID": "your-tenant-uuid"
      }
    }
  }
}
```

### B. Registering in Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "retriever": {
      "command": "node",
      "args": ["/Users/prateeksharma/Developer/retriever/packages/retriever-mcp/dist/index.js"],
      "env": {
        "RETRIEVER_API_URL": "https://rag.prateeq.in",
        "RETRIEVER_ADMIN_MASTER_KEY": "your-admin-master-key"
      }
    }
  }
}
```

### C. Development & Testing
```bash
# Build TypeScript
npm run build

# Run in Stdio mode
node dist/index.js
```
