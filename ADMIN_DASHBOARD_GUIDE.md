# Retriever Admin Dashboard Guide

The **Admin Dashboard** (`apps/web`) is a Next.js 14 application built to manage the global multi-tenant infrastructure, configuration, and security settings of the Retriever platform. It acts as the "root control panel" and is restricted to the platform owner.

---

## 1. System Architecture & Connection to Retriever Core
The Admin Dashboard connects directly to the Retriever Core FastAPI gateway (`localhost:8000`) over HTTP. 

```
  [Admin Dashboard UI]
         │ (Calls Admin APIs with X-Admin-Master-Key header)
         ▼
  [FastAPI Core Gateway]
         │ (Bypasses Row-Level Security for system management)
         ▼
  [Postgres Metadata / Redis Cache]
```

### Authorization Pattern
*   All requests sent by the dashboard include the header:
    `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
*   This master key instructs the backend API to **bypass PostgreSQL Row-Level Security (RLS)** using `app.bypass_rls = 'true'`. This allows the dashboard to query across all tenant boundaries to compile system-wide statistics and logs.

---

## 2. Route & Section Directory

### 🚪 1. `/login` (Authentication)
*   **Purpose:** Restricts dashboard access to platform administrators.
*   **Settings/Inputs:**
    *   `Admin Master Key` (Password field).
*   **Under the Hood:** Verifies the key against the server's `ADMIN_MASTER_KEY` environment variable. If matched, it saves the session locally to `sessionStorage` and redirects to the dashboard home.

---

### 📊 2. `/` (Dashboard Overview)
*   **Purpose:** Provides a high-level operational overview of system usage and infrastructure health.
*   **KPI Cards:**
    *   **Active Tenants:** Count of total registered customer workspaces.
    *   **Indexed Chunks:** Total segments stored in the `document_chunks` table.
    *   **Total Vectors:** Row count of the `vector_records` table.
    *   **Generated API Keys:** Count of active credentials across the entire platform.
*   **Interactive Components:**
    *   **Platform Status Indicators:** Displays real-time database, Redis, and RabbitMQ health states returned by the backend `/health/readiness` check.

---

### 🚀 3. `/onboard` (3-Step Onboarding Wizard)
*   **Purpose:** A guided wizard to register and configure a new customer workspace from scratch.
*   **Wizard Steps:**
    *   **Step 1: Tenant Profile:**
        *   `Workspace Name` (e.g., `acme-corp`).
        *   `Tier` (Dropdown: standard, premium, enterprise). This determines logical vs physical database isolation.
    *   **Step 2: Cognitive Engine:**
        *   `AI Provider` (Dropdown: Google Gemini, OpenAI, Anthropic).
        *   `Provider API Key` (Optional. Paste the client's key for BYOK billing, or leave blank to use the platform fallback).
    *   **Step 3: Generate Access Credentials:**
        *   Click **Generate Key** to produce the tenant's first live standard client API key.
        *   Displays the resulting `RETRIEVER_TENANT_ID` (UUID) and `RETRIEVER_API_KEY` (`ret_live_...`).

---

### 🏢 4. `/tenants` (Tenant Directory)
*   **Purpose:** Browse and search through all registered customer workspaces.
*   **Features:**
    *   **Search Box:** Filters tenants by business name dynamically.
    *   **Status Badges:** Shows if a tenant is `active`, `suspended`, or `pending`.
    *   **Action Column:** View Details link navigating to `/tenants/[id]`.

---

### 🔍 5. `/tenants/[id]` (Tenant Cockpit & Detail View)
This is the most critical management page. It contains a detailed dashboard segmented into **7 tabs**:

#### Tab 1: Overview
*   **Details:** Displays the tenant UUID, status, created date, tier, and basic metadata.
*   **Actions:**
    *   **Suspend Workspace Button:** Instantly flags the tenant status as `suspended` in the database. This blocks all subsequent API queries under this tenant context.
    *   **Re-activate Button:** Restores status to `active`.

#### Tab 2: Documents
*   **Details:** A paginated grid listing all raw files uploaded by the tenant.
*   **Columns:** Filename, File Size, Ingestion Status (`pending`, `processed`, `failed`), and Upload Date.
*   **Actions:**
    *   **Upload Document File Button:** Trigger file selector to upload new PDFs/Markdown files for vector slicing.
    *   **Delete Icon:** Permanently removes the file from S3/local storage and cascades deletion to drop all related vectors.

#### Tab 3: Users
*   **Details:** Lists user profiles registered under this tenant. Used for user-level RAG filters and citation validation.
*   **Actions:** Add User, Edit Role (admin, developer, client), or Deactivate User.

#### Tab 4: API Keys
*   **Details:** Grid listing all credentials issued to the client application.
*   **Columns:** Key Name, Key Prefix (e.g., `ret_live_abcd`), Key Role (`client` vs `admin`), and Expiration Date.
*   **Actions:**
    *   **Generate API Key Button:** Issues a new token pair for the client application.
    *   **Revoke Key Button:** Permanently deletes the token's cryptographic hash, blocking all client access instantly.

#### Tab 5: Prompts (System Templates)
*   **Details:** Manage system prompts and instruction templates for the RAG chat loop.
*   **Actions:**
    *   **Create Template Button:** Save custom instructions (e.g., *"You are a legal assistant specializing in contract law..."*).
    *   **Edit Prompt Editor:** Modifies template contents.
    *   **Preview Mode:** Test prompt rendering with mockup context variables without making expensive LLM calls.

#### Tab 6: Sandbox (RAG Chat Panel)
*   **Details:** An embedded playground chat window designed for administrative testing.
*   **Actions:** Enter chat queries to test the tenant's current vector indexes and LLM responses.

#### Tab 7: Configuration (Tenant Rules)
*   **Details:** A JSON editor to customize specific tenant behaviors.
*   **Settings Editor:**
    *   `Top K` / `Reranking Threshold`: Tweak semantic retrieval weights.
    *   `Rate Limits`: Set client API rate limits (requests per minute).
    *   `FeatureFlags`: Toggle features like `enable_hybrid_search`, `enable_web_search`, or `allow_platform_key` (managed billing).

---

### 🛠️ 6. `/settings` (Global Configuration Editor)
*   **Purpose:** Modify the default system rules that apply to all standard tenants on the platform.
*   **Sections:**
    *   **AI Settings:** Set default LLM models (e.g., `gemini-1.5-flash`), default temperature, and provider endpoint parameters.
    *   **Embedding Settings:** Configure dimensions (e.g., 768) and standard cloud providers.
    *   **Security & RLS Settings:** Configure default token expiration windows and RLS policies.

---

### 📝 7. `/audit-log` (Platform Security Audit)
*   **Purpose:** Compliance viewer monitoring crucial platform mutations (API key creations, file deletions, config overrides).
*   **Columns:** Timestamp, Tenant ID, User ID, Action Type (e.g., `tenant.suspended`), IP Address, and Change Notes.
*   **Filters:** Filter entries by specific Tenant ID or Action type.

---

## 3. How to Modify and Add Features

### Changing Page UI or Layout
All visual assets and page routes live in:
`apps/web/src/app/(dashboard)/`
*   To add a new route, create a folder under `(dashboard)/` with a `page.tsx` file.
*   The sidebar layout is managed in `apps/web/src/components/sidebar.tsx`. Add new navigation paths there.

### Modifying Backend Admin API Interactions
All API requests are handled by React Query hooks or custom fetch utilities in:
`apps/web/src/components/` (specifically `tenant-config.tsx`, `tenant-api-keys.tsx`, etc.).
If you add an endpoint to `apps/api/src/main.py` under the admin route prefix, add a matching fetch method in the corresponding UI component using the `X-Admin-Master-Key` headers.
