# Retriever Developer Console Guide

The **Developer Console** (`apps/developer-console`) is a Next.js 16 application built as an **interactive RAG playground** and **SDK integration blueprint**. Unlike the Admin Dashboard, it runs on tenant-scoped rules (isolated by RLS) to test how Retriever behaves for an individual developer or client application.

---

## 1. Technical Architecture & Connection to Retriever Core
The Developer Console connects to the Retriever Core FastAPI gateway (`localhost:8000`) and operates under standard client permissions.

```
  [Developer Console UI]
         │ (Calls Client APIs using @prat3010/retriever-client-js SDK)
         ▼
  [FastAPI Core Gateway]
         │ (Enforces Postgres RLS using Tenant ID / API Key headers)
         ▼
  [Postgres Client Tables / Vector Chunks / Local Ollama Embeddings]
```

### SDK Integration
*   It serves as a live demo of the `@prat3010/retriever-client-js` TypeScript SDK.
*   Every request (search, upload, chat) is routed through the SDK instance, using the client-provided `tenantId` and `apiKey`.
*   PostgreSQL enforces **Row-Level Security (RLS)** using these credentials. The developer console can **never** see or query files belonging to other client tenants.

---

## 2. Interactive Sections & Settings Directory

The console layout is divided into three responsive columns:

### 📁 1. Left Column: Workspace Navigation Sidebar
*   **Purpose:** Browse documents indexed inside the active tenant's workspace and trigger file synchronization.
*   **Components:**
    *   **Workspace Documents Tree:** Lists all files current registered in the database for the active tenant (fetched via `client.listDocuments()`). Shows file names and status badges (`processed`, `pending`, `failed`).
    *   **🔄 Sync Local Files Button:** Triggers a re-indexing command in development to scan your local folders, segment the files, and update the vectors database.

---

### 💬 2. Center Column: RAG Chat Console
*   **Purpose:** The main interface to test your search accuracy, prompt configurations, and chat streaming.
*   **Components:**
    *   **Chat Output Area:** Renders the conversation flow.
        *   *User Messages:* Renders as standard text.
        *   *Assistant Messages:* Renders markdown, code blocks, and **interactive citation buttons** (e.g. `[1] connection.py`).
    *   **Input Form:** Text input field to query the system with a Send button.
*   **SSE Stream Handling:**
    *   When you click Send, the console initiates a Server-Sent Events (SSE) connection using `client.chatStream()`.
    *   It parses incoming SSE tokens and updates the assistant message in real-time.
*   **Citation Parsing:**
    *   The backend formats references as markdown citation links.
    *   The frontend interceptor parses references like `[1]` and turns them into clickable buttons mapped to the search results.

---

### ⚙️ 3. Right Column: Settings & Validation Panel
*   **Purpose:** Configure connection parameters and validate active LLM provider credentials.
*   **Inputs:**
    *   **FastAPI Base URL:** Endpoint of your core Retriever API (defaults to `http://localhost:8000`).
    *   **Tenant UUID:** The active workspace context (defaults to the system tenant `00000000-0000-0000-0000-000000000000`).
    *   **Admin Master Key:** Authorization key used to fetch document lists from administrative routes.
    *   **Active LLM Model:** Dropdown to select the target model (Gemini vs. OpenAI).
    *   **Provider API Key (Optional):** Input box to test a custom LLM API key. If left blank, it tells the backend to fall back to the server's `.env` key.
*   **Actions:**
    *   **Test Provider Connection Button:** Calls the `/v1/config/validate-key` endpoint to ping the AI provider using the specified key and model.
    *   **Validation Result Box:** Displays a success message (🟢 **Connection Successful**) or a detailed error printout (🔴 **Validation Failed: [Error Message]**).

---

### 📄 4. Popups: Cited Source Modal
*   **Purpose:** Renders the exact text snippet stored in the database when a user clicks a citation tag.
*   **Components:**
    *   **File Name Header:** Displays the file path of the cited file.
    *   **Metadata Details:** Shows the semantic match relevance score and the AST (Abstract Syntax Tree) node type (e.g., class, function, or block).
    *   **Code viewer:** Renders the raw text/code content of the chunk inside a syntax-highlighted code block.

---

## 3. How to Modify and Add Features

### State Management (`page.tsx`)
All states are managed locally inside `apps/developer-console/src/app/page.tsx`:
*   `baseUrl`, `tenantId`, `apiKey` -> Track credentials.
*   `llmApiKey`, `activeModel` -> Track key validation.
*   `messages`, `inputMessage` -> Manage chat flow.
*   `activeCitation` -> Manages the popup modal visibility.

### Styling the Theme
The console's dark-mode glassmorphic theme is defined in two files:
1.  `apps/developer-console/src/app/globals.css` (global typography, scrollbars, keyframe animations).
2.  `apps/developer-console/src/app/components.module.css` (layout grids, container borders, buttons, and input styles).

To change panel sizes, borders, colors, or animations, edit these files.
