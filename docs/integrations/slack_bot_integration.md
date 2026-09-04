# Integration Guide: Slack Workspace Knowledge Bot

**Platform Surface:** Slack Messaging (Channels & Direct Messages)  
**Milestone:** 90 (Phase K)  
**Status:** Production Ready  

---

## 1. Architecture & Message Flow

The Slack Workspace Bot integration enables team members to query tenant knowledge bases directly from Slack using slash commands (e.g. `/ask-retriever <query>`).

```text
[Slack Client User]
       │  Types `/ask-retriever What is our refund policy?`
       ▼
[Slack API Gateway]
       │  POST https://rag.prateeq.in/v1/integrations/slack/slash
       │  Headers: X-Slack-Signature, X-Slack-Request-Timestamp
       ▼
[Retriever API Gateway]
       ├── 1. Cryptographic HMAC-SHA256 Signature Verification
       ├── 2. Map Slack Team/Channel to Tenant UUID
       ├── 3. Hybrid Vector + BM25 Search Lookup
       ├── 4. Grounded Inference Generation with Citations
       └── 5. Build Slack Block Kit Message (Formatted MRKDWN + Sources)
       │
       ▼
[Slack Channel Output] ──► In-channel or Ephemeral cited response
```

---

## 2. Slack App Configuration (Manifest)

Create a new Slack App at [api.slack.com/apps](https://api.slack.com/apps) and paste the following manifest:

```json
{
  "display_information": {
    "name": "Retriever Copilot",
    "description": "Enterprise AI Knowledge Search & Copilot",
    "background_color": "#08080a"
  },
  "features": {
    "slash_commands": [
      {
        "command": "/ask-retriever",
        "url": "https://rag.prateeq.in/v1/integrations/slack/slash",
        "description": "Ask Retriever AI a question grounded in team knowledge",
        "usage_hint": "[your question]",
        "should_escape": false
      }
    ]
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "commands",
        "chat:write"
      ]
    }
  },
  "settings": {
    "event_subscriptions": {
      "request_url": "https://rag.prateeq.in/v1/integrations/slack/events",
      "user_events": []
    }
  }
}
```

---

## 3. Environment Variables Configuration

In `.env` or systemd environment on your server:
```bash
SLACK_SIGNING_SECRET="your_slack_signing_secret_here"
SLACK_DEFAULT_TENANT_ID="prateeq_scoping" # Default tenant mapped to Slack queries
```

---

## 4. Verification & Testing

Test the webhook using curl with a test payload:
```bash
curl -X POST "https://rag.prateeq.in/v1/integrations/slack/slash" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "command=%2Fask-retriever&text=What+is+our+deployment+guide%3F&user_name=dev&channel_id=C123"
```
The endpoint returns a structured Slack Block Kit JSON payload with cited sources and latency metrics.
