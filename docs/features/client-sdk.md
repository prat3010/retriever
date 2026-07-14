# Client SDK Integration Guide

This guide describes how to install, configure, and use the lightweight TypeScript/JavaScript Client SDK (`@prat3010/retriever-client-js`) to build multi-tenant Retrieval-Augmented Generation (RAG) applications on top of the Retriever Core Platform.

---

## 🚀 Quickstart: Add Retriever in 5 Minutes

### 1. Installation

Install the client SDK in your web application workspace:
```bash
npm install @prat3010/retriever-client-js
```

### 2. Initialization

Initialize the `RetrieverClient` using your active tenant credentials. In client-side components, request context is automatically scoped to the active tenant.

```typescript
import { RetrieverClient } from "@prat3010/retriever-client-js";

const client = new RetrieverClient({
  baseUrl: "https://api.retriever-core.com",
  apiKey: "ret_live_your_tenant_api_key.secret",
  tenantId: "8ca819f7-640a-4286-8d19-ee3271701b2a",
  userId: "user_customer_9901" // Optional: scopes subsequent chat history automatically
});
```

---

## 🛠️ Usage Examples

### 📂 Document Ingestion (With Idempotency Key)

Upload files dynamically. By specifying a unique `idempotencyKey`, you guarantee that retry attempts do not trigger duplicate Celery extraction worker runs or produce duplicate vector records.

```typescript
const file = ...; // Browser File object, Blob, or Node Buffer

try {
  const result = await client.uploadDocument(
    file,
    "user_manual.pdf",
    "application/pdf",
    "upload_token_session_hash_123" // Idempotency key (forces deduplication on retries)
  );
  console.log("Ingestion scheduled:", result.documentId);
} catch (error) {
  console.error("Upload failed:", error);
}
```

### 🔍 Execute Semantic & Hybrid Search

Execute high-performance RAG hybrid queries merging pgvector cosine distance metrics and BM25 keyword rankings.

```typescript
const searchResults = await client.search("How do I reset my credentials?", {
  limit: 5
});

searchResults.results.forEach((match) => {
  console.log(`[Score: ${match.score}] Chunk: ${match.content}`);
});
```

### 💬 Chat Session Creation & SSE Streaming

Initiate an interactive generative session and read streaming response chunks line-by-line using a standard JavaScript asynchronous iterator.

```typescript
// 1. Create a chat session
const { sessionId } = await client.createSession();

// 2. Stream answer chunks via SSE
const chatStream = client.chatStream(sessionId, "What is the return policy?");

for await (const chunk of chatStream) {
  if (chunk.content) {
    process.stdout.write(chunk.content); // Output answer tokens as they arrive
  }
}
```

---

## 📄 Pagination & List Operations

All SDK listing methods return cursor-based pagination blocks. You can traverse records backward and forward reliably.

```typescript
// Fetch page 1 of document records
const page1 = await client.listDocuments({ limit: 10 });

if ('items' in page1) {
  console.log("Documents:", page1.items);
  
  if (page1.pagination.hasMore && page1.pagination.nextCursor) {
    // Fetch page 2 using the nextCursor
    const page2 = await client.listDocuments({
      limit: 10,
      cursor: page1.pagination.nextCursor
    });
    console.log("Page 2 items:", page2.items);
  }
}
```

Similarly, query chat history for a session:
```typescript
const history = await client.listMessages(sessionId, { limit: 20 });
console.log("Last messages:", history.items);
console.log("Next page cursor:", history.pagination.nextCursor);
```

---

## 🚦 Enforcing Rate Limits & Headers

The client SDK automatically passes credentials, and the API returns standardized rate limiting metadata headers on all responses. If rate limits are exceeded, a standard `429 Too Many Requests` HTTP error is raised:

- `X-RateLimit-Limit`: The request window quota.
- `X-RateLimit-Remaining`: The remaining capacity within the current window.
- `X-RateLimit-Reset`: The cooldown period in seconds before the quota resets.

The SDK will raise an error that contains these rate limiting headers for proper handling in UI error states.
