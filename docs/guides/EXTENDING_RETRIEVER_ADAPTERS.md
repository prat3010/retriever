# Extending & Customizing Retriever: Hexagonal Architecture Guide

Retriever is intentionally engineered with a **Strict Hexagonal Architecture (Ports and Adapters)**. This means the core cognitive domain logic (multi-tenancy RLS, GraphRAG community clustering, hybrid fusion search, sliding-window token shields, citation tracking, and DSPy optimization) is **100% decoupled** from external infrastructure, databases, third-party libraries, and AI vendor SDKs.

If you or your enterprise team wants to modify, swap, or extend any component—such as replacing PostgreSQL pgvector with Qdrant, plugging in an on-premises proprietary LLM, writing custom legal chunkers, or implementing bespoke PII guardrails—you can do so with **zero modifications to the core business logic**.

---

## 🏛️ The Hexagonal Extensibility Model

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      Core Domain Layer                      │
 │    (src/domain/abstractions/ - Pure Interfaces/Protocols)   │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Implements Port
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                      Adapters Layer                         │
 │     (src/adapters/ - Concrete Tech Implementations)         │
 │   - Existing: pgvector_adapter.py, ollama_adapter.py        │
 │   - User Custom: qdrant_adapter.py, custom_llm_adapter.py   │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Injected by Container
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                 Container (src/container.py)                │
 │    Reads env var / config & injects the chosen adapter      │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Exposes
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     API Routers & Workers                   │
 │           (FastAPI REST, WebSockets, Celery/Redis)          │
 └─────────────────────────────────────────────────────────────┘
```

### The Invariant Guarantee:
When you swap or extend an adapter:
1. **Zero Core Rewrites:** You never need to touch `src/domain/`.
2. **Battery Preservation:** All 38 production batteries (caching, evaluation benchmarks, hybrid reranking, citation verification) continue to work out of the box.
3. **Future-Proof Upgrades:** When you pull updates from upstream Retriever, your custom adapters remain completely isolated and intact.

---

## ⚙️ Level 1: Zero-Code Configuration Swapping

For 90% of use cases, you do not need to write any Python code at all. Retriever provides pluggable configuration via environment variables:

| Component | Default | Alternatives | Configuration |
| :--- | :--- | :--- | :--- |
| **Embeddings** | Local Ollama (`nomic-embed-text`) | HuggingFace TEI (`BAAI/bge-base-en-v1.5`) | `EMBEDDING_PROVIDER="hf"` |
| **Document Storage** | Local Disk (`./storage`) | AWS S3, Cloudflare R2, MinIO | `STORAGE_PROVIDER="s3"` |
| **Chat / LLM** | Local Ollama (`llama3.2` / `qwen2.5`) | OpenAI, Gemini, Anthropic, Groq, Mistral | `OPENAI_API_KEY`, `GEMINI_API_KEY`, etc. |
| **Knowledge Graph** | PostgreSQL (`pg_graph`) | Neo4j Enterprise Cluster | `GRAPH_ENGINE="neo4j"` |
| **Sparse Lexical** | SQLite / BM25 Okapi | PostgreSQL full-text search | `SPARSE_SEARCH_PROVIDER="bm25"` |

---

## 🛠️ Level 2: The 3-Step Hexagonal Extension Pattern

When you want to integrate new technology (e.g. Qdrant, Pinecone, or a proprietary internal LLM server), follow this standardized 3-step workflow:

### Step 1: Inspect the Abstract Port
Every extensible component in Retriever implements an abstract interface under `src/domain/abstractions/`:
- **Vector Storage:** `src/domain/abstractions/vector.py` (`VectorRepository`)
- **LLM Provider:** `src/domain/abstractions/inference.py` (`LlmProvider`)
- **Embedding Provider:** `src/domain/abstractions/embeddings.py` (`EmbeddingProvider`)
- **Document Parser / Chunker:** `src/domain/abstractions/document.py` (`DocumentParser`)
- **Security & Guardrails:** `src/domain/abstractions/guardrails.py` (`SafetyGuardPort`)

### Step 2: Implement Your Adapter
Create a new file under `src/adapters/<category>/my_custom_adapter.py` that inherits from the port and fulfills its contract.

### Step 3: Register in Dependency Injection Container (`src/container.py`)
Add your adapter instantiation in `src/container.py`, keyed by a configuration flag or environment variable.

---

## 📖 Practical Customization Recipes

---

### Recipe 1: Adding a Custom Vector Store Adapter (e.g., Qdrant)

#### Step 1: Create `src/adapters/vector/qdrant_adapter.py`
```python
"""Qdrant Vector Database Adapter for Retriever."""
from typing import Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.domain.abstractions.vector import (
    VectorRepository,
    VectorSearchQuery,
    VectorSearchResult,
)

class QdrantVectorAdapter(VectorRepository):
    def __init__(self, url: str = "http://localhost:6333", api_key: str | None = None):
        self.client = AsyncQdrantClient(url=url, api_key=api_key)
        self.collection_name = "retriever_vectors"

    async def initialize(self) -> None:
        """Create collection if not present."""
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)
        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

    async def upsert_vector(
        self,
        tenant_id: str,
        chunk_id: str,
        document_id: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Upsert vector with strict tenant_id isolation in payload."""
        payload = {
            **metadata,
            "tenant_id": str(tenant_id),
            "document_id": str(document_id),
            "chunk_id": str(chunk_id),
        }
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=str(chunk_id),
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    async def search(self, query: VectorSearchQuery) -> list[VectorSearchResult]:
        """Execute vector similarity search strictly scoped by tenant_id."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Enforce multi-tenancy filter
        tenant_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=str(query.tenant_id)),
                )
            ]
        )

        response = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query.vector,
            query_filter=tenant_filter,
            limit=query.limit,
            score_threshold=query.min_similarity,
        )

        return [
            VectorSearchResult(
                chunk_id=hit.payload["chunk_id"],
                document_id=hit.payload["document_id"],
                score=hit.score,
                metadata=hit.payload,
            )
            for hit in response
        ]
```

#### Step 2: Register in `src/container.py`
```python
# In src/container.py
if getattr(settings, "VECTOR_PROVIDER", "postgres") == "qdrant":
    from src.adapters.vector.qdrant_adapter import QdrantVectorAdapter
    self._cache["vector_repo"] = QdrantVectorAdapter(
        url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        api_key=os.environ.get("QDRANT_API_KEY"),
    )
```

---

### Recipe 2: Connecting a Proprietary Enterprise On-Prem LLM

If your enterprise hosts an internal vLLM, TGI, or bespoke REST model endpoint:

#### Step 1: Create `src/adapters/cognitive/enterprise_llm_adapter.py`
```python
"""Custom Enterprise Internal LLM Adapter."""
import httpx
from typing import Any
from src.domain.abstractions.inference import (
    LlmProvider,
    InferenceRequest,
    InferenceResponse,
    Usage,
)

class EnterpriseLLMAdapter(LlmProvider):
    def __init__(self, endpoint_url: str, auth_token: str):
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        """Call enterprise proprietary model API."""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": "\n".join(f"{m.role}: {m.content}" for m in request.messages),
            "max_tokens": request.max_tokens or 1024,
            "temperature": request.temperature or 0.2,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.endpoint_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return InferenceResponse(
            content=data.get("generated_text", ""),
            usage=Usage(
                input_tokens=data.get("prompt_tokens", 0),
                output_tokens=data.get("completion_tokens", 0),
                total_tokens=data.get("total_tokens", 0),
            ),
            finish_reason="stop",
        )
```

---

### Recipe 3: Creating a Custom Legal / Financial Document Chunker

If standard recursive character chunkers break semantic boundaries in your industry-specific documents:

#### Step 1: Create `src/adapters/cognitive/legal_clause_chunker.py`
```python
"""Custom Legal Clause Chunker preserving Article and Clause headings."""
import re
from src.domain.abstractions.document import ChunkerPort, ChunkItem

class LegalClauseChunker(ChunkerPort):
    def chunk(self, text: str, document_id: str, tenant_id: str) -> list[ChunkItem]:
        # Split text on Section / Article / Clause boundaries
        clause_pattern = r"(?=(?:Section|Article|Clause)\s+\d+[\.:])"
        raw_sections = re.split(clause_pattern, text, flags=re.IGNORECASE)

        chunks: list[ChunkItem] = []
        for idx, section in enumerate(raw_sections):
            clean_text = section.strip()
            if not clean_text:
                continue
            chunks.append(
                ChunkItem(
                    document_id=document_id,
                    tenant_id=tenant_id,
                    sequence_order=idx,
                    content=clean_text,
                    metadata={"chunk_type": "legal_clause", "clause_index": idx},
                )
            )
        return chunks
```

---

### Recipe 4: Creating a Custom Compliance / PII Redaction Guardrail

If your regulatory environment requires blocking specific internal identifier patterns:

#### Step 1: Create `src/adapters/guardrails/enterprise_pii_guard.py`
```python
"""Enterprise PII and Secret Guardrail Adapter."""
import re
from src.domain.abstractions.guardrails import SafetyGuardPort, GuardrailResult

class EnterprisePIIGuardAdapter(SafetyGuardPort):
    def __init__(self):
        # Pattern for internal enterprise employee IDs: EMP-123456
        self.emp_id_pattern = re.compile(r"\bEMP-\d{6}\b", re.IGNORECASE)

    async def validate_input(self, text: str, tenant_id: str) -> GuardrailResult:
        """Sanitizes or blocks employee IDs from prompt leakage."""
        if self.emp_id_pattern.search(text):
            sanitized = self.emp_id_pattern.sub("[REDACTED_EMPLOYEE_ID]", text)
            return GuardrailResult(
                allowed=True,
                modified_text=sanitized,
                reason="Redacted internal employee ID before LLM dispatch.",
            )
        return GuardrailResult(allowed=True, modified_text=text)

    async def validate_output(self, text: str, tenant_id: str) -> GuardrailResult:
        """Enforces clean output without internal secret tokens."""
        return GuardrailResult(allowed=True, modified_text=text)
```

---

## 🧪 Testing Your Custom Adapter (Contract Testing)

Retriever enforces **Strict Contract Testing**. When you build a custom adapter, you can verify it using our standard test harness to prove it obeys all system invariants:

```bash
# Run the contract test suite on your new adapter
pytest apps/api/tests/test_architecture.py
pytest apps/api/tests/test_zero_toy_invariants.py
```

### Invariant Rules for Custom Adapters:
1. **Multi-Tenancy Isolation:** Every search, write, and delete MUST receive and filter by `tenant_id`. Never allow cross-tenant data leakage.
2. **Fail-Fast Transparency:** If your underlying service or API key is unavailable, raise `ProviderUnavailableError` or `HTTPException(503)`. **Never return fake synthetic mock data.**
3. **Async-Native:** All network I/O in adapters should use `async/await` to preserve high-throughput streaming concurrency.

---

## 🤝 Summary: Why Hexagonal Architecture Protects You

By keeping the domain clean and technology-neutral:
- You can **start free locally** with PostgreSQL pgvector + Ollama.
- You can **scale to enterprise multi-cloud** with Qdrant, S3, and vLLM clusters.
- You can **customize any component** in less than 50 lines of Python.
- Your custom code will **never break** across core platform upgrades.
