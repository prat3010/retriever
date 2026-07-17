# Frontend Integration & Secure Client Proxy Guide

This guide details how to securely connect public frontend applications (such as iOS/Android mobile apps or web clients) to your **Retriever** RAG backend.

The current production deployment runs entirely on free-tier infrastructure:
- **API**: Render (free web service, Docker)
- **Database**: Supabase (free tier, PostgreSQL + pgvector)
- **Embeddings**: HuggingFace Inference API (free, `BAAI/bge-base-en-v1.5`, 768-dim)
- **LLM**: Client BYOK (tenant provides their own API key)
- **Proxy**: Cloudflare Workers (free, 100k req/day)

---

## 1. Rationale: Why Direct Connection is Dangerous

If your mobile app talks directly to the Retriever backend, you must store your tenant's master API key inside the mobile app:

```
[Mobile App Code] ---> HTTP Headers: X-API-Key: "tenant-key-123" ---> [Retriever API]
```

**The Threat:**
Mobile app binaries (IPAs and APKs) can be decompiled in seconds using standard reverse-engineering tools (e.g., Apktool, class-dump). Once an attacker extracts your `X-API-Key`, they can:
- Read all your private company documents.
- Overwrite your configurations or prompts.
- Spam the search/chat endpoints to run up your LLM bills.
- Exceed your rate limits, causing denial-of-service for legitimate users.

---

## 2. The Solution: The Safe Proxy Architecture

Instead of direct connection, route client traffic through an edge-based **Cloudflare Worker Proxy**. The proxy validates your user's auth token, injects the hidden API key from environment secrets, and forwards the request to your live Retriever engine.

```
Client App → Cloudflare Proxy (JWT auth, key injection) → Render (API) → Supabase (DB, vectors, RLS)
                                                                         → HuggingFace (embeddings)
                                                                         → Tenant's LLM
```

---

## 3. How to Deploy the Proxy Worker

We have packaged a ready-to-deploy proxy worker template under `packages/client-proxy-worker/`.

### Step 1: Install Dependencies
```bash
cd packages/client-proxy-worker
npm install
```

### Step 2: Configure Environment
Open `wrangler.toml` and set `RETRIEVER_API_URL` to the production API URL:
```toml
[vars]
RETRIEVER_API_URL = "https://retriever-1vjx.onrender.com"
```

### Step 3: Set Your API Key Secret
```bash
npx wrangler secret put RETRIEVER_API_KEY
```
*(Paste the target tenant's `X-API-Key` from the Admin Dashboard).*

### Step 4: Deploy
```bash
npx wrangler deploy
```
Outputs your proxy URL (e.g., `https://retriever-client-proxy.retriever.workers.dev`).

---

## 4. Configuring the JWT Claims

Your mobile app authentication system (e.g., Supabase Auth, Firebase Auth, or a custom authentication server) must issue a JSON Web Token (JWT) containing the following claims:

```json
{
  "sub": "user-uuid-12345",         // Unique user identifier (will map to X-User-ID)
  "tenant_id": "tenant-uuid-abcde", // The tenant ID this user belongs to
  "exp": 1718919600                 // Expiration timestamp (Unix epoch seconds)
}
```

*Note: The proxy code in `src/index.ts` automatically parses these claims to route the requests and inject headers.*

---

## 5. Client Integration Code Examples (TypeScript / React Native)

Below are functional snippets demonstrating how your mobile application can communicate with the proxy.

### A. Performing a Vector Search
```typescript
interface SearchResult {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
}

async function searchDocuments(query: string, userJwt: string): Promise<SearchResult[]> {
  const response = await fetch("https://retriever-client-proxy.yourdomain.workers.dev/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${userJwt}`
    },
    body: JSON.stringify({
      query: query,
      limit: 5
    })
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error || "Search failed");
  }

  return response.json();
}
```

### B. Creating a Chat Session
```typescript
interface ChatSession {
  session_id: string;
  title: string;
}

async function createChatSession(userJwt: string): Promise<ChatSession> {
  const response = await fetch("https://retriever-client-proxy.yourdomain.workers.dev/chat/sessions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${userJwt}`
    }
  });

  if (!response.ok) {
    throw new Error("Failed to create chat session");
  }

  return response.json();
}
```

### C. Streaming Chat Responses (SSE) on Mobile
To support real-time token-by-token streaming, consume the Server-Sent Events stream using a text decoder:

```typescript
async function streamChatMessage(
  sessionId: string,
  message: string,
  userJwt: string,
  onChunk: (text: string) => void,
  onDone: () => void
) {
  const response = await fetch(
    `https://retriever-client-proxy.yourdomain.workers.dev/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userJwt}`,
        "Accept": "text/event-stream"
      },
      body: JSON.stringify({
        query: message,
        stream: true
      })
    }
  );

  if (!response.ok || !response.body) {
    throw new Error("Streaming connection failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    
    // Process all complete lines, leaving partial chunk in buffer
    buffer = lines.pop() || "";

    for (const line of lines) {
      const cleanLine = line.trim();
      if (!cleanLine) continue;
      
      if (cleanLine.startsWith("data: ")) {
        const rawData = cleanLine.substring(6);
        try {
          const parsed = JSON.parse(rawData);
          // Yield character delta (SSE event data format)
          if (parsed.event === "token" && parsed.delta) {
            onChunk(parsed.delta);
          } else if (parsed.event === "done") {
            onDone();
            return;
          }
        } catch {
          // Skip malformed SSE noise lines
        }
      }
    }
  }
}
```

---

## 6. Frontend RAG UX Best Practices

When building RAG-based search and chat interfaces, implement these design patterns to ensure a smooth, premium user experience.

### A. Auto-Scroll Lock during Streaming
When rendering streaming text block-by-block, your chat window should auto-scroll down to show incoming content. However, if the user scrolls up to check an earlier message, auto-scrolling will disrupt their reading.
*   **Best Practice:** Check the scroll window offset. If the user scrolls up past a threshold (e.g., more than 100px from the bottom), lock auto-scrolling. Show a floating action button saying *"New token incoming... [Scroll to bottom]"*. Resume automatic scrolling only when they click the button or scroll back down.

### B. Interactive Citation Badges
Retriever formats source citations based on the active tenant's `citation_template` setting (e.g., `[1]`, `[Source PDF]`).
*   **Best Practice:** Do not leave citations as plain text. Run a regex match over incoming stream chunks to extract citation markers and render them as clickable inline UI badges.
*   **Interaction:** Clicking a citation badge should slide up a bottom sheet card displaying the exact document text snippet that was retrieved, allowing users to verify facts without losing their place in the chat.

### C. Optimistic UI Updates
Generating embeddings, running vector searches, and awaiting the first LLM token stream takes 500ms to 2s depending on the cloud compute status.
*   **Best Practice:** The moment a user taps send, immediately update the message bubble UI list with their text, clear the input, and display a "typing indicator" (e.g., bouncing dots or skeleton block). Once the first SSE chunk arrives, replace the indicator with the streaming text.

### D. Local Chat Caching (Offline-First)
Querying the remote database for previous messages on every application launch adds latency and ruins offline availability.
*   **Best Practice:** Cache conversations locally. Store the list of sessions and messages in a local client database (e.g. **Expo SQLite** or **WatermelonDB**). Render the cache immediately on boot for a 0ms load speed, and fetch the server API in the background to sync updates.

### E. Stream Cancellation & AbortController
If the user navigates away or walks into a cellular dead-zone, active HTTP requests should be terminated.
*   **Best Practice:** Store an `AbortController` reference on every stream request. If the user clicks "Cancel" or closes the conversation view, call `controller.abort()` to terminate the HTTP connection. The cloud API will immediately detect the client close-event, aborting backend tasks and freeing up resources.

---

## 7. Production Deployment & Connection Checklist

### Current Stack (Free Tier)

| Component | Provider | URL |
|-----------|----------|-----|
| API | Render | `https://retriever-1vjx.onrender.com` |
| Database | Supabase (us-west-2) | Session pooler via `aws-1-us-west-2.pooler.supabase.com` |
| Embeddings | HuggingFace Inference API | `BAAI/bge-base-en-v1.5` via `router.huggingface.co/hf-inference/models/{model}` |
| Proxy | Cloudflare Workers | `https://retriever-client-proxy.retriever.workers.dev` |

### Step 1: Deploy the API on Render
- Push the repo to GitHub (Render auto-deploys from `main`).
- Set the following env vars in Render dashboard:
  - `DATABASE_URL` — Supabase pooler connection string
  - `HF_API_TOKEN` — your HuggingFace API token (free, optional)
- The code auto-detects Render via the `RENDER` env var (set automatically) and switches to `production` mode.

### Step 2: Onboard Tenant
- Run the Admin Dashboard locally, or use the API directly.
- Create a Tenant, generate an API Key, configure prompts.

### Step 3: Deploy the Proxy Worker
```bash
cd packages/client-proxy-worker
npx wrangler secret put RETRIEVER_API_KEY  # paste tenant API key
npx wrangler deploy
```

### Step 4: Configure Frontend
```env
EXPO_PUBLIC_API_URL=https://retriever-client-proxy.retriever.workers.dev
```

### Step 5: Issue User JWT Tokens
JWT must contain:
- `sub`: user UUID (maps to `X-User-ID`)
- `tenant_id`: tenant UUID (routes to correct tenant)

### Step 6: Ingest Documents
Upload via `POST /v1/admin/tenants/{tenantId}/documents/ingest`. Processing is synchronous (no Celery).


