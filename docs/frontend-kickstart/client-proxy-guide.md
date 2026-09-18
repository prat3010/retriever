# Frontend Integration & Secure Client Proxy Guide

This guide details how to securely connect public frontend applications (such as iOS/Android mobile apps or web clients) to your **Retriever** RAG backend.

The current production deployment runs on production-grade infrastructure:
- **API**: Oracle Cloud VPS (`http://localhost:8000` at `YOUR_SERVER_IP`, Ubuntu 24.04, FastAPI, systemd)
- **Database**: Supabase (PostgreSQL + pgvector)
- **Embeddings**: Local Ollama (`nomic-embed-text` on `http://localhost:11434`, 768-dim) to eliminate API rate limits and external costs
- **LLM**: Client BYOK / Tenant configured keys (Gemini, OpenAI, Anthropic, or local)
- **Mobile Proxy**: Cloudflare Workers edge proxy (`packages/client-proxy-worker/`)
- **Web Proxy**: Next.js API Route Handlers / Server Actions (Backend-for-Frontend / BFF pattern)

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

Instead of direct connection, route client traffic through an edge-based **Cloudflare Worker Proxy** (for mobile apps) or **Next.js Route Handlers** (for web apps). The proxy validates your user's auth token, injects the hidden API key from environment secrets, and forwards the request to your live Retriever engine.

```
Client App (Mobile) ───────→ Cloudflare Proxy (JWT auth, key injection) ──┐
                                                                           ├──→ Oracle VPS (FastAPI: http://localhost:8000)
Client App (Web/Next.js) ──→ Next.js Route Handler (BFF pattern) ─────────┘        ├──→ Local Ollama (nomic-embed-text)
                                                                                   ├──→ Supabase (DB, vectors, RLS)
                                                                                   └──→ Tenant's LLM
```

> **Architecture Note:**
> - **Native Mobile Apps (React Native / Expo / Flutter):** Must route through the Cloudflare Worker proxy (`packages/client-proxy-worker`) because client app binaries cannot keep secrets safe.
> - **Web Apps (Next.js / SvelteKit / Remix):** Do **not** need Cloudflare Workers. Your Next.js server route handlers (e.g. `src/app/api/chat/route.ts`) act as the secure BFF proxy directly on Vercel/Node.js, keeping `RETRIEVER_API_KEY` safe in `.env.local`.

---

## 3. How to Deploy the Proxy Worker (for Mobile Apps)

We have packaged a ready-to-deploy proxy worker template under `packages/client-proxy-worker/`.

### Step 1: Install Dependencies
```bash
cd packages/client-proxy-worker
npm install
```

### Step 2: Configure Environment
Open `wrangler.toml` and verify `RETRIEVER_API_URL` points to the production API URL:
```toml
[vars]
RETRIEVER_API_URL = "http://localhost:8000"
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

### Current Stack

| Component | Provider | URL / Endpoint |
|---|---|---|
| **API Engine** | Oracle Cloud VPS | `http://localhost:8000` (IP: `YOUR_SERVER_IP`) |
| **Admin Dashboard** | Vercel | `http://localhost:3000` (`retriever/apps/web`) |
| **SaaS App Studio** | Vercel | `http://localhost:3000` (`Prateek_website`) |
| **Database** | Supabase (us-west-2) | PostgreSQL + pgvector session pooler |
| **Embeddings** | Local Ollama VPS | `nomic-embed-text` (768-dim) on `http://localhost:11434` |
| **Mobile Proxy** | Cloudflare Workers | Edge Worker template (`packages/client-proxy-worker`) |

### Step 1: Verify Live API Health
The live engine runs 24/7 on Oracle Cloud VPS managed via systemd:
```bash
curl http://localhost:8000/health/readiness
# Returns: {"status":"ready"}

curl http://localhost:8000/v1/admin/platform/batteries
# Returns: {"total":38,"active":36}
```

### Step 2: Onboard Tenant & Issue Credentials
- Navigate to **[`http://localhost:3000/onboard`](http://localhost:3000/onboard)**.
- Create a Tenant (e.g. `tn_evolution_story`), generate a Client API Key (`ret_live_...`), and configure initial prompt templates.

### Step 3: Choose Integration Strategy

#### Path A: Web Application (Next.js / SvelteKit / Remix)
- **Do not deploy the Cloudflare Worker.**
- Store secrets securely in `.env.local`:
  ```env
  RETRIEVER_API_URL=http://localhost:8000
  RETRIEVER_TENANT_ID=your-tenant-uuid
  RETRIEVER_API_KEY=your-client-api-key
  ```
- Make server-side calls directly via Next.js Route Handlers (e.g. `/api/chat/route.ts`) or use the `@prat3010/retriever-client-js` SDK in Node.js server context.

#### Path B: Mobile Application (React Native / Expo / Flutter)
- Deploy the Cloudflare Worker proxy to guard the API key from binary decompilation:
  ```bash
  cd packages/client-proxy-worker
  npx wrangler secret put RETRIEVER_API_KEY  # Paste target tenant API key
  npx wrangler deploy
  ```
- Configure your mobile app environment:
  ```env
  EXPO_PUBLIC_API_URL=https://retriever-client-proxy.your-account.workers.dev
  ```
- Pass the user's authenticated session JWT with `sub` (User ID) and `tenant_id` (Tenant UUID).

### Step 4: Ingest Story / Domain Knowledge
Upload knowledge documents using the Admin Dashboard at `http://localhost:3000/tenants/{tenantId}` or via API:
```bash
POST /v1/admin/tenants/{tenantId}/documents/upload
```



