# Operational Runbook: Edge AI Token Shield, DDoS Defense & SSE Reconnection Protocol

**Document Status:** Production-Ready  
**Milestone:** 86 (v0.71.0)  
**Target Audience:** SREs, Security Engineers, Frontend Engineers & API Consumers  

---

## 1. Problem Statement: AI Token Drainage Attacks

Traditional Web Application Firewalls (WAFs) measure request frequency (e.g. 1,000 requests/minute). In Generative AI systems, an attacker can launch an **Asymmetric Denial-of-Wallet (DoW) Attack**:
- By sending just 10 concurrent requests with massive 50,000-token prompts and requesting 4,000-token completions, an attacker can consume millions of LLM tokens and exhaust API quotas or generate thousands of dollars in cloud bills without ever triggering traditional HTTP request limits.

**Milestone 86** establishes a multi-layered **Edge AI Token Shield** combining distributed sliding-window rate limiting with resilient Server-Sent Event (SSE) connection recovery.

---

## 2. Dual-Mode Sliding-Window Rate Limiter Architecture

The Token Shield operates across both the Next.js edge control plane (`src/lib/rateLimit.ts`) and the FastAPI backend (`apps/api/src/routers/tenant.py`):

```text
                  [Incoming Request]
                           │
                           ▼
             ┌───────────────────────────┐
             │ Upstash Redis REST Config?│
             └─────────────┬─────────────┘
                           │
                 Yes ──────┴────── No (or Redis Down)
                  │                 │
                  ▼                 ▼
         ┌────────────────┐ ┌────────────────┐
         │ Upstash Redis  │ │ Thread-Safe    │
         │ Sliding Window │ │ In-Memory LRU  │
         │ REST API       │ │ Cache Fallback │
         └───────┬────────┘ └───────┬────────┘
                 │                  │
                 └─────────┬────────┘
                           │
                           ▼
           Quota Check: (Used <= Limit)?
             ├── YES ──> Allow Request (Append RFC 429 headers)
             └── NO  ──> HTTP 429 Too Many Requests (`Retry-After`)
```

### A. Primary Mode: Upstash Redis REST API
- Uses atomic sliding-window incrementing over HTTPS REST (`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`).
- Works seamlessly in serverless edge environments (Vercel Edge, Cloudflare Workers) without persistent TCP connection overhead.

### B. Fallback Mode: Thread-Safe In-Memory LRU
- If Upstash credentials are not supplied (e.g. during local development or offline CI), the engine automatically falls back to an **In-Memory sliding-window LRU**.
- Thread-safe, self-evicting, and operates with zero external dependencies and **$0 cloud cost**.

---

## 3. Rate Limit Quotas by Endpoint

| Endpoint Scope | Default Rate Limit | Cooldown Window | Target Threat |
| :--- | :--- | :--- | :--- |
| **`/api/scoping/parse-intent`** | 10 requests | 60 seconds | Natural language scope parser token abuse |
| **`/api/scoping/parse-rfp`** | 5 requests | 60 seconds | Heavy multi-page PDF RFP extraction |
| **`/api/client/copilot`** | 20 requests | 60 seconds | Client workspace scoping AI copilot |
| **`/api/contact`** | 5 requests | 60 seconds | Spam bots & email inundation |
| **`/v1/tenants/{tenantId}/intent/classify`** | 30 requests | 60 seconds | Backend query router spam |

---

## 4. RFC 429 Standard Rate Limit Headers

Every response emitted through the Token Shield includes standard RFC rate limit headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1725418860
```

When a caller exceeds the window quota, the server returns an RFC 429 response with a `Retry-After` header specifying the exact number of seconds until the window resets:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 42
Content-Type: application/json

{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Please retry in 42 seconds.",
  "retryAfter": 42
}
```

---

## 5. Resilient SSE Reconnection Protocol

### The Problem with Real-Time Streaming
Mobile users frequently experience broken SSE streams when walking out of Wi-Fi range or switching cellular towers. Traditional SSE connections fail permanently, leaving the user with half-rendered responses and forcing a complete re-query.

### The Solution: Sequential Event IDs & Exponential Backoff
Retriever implements the **HTML5 EventSource `Last-Event-ID` Standard**:

```text
Server Event: id: 14\ndata: {"token": "architecture"}\n\n
                       ... (Network Disconnect) ...
Client Reconnect: GET /v1/chat/stream HTTP/1.1
                  Last-Event-ID: 14
Server Response:  Resumes token stream from event #15 without re-invoking LLM!
```

1. **Sequential Event Tracking:** Every token chunk emitted by Retriever includes an incremental event sequence (`id: {event_seq}`).
2. **Client State Cache:** The client frontend (`rag-client.ts`, `ChatPanel.tsx`) tracks `lastEventId`.
3. **3-Attempt Exponential Backoff:** If the TCP socket severs, the client immediately retries:
   - Attempt 1: 500ms delay
   - Attempt 2: 1,500ms delay
   - Attempt 3: 3,500ms delay
4. **Seamless Token Append:** Re-established stream resumes appending new tokens directly into the existing message bubble without UI flicker.

---

## 6. SRE Configuration & Troubleshooting

### Enabling Upstash Redis in Production
Set the following environment variables in Vercel or Oracle VPS:
```bash
UPSTASH_REDIS_REST_URL="https://your-upstash-redis.upstash.io"
UPSTASH_REDIS_REST_TOKEN="your-upstash-rest-token"
```

### Verifying Fallback Mode in Local Development
If Upstash is unconfigured, inspect application logs on startup:
```text
[info] Upstash credentials not found; Edge Token Shield initialized in In-Memory LRU fallback mode.
```
This confirms that rate limiting is active locally without requiring an internet connection or credit card.
