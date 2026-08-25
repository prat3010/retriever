---
id: DeepDive_Evaluation_Hallucinations
title: "Cognitive Deep-Dive: Online Faithfulness Benchmarking, RAGAS & DeepEval Testbeds"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/evaluation
  - cognitive/ragas
  - cognitive/deepeval
  - cognitive/faithfulness
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Online faithfulness evaluations MUST run asynchronously via Celery worker to avoid blocking SSE latency."
---

# Cognitive Deep-Dive: Online Faithfulness Benchmarking, RAGAS & DeepEval Testbeds

#cognitive #evaluation #ragas #deepeval #faithfulness #hallucinations #benchmarks #retriever

> **Technical architecture, online evaluation metrics, automated benchmark testbeds, and offline regression suites in Retriever.**

---

## 1. Online vs Offline Evaluation Flow

```mermaid
flowchart TD
    subgraph Online Production Path (Async Celery)
        LiveChat[User Chat Query & Streamed Answer] --> Trace[Inference Log & Context Chunks]
        Trace --> CeleryEval[Celery Worker: evaluation.run]
        CeleryEval --> Metric1[Faithfulness Score (0.0–1.0)]
        CeleryEval --> Metric2[Context Precision & Recall]
        CeleryEval --> Metric3[Answer Relevance Score]
        Metric1 & Metric2 & Metric3 --> Dashboard[(Admin Eval Dashboard)]
    end

    subgraph Offline CI/CD Regression Testbed
        GoldSet[(Golden Benchmark Dataset: 500 Q&A Pairs)] --> TestRunner[RAGAS / DeepEval Test Runner]
        TestRunner --> ReleaseGate{Score >= 0.88 Threshold?}
        ReleaseGate -->|Pass| Deploy[Deploy Canary Release]
        ReleaseGate -->|Fail| Alert[Block PR & Alert Engineers]
    end
```

---

## 2. Core RAG Metrics Formulation

### 2.1 Faithfulness
Measures factual consistency of the generated response against retrieved context chunks:

\[
\text{Faithfulness} = \frac{|\text{Verifiable Claims in Answer Grounded in Context}|}{|\text{Total Number of Claims in Answer}|}
\]

### 2.2 Context Relevance
Measures signal-to-noise ratio in retrieved context passages:

\[
\text{Context Relevance} = \frac{|\text{Sentence Chunks Relevant to Query}|}{|\text{Total Sentence Chunks Retrieved}|}
\]

---

## 🔗 Related Architecture & Cross-References
- [Master Admin Gateway Specification](../api/admin.md)
- [Multi-Agent Consensus & Reflection](consensus_and_reflection.md)
- [Async Workers & Queues](../infrastructure/async_workers_and_queues.md)
