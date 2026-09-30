# Retriever — Open-Source Multi-Tenant RAG Engine

<div align="center">

[![Release](https://img.shields.io/badge/release-v2.2.0-blueviolet.svg)](https://github.com/prat3010/retriever/releases)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Tests](https://img.shields.io/badge/tests-passed%20%E2%9C%93-brightgreen.svg)](tests/)
[![Architecture](https://img.shields.io/badge/architecture-hexagonal-green.svg)](#-architecture)

**A fast, local-first retrieval engine replacing the fragmented LangChain + Pinecone + LiteLLM stack.**  
*Strict PostgreSQL Row-Level Security, pgvector HNSW + BM25 hybrid search, $0 local Ollama embeddings, Celery async ingestion, and a 1-line embeddable chat widget.*

[🚀 Quickstart](#-quick-start) • [🏗️ Architecture](#️-architecture) • [📖 Core Subsystems](#-core-subsystems) • [🔌 Client SDKs](#-client-sdks) • [📊 Benchmarks](docs/benchmarks/EMPIRICAL_LOAD_BENCHMARK_REPORT.md)

</div>

---

## 💡 Why Retriever?

Most RAG setups in production end up as fragile glue code: teams stitch together LangChain (heavy abstractions), Pinecone or Qdrant ($100s/mo with cross-tenant leak risks), LiteLLM, Celery, and custom OCR scripts.

**Retriever replaces the fragmented stack with a single, high-performance engine built on PostgreSQL 16 + pgvector:**

| Capability | Retriever (Open-Source) | Pinecone / Closed Cloud | LangChain / LlamaIndex |
|:---|:---:|:---:|:---:|
| **Architecture** | **Pure Hexagonal (Zero Lock-in)** | Proprietary Cloud | Library Wrappers |
| **Multi-Tenancy** | **PostgreSQL RLS (Database-Level)** | Namespace Filtering | Application-Level Filtering |
| **Hybrid Retrieval** | **Concurrent HNSW + BM25 + RRF Fusion** | Dense Vector Only | Manual Glue Code |
| **Reranking** | **ColBERT MaxSim Late Interaction** | Add-on Service | Separate Library |
| **Embeddings** | **$0 Local Ollama (`nomic-embed-text`)** | Cloud API Costs | External Provider |
| **Document Ingestion** | **Docling OCR + Celery Worker Queues** | None | Community Loaders |
| **Deploy Target** | **1-Click Docker Compose ($10/mo VPS)** | Cloud Subscription | Self-Managed Pipeline |

---

## 🎯 Production Use Cases

Retriever is designed for engineering teams that need rock-solid, verifiable retrieval without multi-vendor subscription sprawl:

### 1. 🏢 Multi-Tenant B2B AI SaaS
* **Strict Tenant Isolation:** Enforced via PostgreSQL Row-Level Security (RLS) directly on connection sessions (`SET LOCAL app.current_tenant = ...`). Vectors, chunks, and metadata cannot leak across tenant boundaries, even if application logic fails.
* **Per-Tenant Quotas:** Built-in rate limiting, token budgets, and API key management per workspace.

### 2. 💬 1-Line Embeddable AI Concierge
* **Instant Deployment:** Drop a single `<script src=".../widget.js">` tag onto any website, documentation portal, or e-commerce store.
* **Custom Persona & Branding:** Configure system prompts, theme accents, and custom greetings via REST API or the Web Studio.

### 3. 📄 High-Precision Enterprise Document Grounding
* **Tabular Layout Accuracy:** Vision-native Docling OCR preserves multi-column PDF layouts, tables, and section hierarchies.
* **Verifiable Citations:** Returns page numbers, character ranges, and presigned document links so users can audit the exact source of every answer.

### 4. 💰 $0 Local-First RAG
* **Zero API Costs for Vectors:** Generates high-dimensional vector embeddings locally via Ollama (`nomic-embed-text`) with zero per-token fees.
* **Semantic Answer Cache:** Sub-15ms cached responses for recurring user questions, slashing downstream LLM inference costs.

---

## ⚡ Quick Start

Spin up the entire platform locally with zero external API dependencies (runs 100% free with local Ollama embeddings):

### Option A: Docker Compose (Production Stack)
```bash
# 1. Clone and launch full stack (PostgreSQL 16 + pgvector, Redis, Ollama, API, Web Studio)
git clone https://github.com/prat3010/retriever.git && cd retriever
docker compose up -d

# 2. Verify readiness
curl http://localhost:8000/health/readiness
# {"status":"ready","environment":"production"}

# 3. Query the auto-seeded demo workspace
curl -X POST http://localhost:8000/v1/tenants/00000000-0000-0000-0000-000000000000/search \
  -H "Authorization: Bearer ret_live_demo_00000000000000000000000000000000" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does hybrid search fusion work?"}'
```

- **Interactive Swagger Docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Web Admin Studio:** [`http://localhost:3000`](http://localhost:3000)

### Option B: Local Python Development
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest apps/api/tests/
```

---

## 🏗️ Core Subsystems

Retriever wires together production-tested retrieval components through Hexagonal dependency injection:

| Subsystem | Layer | Description |
|:---|:---|:---|
| **`pgvector_hnsw`** | Core Retrieval | Sub-millisecond approximate nearest-neighbor search directly in PostgreSQL. |
| **`sparse_bm25`** | Core Retrieval | PostgreSQL full-text search with stemming and Reciprocal Rank Fusion (RRF). |
| **`colbert_maxsim`** | Reranking | Fine-grained token-level cross-attention similarity for high-precision spans. |
| **`docling_parser`** | Ingestion | Layout-aware multi-column PDF and table Markdown extraction. |
| **`semantic_cache`** | Performance | Vector-similarity caching for sub-15ms instant responses to repeated queries. |
| **`celery_workers`** | Async Pipeline | Background worker swarm for non-blocking document ingestion and vectorization. |
| **`rls_isolation`** | Security | PostgreSQL Row-Level Security ensuring strict multi-tenant boundary enforcement. |
| **`streaming_sse`** | Real-Time API | Server-Sent Events delivering token streaming with live citation references. |
| **`widget_embed`** | Integration | Standalone `<script>` embed widget with customizable theme and system prompts. |
| **`resilient_embedder`** | Reliability | Stateful circuit breaker with deterministic local Ollama fallback. |

---

## 🛠️ Developer Tools

Retriever ships with out-of-the-box CLI, IDE, and browser tools so you can test and ingest knowledge in seconds:

### 1. 💬 Terminal Chat REPL
Chat directly with your vector knowledge base from your shell with grounded citations:
```bash
python3 scripts/chat_repl.py
```

### 2. 📂 Batch Directory Ingestion
Recursively crawl and vector-index an entire directory of PDFs, Markdown, TXT, or JSON files in one command:
```bash
python3 scripts/ingest_directory.py --tenant <tenantId> --dir ./docs
```

### 3. 🌐 1-Line Embeddable Chat Widget
Drop an AI assistant into **any** website or landing page with zero external dependencies:
```html
<script 
  src="http://localhost:8000/v1/integrations/extension/bundle" 
  data-tenant="YOUR_TENANT_ID" 
  data-key="YOUR_API_KEY" 
  data-title="Knowledge Assistant"
  data-color="#2563eb">
</script>
```

### 4. 🤖 AI Agent MCP Integration (Cursor / Windsurf / Claude)
Connect your AI coding assistant directly to Retriever's hybrid search and document ingestion tools:
```json
{
  "mcpServers": {
    "retriever": {
      "command": "npx",
      "args": ["-y", "@prat3010/retriever-mcp"]
    }
  }
}
```

---

## 📦 Client SDKs

Integrate Retriever natively into your applications with official client SDKs:

### TypeScript / JavaScript (Node, Browser & Next.js)
```bash
npm install @prat3010/retriever-client
```
```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  baseUrl: "http://localhost:8000",
  apiKey: "YOUR_API_KEY",
  tenantId: "YOUR_TENANT_ID",
});

const results = await client.search("How does hybrid search fusion work?");
console.log(results);
```

### Python (Sync & Async)
```bash
pip install retriever-python
```
```python
from retriever import RetrieverClient

client = RetrieverClient(
    base_url="http://localhost:8000",
    api_key="YOUR_API_KEY",
    tenant_id="YOUR_TENANT_ID",
)

results = client.search("How does hybrid search fusion work?")
print(results.results[0].content)
```

---

## 🛡️ Architectural Principles

1. **The 30-Year PostgreSQL Foundation:** Rather than running fragile bespoke vector databases, Retriever is anchored on PostgreSQL 16 with `pgvector`—combining relational data, JSONB tenant configs, BM25 full-text search, and HNSW indexes within a single unified database.
2. **Model-Agnostic Hexagonal Boundaries:** The core domain layer (`src/domain/`) enforces strictly zero external vendor SDK imports. Swapping from local Ollama to OpenAI, Anthropic, or Groq requires editing a single adapter without altering domain logic.
3. **Local-First Economics:** Embeddings default to local Ollama (`nomic-embed-text`). You can run millions of vector operations per month with $0 external API bills.
4. **Standard Protocols:** In addition to clean REST and SSE endpoints, Retriever exposes tools via the Model Context Protocol (MCP) so AI agents can query your knowledge base natively.

---

## 📄 License

Apache 2.0 — Free for commercial and non-commercial use.
