# Retriever Developer Experience (DX) & Tooling Guide

This guide details the high-leverage developer utilities and tooling built to operate Retriever effortlessly from terminal environments, AI coding assistants, and the web control plane.

---

## 1. Batch Directory Ingestion

Instead of uploading documents one-by-one, Retriever supports batch crawling and indexing of entire local directories (filtering out noise like `.git`, `node_modules`, `.next`, `dist`, and `__pycache__`).

### A. Via AI Coding Agents (MCP Tool)
Any agent connected to `retriever-mcp` (in Cursor, Claude Desktop, Antigravity) can call:

```json
{
  "name": "retriever_ingest_directory",
  "arguments": {
    "tenant_id": "1f85286c-9d9a-4ebc-9c62-a99360a5ece4",
    "directory_path": "./docs",
    "extensions": [".md", ".pdf", ".txt", ".json"],
    "recursive": true,
    "max_files": 100
  }
}
```

### B. Via Terminal CLI Script
Run [`scripts/ingest_directory.py`](file:///Users/prateeksharma/Developer/retriever/scripts/ingest_directory.py):

```bash
# Preview matched files (dry run)
python3 scripts/ingest_directory.py --tenant <tenantId> --dir ./my-docs --dry-run

# Execute live batch upload
python3 scripts/ingest_directory.py --tenant <tenantId> --dir ./my-docs --ext md,pdf,txt
```

---

## 2. Interactive Terminal Chat REPL

Test RAG knowledge retrieval and examine grounded citations directly from your shell without opening a browser.

```bash
python3 scripts/chat_repl.py
```

### Key Features:
- **Interactive Tenant Discovery:** Automatically senses registered tenants from `.env` or lists them for 1-key selection.
- **Ephemeral Session Auth:** Automatically provisions an active session API key from `ADMIN_MASTER_KEY` so developers never have to copy-paste tokens.
- **Citation Inspection:** Renders grounded source passages, filenames, and hybrid MaxSim similarity scores.
- **Built-in REPL Commands:**
  - `/docs` — List all indexed documents in the active tenant
  - `/tenant` — Switch connected tenant UUID on the fly
  - `/clear` — Clear terminal buffer
  - `/help` — View available commands
  - `/exit` — Quit REPL

---

## 3. Multi-Language Code Generator (Web Studio)

On the **Client Onboarded** screen (`/onboard`) and Tenant Details in the Next.js Web Studio (`apps/web`), developers can instantly switch between 4 copy-paste integration tabs:

1. **TypeScript / Next.js:** Pre-configured `@prat3010/retriever-client` instantiation and query execution.
2. **Python:** Zero-dependency `requests` snippet with authentication headers.
3. **1-Line HTML Widget:** Drop-in `<script src=".../widget.js">` tag to embed the floating chatbox on any website.
4. **cURL:** Direct terminal shell commands for document upload and hybrid search.

---

## 4. MCP System Health & Diagnostics

AI coding agents can autonomously introspect engine availability and diagnose issues using:

```json
{
  "name": "retriever_system_health",
  "arguments": {}
}
```

Returns structured status:
- Gateway readiness (`/health/readiness`)
- Worker liveness (`/health/liveness`)
- Platform host URL and timestamp
