# Operational Runbook: Universal Ecosystem Plugins & Integrations

**Document Status:** Production-Ready  
**Milestone:** 90 (v0.75.0)  
**Target Audience:** Workspace Administrators, Integrations Engineers, SREs & Enterprise End-Users  

---

## 1. Executive Summary & Ecosystem Topology

Enterprises rarely work within standalone SaaS web portals. To achieve daily operational ubiquity, **Milestone 90** embeds Retriever directly into existing corporate collaboration tools:

```text
                               [Retriever Core API]
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             │                          │                          │
             ▼                          ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
    │ Native Slack    │        │ 1-Click Chrome  │        │ 2-Way Cloud     │
    │ Workspace Bot   │        │ Ingestion Ext   │        │ Sync Connectors │
    │ (/ask-retriever)│        │  (Manifest V3)  │        │  (GDrive/Notion)│
    └────────┬────────┘        └────────┬────────┘        └────────┬────────┘
             │                          │                          │
      Direct Slack               Active Browser              Continuous
       Block Kit                  Reader-Mode                Differential
       Q&A in Teams               DOM Extraction             Vector Sync
```

---

## 2. Native Slack Workspace Bot

### A. Core Architecture
- **Request Endpoint:** `POST /v1/integrations/slack/slash`
- **Verification Standard:** HMAC-SHA256 request signature verification using `SLACK_SIGNING_SECRET`.
- **Response Standard:** Slack Block Kit UI components with grounded citations and interactive action buttons.

### B. Cryptographic Signature Verification
Slack signs every request with a custom header `X-Slack-Signature`:
$$\text{Signature} = \text{v0}=\text{HMAC-SHA256}\Big(\text{SLACK\_SIGNING\_SECRET},\; \text{"v0:"} \mathbin{\Vert} \text{timestamp} \mathbin{\Vert} \text{raw\_body}\Big)$$

The domain verification in `apps/api/src/domain/integrations/slack_service.py`:
1. Rejects timestamps older than 300 seconds to protect against replay attacks.
2. Generates the base string and compares digests using constant-time `hmac.compare_digest`.

### C. Configuring in Slack API Console
1. Navigate to **[api.slack.com/apps](https://api.slack.com/apps)** $\rightarrow$ **Create New App** $\rightarrow$ **From scratch**.
2. Under **Slash Commands**, click **Create New Command**:
   - **Command:** `/ask-retriever`
   - **Request URL:** `https://rag.prateeq.in/v1/integrations/slack/slash`
   - **Short Description:** `Ask Retriever AI enterprise knowledge assistant`
   - **Usage Hint:** `[your question]`
3. Under **Basic Information** $\rightarrow$ **App Credentials**, copy your **Signing Secret** and set:
   ```bash
   SLACK_SIGNING_SECRET="your-slack-signing-secret"
   SLACK_DEFAULT_TENANT_ID="your-tenant-uuid"
   ```
4. Install app to your workspace.

### D. Interactive Block Kit Format
When a team member enters `/ask-retriever What is our refund policy?`, Retriever responds with:
- **Query & Answer Section:** Clean markdown synthesis.
- **Source Citation Pills:** Clickable links to documents consulted (e.g. `<url|*Refund_SOP_v2.pdf*>`).
- **Interactive Action Buttons:**
  - `👍 Helpful` (emits positive telemetry).
  - `👎 Inaccurate` (flags hallucination for online evaluation).
  - `📄 Open in Studio` (deep links into SaaS Studio).

---

## 3. 1-Click Chrome Ingestion Extension (Manifest V3)

### A. Location & Architecture
- **Extension Source:** `retriever/apps/extension/`
- **Manifest Version:** Manifest V3 (`permissions: ["activeTab", "scripting", "storage"]`)
- **Direct Zip Download:** `GET /v1/integrations/extension/bundle`

### B. DOM Extraction Logic
When the user clicks **"⚡ Ingest Active Page"** in the popup:
1. `popup.js` injects a lightweight content script into the active browser tab.
2. If the user has highlighted text, it extracts the selection.
3. Otherwise, it clones the DOM, strips irrelevant chrome (`<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`), and extracts reader-mode plain text.
4. Posts authenticated payload to `POST /v1/tenants/{tenantId}/documents/raw`.
5. Retriever runs synchronous tokenization and HNSW vector indexing, returning chunk count and confirmation toast within <1 second.

### C. 3-Step Installation Guide (Developer Mode)
1. Download `retriever-chrome-extension.zip` from the Admin Dashboard or SaaS Studio (`/rag/app` Integrations tab).
2. Unzip to a local folder.
3. In Chrome/Brave/Edge, navigate to `chrome://extensions`, enable **Developer mode** (top-right), and click **Load unpacked**.
4. Click the extension puzzle icon, enter your Tenant ID and API Key, and start clipping knowledge with 1 click.

---

## 4. 2-Way Google Drive Sync Connector

### A. Implementation (`apps/api/src/domain/connectors/google_drive.py`)
- Interfaces with **Google Drive v3 REST API**.
- Authenticates using Bearer token (`access_token` or service account key).
- Lists files matching query: `'folder_id' in parents and trashed = false`.
- **Automatic Google Docs Conversion:** Calls `https://www.googleapis.com/drive/v3/files/{id}/export?mimeType=text/plain` to convert live Google Docs into clean plain text.
- Downloads PDF, Markdown, and CSV binaries directly.
- **Differential Sync:** Tracks `modifiedTime` and `md5Checksum` to prevent re-indexing unmodified documents.

### B. Triggering Sync via API
```bash
curl -X POST "https://rag.prateeq.in/v1/admin/tenants/{tenantId}/connectors/{connectorId}/sync" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```

---

## 5. Notion Knowledge Base Connector

### A. Implementation (`apps/api/src/domain/connectors/notion.py`)
- Interfaces with **Notion API v1** (`https://api.notion.com/v1`).
- Authenticates using Notion Internal Integration Token (`Bearer secret_...`).
- Queries pages within database: `POST /v1/databases/{database_id}/query`.
- **Recursive Block-to-Markdown Traversal:**
  - Iterates `/v1/blocks/{page_id}/children`.
  - Converts rich blocks (`heading_1`, `heading_2`, `heading_3`, `paragraph`, `bulleted_list_item`, `numbered_list_item`, `quote`, `callout`, `code`) into standard GitHub Flavored Markdown.
- **Differential Sync:** Compares `last_edited_time` against previous sync manifest.

---

## 6. Raw Document Ingestion API

For third-party automations (Zapier, n8n, custom webhooks, or browser extensions):

```bash
curl -X POST "https://rag.prateeq.in/v1/tenants/{tenantId}/documents/raw" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Competitive Architecture Benchmark 2026",
    "content": "# Benchmark Results\n\nRetriever achieved sub-30ms global vector latency across multi-region read replicas...",
    "source_url": "https://techblog.internal/post/492",
    "mime_type": "text/markdown",
    "tags": ["benchmark", "chrome_extension"]
  }'
```

**Response (HTTP 201 Created):**
```json
{
  "document_id": "doc_9f48a120c482",
  "filename": "Competitive_Architecture_Benchmark_2026.md",
  "chunk_count": 8,
  "status": "PROCESSED",
  "message": "Successfully ingested and indexed 8 vector chunks."
}
```
