---
id: Guide_TypeScript_SDK
title: "Client Integration Guide: @retriever/client-js TypeScript SDK"
tier: 5_core_domain
platform: retriever
tags:
  - integrations/typescript-sdk
  - sdk
  - sse
  - client
  - platform/retriever
blast_radius: LOW
invariants:
  - "TypeScript SDK MUST support async iterators for streaming token events."
---

# Client Integration Guide: `@retriever/client-js` TypeScript SDK

#integrations #sdk #typescript #javascript #client #retriever

> **Comprehensive guide, API reference, and production examples for the `@retriever/client-js` SDK.**

---

## 1. Installation

```bash
npm install @retriever/client-js
# or
pnpm add @retriever/client-js
# or
bun add @retriever/client-js
```

---

## 2. Quickstart & Core Methods

```typescript
import { RetrieverClient } from "@retriever/client-js";

// Initialize client
const client = new RetrieverClient({
  baseUrl: "https://rag.prateeq.in",
  apiKey: "ret_live_a1b2c3d4e5f67890abcdef...",
});

// 1. Upload a Document
const doc = await client.documents.upload({
  file: myFileBlob,
  filename: "Quarterly_Report_2026.pdf",
  chunkStrategy: "docling_layout",
  metadata: { department: "finance" },
});
console.log("Uploaded Document ID:", doc.documentId);

// 2. Stream Grounded Chat Completion
const stream = await client.chat.stream({
  sessionId: "4a1d8e9f-5b2c-4e3a-8f1d-9c8e7a6b5c4d",
  message: "What were our total Q2 cloud expenditures?",
});

for await (const event of stream) {
  if (event.type === "token") {
    process.stdout.write(event.delta);
  } else if (event.type === "citation") {
    console.log(`\n[Citation: ${event.filename} (Score: ${event.score})]`);
  }
}
```

---

## 🔗 Related Architecture & Cross-References
- [Chat & Streaming API Specification](../api/chat.md)
- [Document Ingestion API](../api/document.md)
- [Search API](../api/search.md)
