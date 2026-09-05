# LongLLMLingua Context Compression & Token Surprise Pruning

**Milestone:** M85.2 (v0.70.2)  
**System Layer:** Context Window Optimization & Cost Reduction (Platform Battery #13)  
**Architecture:** LongLLMLingua Information Entropy Scoring + Perplexity Surprise Pruning + Query-Aware Context Re-Ordering  

---

## 1. Executive Summary

Milestone 85.2 establishes **Platform Battery #13: `longllmlingua_compression`**, slashing prompt token costs by 50%–70% while improving LLM reasoning fidelity.

As enterprise RAG pipelines retrieve 10 to 30 document chunks per user query, context windows balloon to 8,000–32,000+ tokens. This causes two major operational and cognitive failures:
1. **Exponential Token Costs:** Feeding massive uncompressed context windows to high-capability reasoning models (e.g. Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro) dramatically increases per-query operational expense.
2. **"Lost in the Middle" Degradation:** Extensive research demonstrates that frontier LLMs struggle to recall facts placed in the middle of long contexts, frequently hallucinating or missing key evidence located between tokens 2,000 and 10,000.

Platform Battery #13 deploys the LongLLMLingua algorithm: a small, ultra-fast language model (e.g. Llama-3.2-1B or Qwen-2.5-0.5B) calculates token perplexity and conditional surprise given the user's query. Low-information tokens (boilerplate, repetitive formatting, stopwords) are pruned away, compressing the context by 2x–3x while preserving crucial reasoning tokens, entities, and numbers.

---

## 2. Mathematical Foundation & Information Entropy Pruning

Given a query $q$ and a document token sequence $X = (x_1, x_2, \dots, x_N)$, the conditional surprise (information content) of token $x_i$ is its negative log-likelihood:

$$I(x_i | x_{<i}, q) = - \log P(x_i | x_{<i}, q)$$

- **Low Information ($I \to 0$):** Predictable tokens (e.g. "is", "the", "according to", recurring legal headers). Pruning them causes minimal information loss.
- **High Information ($I \gg 0$):** Surprising tokens (domain-specific entity names, exact dates, monetary amounts, metric values). Retaining them preserves core semantic truth.

```text
       Original Document Tokens (Uncompressed):
       [ "In", "accordance", "with", "Section", "4.2", "the", "reimbursement", "rate", "is", "18.5%", "per", "quarter" ]
          │          │          │        │       │      │         │           │      │     │      │        │
          ▼          ▼          ▼        ▼       ▼      ▼         ▼           ▼      ▼     ▼      ▼        ▼
       (Low I)    (Low I)    (Low I)  (High I)(High I)(Low I)  (High I)    (High I)(Low I)(High I)(Low I) (High I)
       
       LongLLMLingua Pruned Context (50% Budget):
       [ "Section", "4.2", "reimbursement", "rate", "18.5%", "quarter" ]
```

### Query-Aware Dynamic Budgeting
LongLLMLingua dynamically allocates compression budgets across document chunks: chunks with higher query-conditioned mutual information receive larger token budgets, while weakly related background chunks are aggressively compressed or discarded.

---

## 3. System Architecture & Compression Flow

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     LONGLLMLINGUA COMPRESSION PIPELINE                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Retrieved Document Chunks (e.g. 20 chunks = 8,000 tokens) ]                        │
│                         │                                                              │
│                         ▼                                                              │
│            ┌───────────────────────────┐                                               │
│            │ Query-Document Condition  │ ── Evaluates P(Chunk | Query)                 │
│            └────────────┬──────────────┘                                               │
│                         │                                                              │
│                         ▼                                                              │
│            ┌───────────────────────────┐                                               │
│            │ Token Perplexity Evaluator│ ── Calculates Conditional Surprise (SLM)      │
│            └────────────┬──────────────┘                                               │
│                         │                                                              │
│                         ▼                                                              │
│            ┌───────────────────────────┐                                               │
│            │ Dynamic Budget Allocator  │ ── Target Ratio: 0.50 (Slashing 50% tokens)   │
│            └────────────┬──────────────┘                                               │
│                         │                                                              │
│                         ▼                                                              │
│            ┌───────────────────────────┐                                               │
│            │ Context Re-orderer        │ ── Puts highest-density facts at edges to     │
│            │ (Mitigate Lost-in-Middle) │    maximize attention retention               │
│            └────────────┬──────────────┘                                               │
│                         │                                                              │
│                         ▼                                                              │
│   [ Compressed Prompt (4,000 tokens) ──► Forwarded to Frontier Reasoning LLM ]         │
│   (50% Token Cost Reduction, ~45ms Latency Overhead, Higher Recall Fidelity)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/cognitive/context_compressor_adapter.py`
- **Active Parameters:**
  - `compression_target_ratio`: 0.50
  - `min_retained_tokens`: 150
  - `condition_in_the_middle`: True
- **Latency Profile:** $\sim 45\text{ms}$ compression evaluation.
- **Health Check Endpoint:** `GET /v1/cognitive/compress/status`

---

## 5. Non-Negotiable Invariants

1. **Entity & Number Protection:** Named entities, currency symbols, and numerical values are explicitly shielded from pruning heuristics to prevent factual distortion.
2. **Min-Token Floor:** Chunks are never pruned below `min_retained_tokens` (150 tokens) unless explicitly marked for complete deletion.
3. **Transparent Compression Header:** Compressed outputs injected into the prompt are accompanied by metadata headers indicating original vs. compressed token counts.
