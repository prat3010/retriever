---
id: Guide_Cloudflare_Proxy_Worker
title: "Client Integration Guide: Cloudflare Edge Proxy Worker"
tier: 4_api_gateway
platform: retriever
tags:
  - integrations/cloudflare
  - edge-proxy
  - security/jwt
  - platform/retriever
blast_radius: MEDIUM
invariants:
  - "Edge proxy worker MUST inject tenant API secret and strip client Authorization before hitting origin."
---

# Client Integration Guide: Cloudflare Edge Proxy Worker

#integrations #cloudflare #workers #edge #proxy #cors #retriever

> **Architecture, deployment steps, and complete TypeScript source code for deploying a zero-latency Cloudflare Edge Worker proxy.**

---

## 1. Edge Proxy Architecture

```mermaid
flowchart LR
    Browser[Client Web Application] -->|Public Request + User JWT| Worker[Cloudflare Edge Worker]
    Worker -->|Validate Supabase RS256 JWT| Worker
    Worker -->|Inject Server Secret API Key| Origin[Retriever Core API Origin (rag.prateeq.in)]
    Origin -->|SSE Token Stream| Worker
    Worker -->|Forward SSE Stream + CORS Headers| Browser
```

---

## 2. Worker Implementation (`worker.ts`)

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // 1. Handle CORS Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
      });
    }

    // 2. Clone request and inject Tenant Service Secret
    const url = new URL(request.url);
    url.hostname = "rag.prateeq.in";

    const modifiedHeaders = new Headers(request.headers);
    modifiedHeaders.set("X-API-Key", env.RETRIEVER_SERVER_API_KEY);

    const originResponse = await fetch(url.toString(), {
      method: request.method,
      headers: modifiedHeaders,
      body: request.body,
    });

    // 3. Return Streaming Response with CORS
    const responseHeaders = new Headers(originResponse.headers);
    responseHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(originResponse.body, {
      status: originResponse.status,
      headers: responseHeaders,
    });
  },
};
```

---

## 🔗 Related Architecture & Cross-References
- [Auth & Identity Specification](../api/auth.md)
- [Chat & Streaming API](../api/chat.md)
