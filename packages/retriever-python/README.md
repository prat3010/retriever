# retriever-python

Official Python Client SDK for **Retriever Enterprise Cognitive Engine** (`v1.0.0-rc1`).

[![PyPI version](https://img.shields.io/pypi/v/retriever-python.svg)](https://pypi.org/project/retriever-python/)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![Batteries](https://img.shields.io/badge/batteries-26%20included-ff69b4.svg)](#-26-platform-batteries)

---

## 📦 Installation

```bash
pip install retriever-python
```

---

## ⚡ Quick Start

```python
from retriever import RetrieverClient

client = RetrieverClient(
    base_url="http://localhost:8000",
    api_key="ret_live_demo_00000000000000000000000000000000",
    tenant_id="00000000-0000-0000-0000-000000000001", # Demo Workspace
)

# 1. Hybrid Search (HNSW Dense + BM25 Lexical + ColBERT MaxSim)
response = client.search(
    query="How does ColBERT late interaction work?",
    limit=5,
    enable_colbert_rerank=True,
)

print(f"Found {response.total} results in {response.latency_ms:.2f}ms:")
for chunk in response.results:
    print(f"- [{chunk.score:.3f}] {chunk.content[:100]}...")
```

---

## 🔄 Autonomous Multi-Turn ReAct Chat Loop

Stream real-time agent reasoning steps, tool activations, and token emissions:

```python
session_id = "session-test-uuid"

for event in client.chat_stream(session_id, "Analyze memory retention and verify database schema"):
    if event.type == "thought":
        print(f"🤔 [Thought]: {event.content}")
    elif event.type == "tool_call_start":
        print(f"⚡ [Tool Call]: {event.tool_name}({event.arguments})")
    elif event.type == "tool_call_done":
        print(f"✅ [Tool Result]: Step {event.step}")
    elif event.type == "token":
        print(event.content, end="", flush=True)
```

---

## 🚀 Asynchronous Client Support

```python
import asyncio
from retriever import AsyncRetrieverClient

async def main():
    async with AsyncRetrieverClient(
        base_url="http://localhost:8000",
        api_key="ret_live_demo_00000000000000000000000000000000",
        tenant_id="00000000-0000-0000-0000-000000000001",
    ) as client:
        # Asynchronous search
        results = await client.search("scale-to-zero vLLM compute")
        print(f"Async search returned {len(results.results)} chunks.")

        # Asynchronous Swarm Quorum Debate
        debate = await client.swarm_debate(
            task="Evaluate PostgreSQL vs ClickHouse for petabyte telemetry",
            roles=["planner", "auditor", "synthesizer", "skeptic"],
        )
        print(f"Consensus Confidence: {debate.quorum_confidence * 100:.1f}%")
        print(debate.consensus_response)

asyncio.run(main())
```

---

## 🔋 26 Platform Batteries Supported

- **Batteries 1–3**: Dense HNSW, Sparse BM25, and ColBERT MaxSim late interaction.
- **Battery 4**: Docling Vision Layout OCR & markdown table parsing.
- **Battery 5**: Recursive Language Model (RLM) Python REPL execution.
- **Battery 21**: Zero-Trust Micro-Enclave KMS Remote Attestation.
- **Battery 23**: Universal Model Context Protocol (MCP) JSON-RPC tool gateway.
- **Battery 24**: Autonomous cyclic ReAct tool loop with self-healing error recovery.
- **Battery 25**: Cognitive Agent Memory with mathematical Ebbinghaus retention decay.
- **Battery 26**: Multi-Agent Swarm Quorum with dialectic debate DAG and hallucination pruning.

---

## 📄 License

Apache-2.0. Maintained by [Prateek Sharma](https://github.com/prat3010).
