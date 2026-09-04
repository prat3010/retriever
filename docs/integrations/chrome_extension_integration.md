# Integration Guide: 1-Click Chrome Ingestion Extension

**Platform Surface:** Google Chrome Browser (Manifest V3)  
**Milestone:** 90 (Phase K)  
**Status:** Production Ready  

---

## 1. Overview & Capabilities

The **Retriever 1-Click Chrome Extension** allows users to ingest any active browser tab (HTML article, research paper, PDF, or documentation page) directly into their tenant's vector database without leaving the page.

### Key Capabilities:
1. **DOM Content Extraction**: Automatically extracts clean readable article text, title, canonical URL, and metadata using an injected content script.
2. **Side-Panel Search & Q&A**: Lets users query their workspace knowledge base directly from the Chrome side panel while browsing.
3. **Multi-Tenant Key Storage**: Securely stores the tenant's API key (`ret_live_...`) and API endpoint in Chrome `chrome.storage.sync`.
4. **1-Click Download**: Bundled dynamically and downloadable directly from `/v1/integrations/extension/bundle` or the Admin Dashboard.

---

## 2. Architecture & File Topology

```text
apps/extension/
├── manifest.json       # Chrome Manifest V3 declaration
├── background.js       # Service worker handling API dispatch & context menus
├── content.js          # Injected content script extracting DOM reader text
├── popup.html          # Extension popup UI (Azure / Noir styling)
├── popup.js            # Popup controller for ingestion & tenant configuration
└── icons/              # Extension brand gremlin icons (16px, 48px, 128px)
```

---

## 3. Installation & Side-Loading Guide

### Step 1: Download Extension Bundle
Download the extension zip file directly via the browser or curl:
```bash
curl -O "https://rag.prateeq.in/v1/integrations/extension/bundle"
unzip retriever-chrome-extension.zip -d retriever-extension
```

### Step 2: Load into Google Chrome
1. Open Google Chrome and navigate to `chrome://extensions`.
2. Enable **Developer mode** toggle in the top-right corner.
3. Click **Load unpacked**.
4. Select the unzipped `retriever-extension` folder.

### Step 3: Configure Tenant Credentials
1. Click the Retriever extension gremlin icon in your browser toolbar.
2. Click **Settings** (gear icon).
3. Paste your **API URL** (`https://rag.prateeq.in`) and **API Key** (`ret_live_...`).
4. Click **Save Connection**.

---

## 4. Ingestion Workflow

1. Navigate to any article or documentation page (e.g. `https://arxiv.org/abs/...` or blog post).
2. Click the Retriever extension icon and click **"Ingest Active Tab"**.
3. The content script extracts page text, dispatches `POST /v1/documents/ingest` with `source: "chrome_extension"`, and confirms index status within 2 seconds.
