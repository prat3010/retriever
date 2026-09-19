# 🚀 Production Deployment & Frontend Integration Guide

This guide walks you through deploying **Retriever** to a live cloud server and connecting it to your frontend applications (Next.js, React, mobile apps, or static websites).

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Deploying Retriever Online](#2-deploying-retriever-online)
   - [Option A: Any Cloud VPS / VM (Docker Compose) — Recommended](#option-a-any-cloud-vps--vm-docker-compose--recommended)
   - [Option B: Container PaaS (Fly.io / Render / Railway)](#option-b-container-paas-flyio--render--railway)
   - [Option C: Kubernetes (Helm 3 Chart)](#option-c-kubernetes-helm-3-chart)
3. [Domain, SSL & CORS Configuration](#3-domain-ssl--cors-configuration)
4. [Connecting to an External Frontend](#4-connecting-to-an-external-frontend)
   - [Method 1: 1-Line Embeddable Chat Widget (Zero Code)](#method-1-1-line-embeddable-chat-widget-zero-code)
   - [Method 2: Next.js / React (Secure BFF Pattern)](#method-2-nextjs--react-secure-bff-pattern)
   - [Method 3: Official TypeScript / JavaScript SDK](#method-3-official-typescript--javascript-sdk)
   - [Method 4: Direct Streaming REST API (cURL / Fetch)](#method-4-direct-streaming-rest-api-curl--fetch)
   - [Method 5: Connect AI Assistants via MCP](#method-5-connect-ai-assistants-via-mcp)
5. [Production Checklist](#5-production-checklist)

---

## 1. Architecture Overview

Retriever is designed as a headless, multi-tenant cognitive engine. In production, your frontend and AI clients communicate with Retriever over HTTPS:

```text
┌────────────────────────────────────────────────────────┐
│                   FRONTEND SURFACES                    │
│  • Marketing / Docs: 1-Line Widget (<script>)          │
│  • Next.js / React: BFF API Route or TypeScript SDK    │
│  • AI Agents: Cursor / Windsurf via Remote MCP         │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / SSE
                            ▼
┌────────────────────────────────────────────────────────┐
│               REVERSE PROXY / DOMAIN                   │
│      Nginx / Caddy / Cloudflare (SSL Termination)       │
│               https://api.yourdomain.com               │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                RETRIEVER ENGINE (FastAPI)              │
│  • Strict Row-Level Security (Multi-Tenant Isolation)  │
│  • Hybrid Fusion Search (HNSW Dense + BM25 Sparse)     │
│  • Token-Level MaxSim Reranker (ColBERT)               │
│  • Universal MCP Gateway (/v1/mcp/sse)                 │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
     ┌────────────────────┐    ┌────────────────────┐
     │   PostgreSQL 16    │    │    Local Ollama    │
     │     + pgvector     │    │ (nomic-embed-text) │
     └────────────────────┘    └────────────────────┘
```

---

## 2. Deploying Retriever Online

### Option A: Any Cloud VPS / VM (Docker Compose) — Recommended

Deployable on any Linux VM (Ubuntu 22.04 / 24.04 on AWS EC2, DigitalOcean, Hetzner, GCP, or Oracle Cloud).

#### Step 1: Clone the Repository on your Server
```bash
git clone https://github.com/prat3010/retriever.git /opt/retriever
cd /opt/retriever
```

#### Step 2: Configure Production Environment Variables
Create `/opt/retriever/.env`:
```ini
# Environment
ENVIRONMENT=production
RETRIEVER_API_URL=https://api.yourdomain.com

# PostgreSQL + pgvector
DATABASE_URL=postgresql+asyncpg://postgres:YourSecurePassword@db:5432/retriever

# Security Keys (Generate via: openssl rand -hex 32)
SECRET_KEY=generate_a_random_64_char_hex_secret_here
KEY_ENCRYPTION_KEY=must_be_exactly_32_bytes_long_key!
ADMIN_MASTER_KEY=generate_another_random_64_char_master_key

# CORS Allowlist (Comma-separated origins of your frontends)
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com,https://admin.yourdomain.com

# Local Ollama Embeddings
OLLAMA_BASE_URL=http://ollama:11434/v1
DEFAULT_EMBEDDING_MODEL=nomic-embed-text

# Optional LLM Key for Inference (BYOK / Client keys can also be supplied per tenant)
OPENAI_API_KEY=sk-...
```

#### Step 3: Boot the Full Stack
```bash
docker compose up -d
```
Docker Compose will launch:
- `db` (PostgreSQL 16 with pgvector extension)
- `redis` (Cache & message broker)
- `ollama` (Pre-pulls `nomic-embed-text` for 100% free local embeddings)
- `api` (FastAPI backend engine on `127.0.0.1:8000`)
- `web` (Retriever Admin Studio on `127.0.0.1:3000`)

#### Step 4: Verify Health
```bash
curl http://localhost:8000/health/readiness
# Output: {"status":"ready","environment":"production"}
```

---

### Option B: Container PaaS (Fly.io / Render / Railway)

If you prefer managed container platforms:

1. **Deploy API Container (`Dockerfile` in root)**
   - Set environment variables listed above in your PaaS dashboard.
   - Attach a PostgreSQL instance with the `vector` extension enabled (e.g. Supabase, Neon, or Tembo).
2. **Deploy Admin Studio Container (`apps/web/Dockerfile`)**
   - Set `NEXT_PUBLIC_RETRIEVER_API_URL=https://<your-api-slug>.fly.dev`.

---

### Option C: Kubernetes (Helm 3 Chart)

For enterprise clusters (EKS, GKE, AKS, or microk8s):

```bash
cd deploy/helm/retriever
helm install retriever . \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=api.yourdomain.com \
  --set config.corsOrigins="https://yourdomain.com"
```

---

## 3. Domain, SSL & CORS Configuration

To expose your backend securely over HTTPS, set up an Nginx reverse proxy with Let's Encrypt:

### Nginx Configuration Template (`/etc/nginx/sites-available/retriever`)
```nginx
server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket & SSE Streaming Support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for real-time token streaming
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

Enable SSL:
```bash
sudo certbot --nginx -d api.yourdomain.com
```

### CORS Configuration
Ensure your frontend domains are included in `CORS_ORIGINS` in `.env`:
```ini
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,http://localhost:3000
```

---

## 4. Connecting to an External Frontend

### Step 0: Onboard a Tenant & Get an API Key
Before querying Retriever, create a tenant workspace. You can do this:
- **Via Admin Web Studio**: Navigate to `https://admin.yourdomain.com/onboard`
- **Via cURL**:
  ```bash
  curl -X POST https://api.yourdomain.com/v1/admin/tenants \
    -H "Authorization: Bearer YOUR_ADMIN_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "My Acme App",
      "slug": "acme_prod",
      "plan": "enterprise"
    }'
  ```
  Note the returned `tenant_id` and issue an API key via `/v1/admin/tenants/{tenantId}/keys`.

---

### Method 1: 1-Line Embeddable Chat Widget (Zero Code)

Embed a responsive AI assistant into **any website** (HTML, Webflow, WordPress, Shopify, Next.js) with zero dependencies.

Add this tag before `</body>`:
```html
<script 
  src="https://api.yourdomain.com/v1/integrations/extension/bundle" 
  data-tenant="YOUR_TENANT_ID" 
  data-key="YOUR_TENANT_API_KEY" 
  data-api-url="https://api.yourdomain.com"
  data-title="Acme Copilot" 
  data-color="#2563eb" 
  data-position="bottom-right">
</script>
```

---

### Method 2: Next.js / React (Secure BFF Pattern)

In modern web frameworks like Next.js App Router, keep your `RETRIEVER_API_KEY` secure on the server side using a **Route Handler (Backend-For-Frontend)**:

#### Server Route Handler (`src/app/api/chat/route.ts`)
```typescript
import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const { sessionId, message } = await req.json();

  const RETRIEVER_URL = process.env.RETRIEVER_API_URL || "https://api.yourdomain.com";
  const TENANT_ID = process.env.RETRIEVER_TENANT_ID!;
  const API_KEY = process.env.RETRIEVER_API_KEY!;

  const upstreamRes = await fetch(
    `${RETRIEVER_URL}/v1/tenants/${TENANT_ID}/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${API_KEY}`,
      },
      body: JSON.stringify({ message }),
    }
  );

  // Stream Server-Sent Events directly back to the user interface
  return new Response(upstreamRes.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}
```

#### React Component (`src/components/ChatWidget.tsx`)
```tsx
"use client";

import { useState } from "react";

export function ChatWidget({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId, message: userMsg }),
    });

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();
    let botReply = "";

    setMessages((prev) => [...prev, { role: "assistant", text: "" }]);

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      // Parse SSE data: chunk format
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              botReply += data.token;
              setMessages((prev) => [
                ...prev.slice(0, -1),
                { role: "assistant", text: botReply },
              ]);
            }
          } catch {}
        }
      }
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>{m.text}</div>
        ))}
      </div>
      <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendMessage()} />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

---

### Method 3: Official TypeScript / JavaScript SDK

Install the decoupled client SDK:
```bash
npm install @prat3010/retriever-client
```

Usage in Node.js or TypeScript:
```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  baseUrl: "https://api.yourdomain.com",
  apiKey: process.env.RETRIEVER_API_KEY!,
  tenantId: "acme_prod",
});

// 1. Hybrid semantic search
const results = await client.search({
  query: "What is the return policy?",
  limit: 5,
});
console.log("Citations:", results);

// 2. Document Ingestion
const doc = await client.uploadDocument({
  file: myFileBuffer,
  filename: "handbook.pdf",
});
```

---

### Method 4: Direct Streaming REST API (cURL / Fetch)

#### 1. Create a Chat Session
```bash
curl -X POST https://api.yourdomain.com/v1/tenants/acme_prod/chat/sessions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "User Support Chat"}'
```
Response returns: `{"session_id": "sess_12345"}`.

#### 2. Stream a Question & Receive Server-Sent Events
```bash
curl -N -X POST https://api.yourdomain.com/v1/tenants/acme_prod/chat/sessions/sess_12345/messages \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize our quarterly roadmap"}'
```

---

### Method 5: Connect AI Assistants via MCP

If you want IDE agents like **Cursor**, **Windsurf**, or **Claude Desktop** to search your live deployed Retriever instance:

Add this to your IDE's `mcpServers` configuration (`mcp_config.json`):
```json
{
  "mcpServers": {
    "retriever": {
      "url": "https://api.yourdomain.com/v1/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TENANT_API_KEY"
      }
    }
  }
}
```
Now your AI agent can invoke `retriever_hybrid_search` and `retriever_upload_file` against your production knowledge base directly while coding!

---

## 5. Production Checklist

- [ ] `RETRIEVER_API_URL` set to public HTTPS domain (e.g. `https://api.yourdomain.com`).
- [ ] `CORS_ORIGINS` configured with exact frontend URLs.
- [ ] Random 64-char `SECRET_KEY`, 32-byte `KEY_ENCRYPTION_KEY`, and `ADMIN_MASTER_KEY` generated.
- [ ] Nginx proxy buffer disabled (`proxy_buffering off;`) to allow low-latency SSE streaming.
- [ ] Port `8000` bound to `127.0.0.1` (never exposed directly to public internet; fronted by Nginx/SSL).
- [ ] Health checks monitored (`/health/readiness` and `/health/liveness`).
