# @prat3010/retriever-client

Official TypeScript and JavaScript client SDK for **Retriever Enterprise Cognitive Engine** (`v1.0.0-rc1`).

[![npm version](https://img.shields.io/npm/v/@prat3010/retriever-client.svg)](https://www.npmjs.com/package/@prat3010/retriever-client)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Batteries](https://img.shields.io/badge/batteries-26%20included-ff69b4.svg)](#-26-platform-batteries-coverage)

---

## 📦 Installation

```bash
npm install @prat3010/retriever-client
# or
pnpm add @prat3010/retriever-client
# or
yarn add @prat3010/retriever-client
```

---

## ⚡ Quick Start

```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  baseUrl: "http://localhost:8000",
  apiKey: "ret_live_demo_00000000000000000000000000000000",
  tenantId: "00000000-0000-0000-0000-000000000001", // Demo Workspace
});

// 1. Hybrid Search (HNSW + BM25 + ColBERT MaxSim)
const searchResults = await client.search("How does ColBERT late interaction work?", {
  enableColbertRerank: true,
  limit: 5,
});

console.log(`Found ${searchResults.total} chunks in ${searchResults.latency_ms}ms:`);
for (const chunk of searchResults.results) {
  console.log(`- [${chunk.score.toFixed(3)}] ${chunk.content.slice(0, 100)}...`);
}
```

---

## 🔄 Autonomous Multi-Turn ReAct Chat Loop

Stream real-time agent thoughts, tool execution milestones, and token emissions:

```typescript
const sessionId = "session-test-uuid";

for await (const event of client.streamReActChat(sessionId, "Explain memory decay and verify our platform batteries.")) {
  switch (event.type) {
    case "thought":
      console.log(`🤔 [Agent Thought]: ${event.content}`);
      break;
    case "tool_call_start":
      console.log(`⚡ [Invoking Tool]: ${event.tool_name}(${JSON.stringify(event.arguments)})`);
      break;
    case "tool_call_done":
      console.log(`✅ [Tool Completed] in step ${event.step}`);
      break;
    case "token":
      process.stdout.write(event.content ?? "");
      break;
  }
}
```

---

## 🤝 Multi-Agent Swarm Quorum & Dialectic Debate

Coordinate multi-role agent consensus (Planner, Auditor, Synthesizer, Skeptic):

```typescript
const debate = await client.executeSwarmDebate(
  "Analyze high-concurrency database migration from MySQL to PostgreSQL pgvector",
  ["planner", "auditor", "synthesizer", "skeptic"],
  2 // Max rounds
);

console.log(`Consensus (Confidence: ${(debate.quorum_confidence * 100).toFixed(1)}%):`);
console.log(debate.consensus_response);
console.log(`Pruned ${debate.pruned_hallucinations_count} unverified hallucinations.`);
```

---

## 🧠 Cognitive Memory Consolidation (Battery #25)

Query and synthesize long-horizon episodic & procedural memory:

```typescript
// Query consolidated memory nodes
const memories = await client.queryCognitiveMemory("PostgreSQL database deadlocks");
for (const mem of memories) {
  console.log(`[${mem.category.toUpperCase()} | Retention: ${mem.retention_score}] ${mem.content}`);
}

// Distill recent session traces into procedural heuristics
await client.synthesizeMemoryExperience(sessionId);
```

---

## 🔋 26 Platform Batteries Coverage

| Battery | Feature | Method |
|:---:|:---|:---|
| **1–3** | Hybrid Retrieval & ColBERT Rerank | `client.search()` |
| **4** | Layout OCR & Ingestion | `client.uploadDocument()` |
| **5** | RLM Python REPL Sandbox | `client.executeRlmCode()` |
| **21** | Micro-Enclave Remote Attestation | `client.getEnclaveAttestation()` |
| **23** | Universal MCP Tools Protocol | `client.listMcpTools()`, `client.callMcpTool()` |
| **24** | Autonomous ReAct Loop | `client.streamReActChat()` |
| **25** | Cognitive Agent Memory | `client.queryCognitiveMemory()`, `client.synthesizeMemoryExperience()` |
| **26** | Multi-Agent Swarm Quorum | `client.executeSwarmDebate()` |

---

## 📄 License

Apache-2.0. Maintained by [Prateek Sharma](https://prateeq.in).
