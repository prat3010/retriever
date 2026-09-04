# REST API Reference: Ecosystem Integrations & Plugins

**Base Path:** `/v1/integrations`  
**Authentication:** Provider-specific HMAC signatures (Slack), Master Admin Key, or Tenant Bearer Token  
**Milestone:** 90 (Phase K)  
**Version:** `v0.75.0`  

---

## Overview

The Integrations API bridges Retriever's cognitive RAG platform into third-party surfaces, including team messaging platforms (Slack Workspace Bot), client browsers (1-Click Chrome Ingestion Extension), and cloud storage systems (Google Drive, Notion).

---

## Endpoints

### 1. Get Integrations & Plugins Overview

Returns the list of available and configured ecosystem plugins, connection statuses, webhook URLs, and download targets.

- **Method:** `GET`
- **Path:** `/v1/integrations/overview`
- **Headers:** None (Public / Authenticated)
- **Response (`200 OK`):**
  ```json
  {
    "plugins": [
      {
        "id": "slack",
        "name": "Slack Workspace Bot",
        "category": "Messaging",
        "status": "configured",
        "slash_command": "/ask-retriever",
        "webhook_url": "https://rag.prateeq.in/v1/integrations/slack/slash",
        "description": "Ask questions and get cited answers directly inside team Slack channels."
      },
      {
        "id": "chrome_extension",
        "name": "1-Click Chrome Extension",
        "category": "Browser",
        "status": "available",
        "download_url": "/v1/integrations/extension/bundle",
        "description": "One-click ingestion of articles, PDFs, and web pages into your tenant knowledge base."
      },
      {
        "id": "google_drive",
        "name": "Google Drive 2-Way Sync",
        "category": "Cloud Storage",
        "status": "available",
        "description": "Continuous sync of target Google Drive folders with differential vector indexing."
      },
      {
        "id": "notion",
        "name": "Notion Knowledge Base",
        "category": "Documentation",
        "status": "available",
        "description": "Sync Notion databases and page block trees directly into your vector store."
      }
    ]
  }
  ```

---

### 2. Handle Slack Slash Command (`/ask-retriever`)

Processes inbound Slack slash command requests, verifies the Slack HMAC signature, retrieves relevant tenant context chunks via hybrid search, generates a grounded response, and formats a Slack Block Kit response with citations.

- **Method:** `POST`
- **Path:** `/v1/integrations/slack/slash`
- **Headers:**
  - `X-Slack-Signature: v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd27519666489c69b503`
  - `X-Slack-Request-Timestamp: 1725450000`
  - `Content-Type: application/x-www-form-urlencoded`
- **Request Body (Form URL-Encoded):**
  ```text
  command=%2Fask-retriever&text=What+is+our+sprint+deployment+checklist%3F&user_name=prateek&channel_id=C12345&team_id=T12345
  ```
- **Response (`200 OK` — Slack Block Kit JSON):**
  ```json
  {
    "response_type": "in_channel",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Question:* What is our sprint deployment checklist?"
        }
      },
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Answer:*\nThe sprint deployment checklist requires: 1) Passing CI tests, 2) Blue/green database migration, 3) Restarting systemd service, and 4) Telemetry sanity verification."
        }
      },
      {
        "type": "context",
        "elements": [
          {
            "type": "mrkdwn",
            "text": "📚 *Sources:* [RUNBOOK_DEPLOYMENT.md](https://prateeq.in/rag/app?tenant=prateeq_scoping) (Score: 0.94)"
          },
          {
            "type": "mrkdwn",
            "text": "⚡ Latency: 420ms | Retriever AI"
          }
        ]
      }
    ]
  }
  ```

---

### 3. Handle Slack Event Subscriptions & Handshake

Receives Slack webhooks and fulfills the URL verification challenge during Slack app setup.

- **Method:** `POST`
- **Path:** `/v1/integrations/slack/events`
- **Headers:** `Content-Type: application/json`
- **Challenge Request Body:**
  ```json
  {
    "type": "url_verification",
    "token": "Jhj5dZrVaK7ZwHHjRyZWjbDl",
    "challenge": "3eZbrw1aBm2rZgRNFDxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
  }
  ```
- **Challenge Response (`200 OK`):**
  ```json
  {
    "challenge": "3eZbrw1aBm2rZgRNFDxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
  }
  ```

---

### 4. Download 1-Click Chrome Ingestion Extension ZIP Bundle

Dynamically bundles the latest client-side Chrome Extension (Manifest V3) into a compressed ZIP file ready for 1-click download and browser side-loading (`chrome://extensions`).

- **Method:** `GET`
- **Path:** `/v1/integrations/extension/bundle`
- **Headers:** None (Public / Authenticated)
- **Response (`200 OK`):**
  - **Media Type:** `application/zip`
  - **Header:** `Content-Disposition: attachment; filename=retriever-chrome-extension.zip`
  - **Body:** Binary ZIP stream containing `manifest.json`, `background.js`, `popup.html`, `popup.js`, and styling assets.

---

## Security & Signature Verification

### Slack HMAC SHA-256 Verification
Slack requests are cryptographically validated to prevent spoofing:
1. Extract timestamp from `X-Slack-Request-Timestamp` header. Reject requests older than 5 minutes ($|t_{\text{now}} - t_{\text{req}}| > 300\text{s}$).
2. Form base signature string: `v0:<timestamp>:<raw_request_body>`.
3. Compute HMAC SHA-256 hash using `SLACK_SIGNING_SECRET`:
   $$\text{Signature} = \text{"v0="} + \text{HMAC-SHA256}(\text{SLACK\_SIGNING\_SECRET}, \text{base\_string})$$
4. Perform constant-time comparison (`hmac.compare_digest`) against `X-Slack-Signature`. Return `401 Unauthorized` on mismatch.
