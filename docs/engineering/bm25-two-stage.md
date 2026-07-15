# BM25 Two-Stage Search Architecture

## Rationale

Postgres `ts_rank` (used previously) produces unbounded, non-comparable scores.
BM25 is the standard IR ranking function with well-understood behavior.

A pure-PL/pgSQL BM25 implementation requires global term-frequency stats tables,
triggers on every chunk insert/update/delete, and periodic avgdl maintenance — a
significant infra cost for exact BM25.

**Decision**: Use a two-stage pipeline that keeps both approaches in the codebase:

1. `ts_rank_cd` (fast, DB-side) for Stage 1 candidate retrieval
2. In-app pure-Python BM25 for Stage 2 precise re-ranking

## Pipeline

```
[Query]
   │
   ▼  (Stage 1: ts_rank_cd in SQL)       keyword_repository.py
[Top-K candidates from keyword leg]
   │
   ▼  (RRF fusion with vector leg)       search_service.py
[Fused candidates]
   │
   ▼  (Stage 2: in-app BM25)             bm25_reranker.py
[BM25 re-scored]
   │
   ▼  (Cohere cross-encoder reranker)    reranker_adapter.py
[Final results]
```

Both BM25 and Cohere reranking are optional, controlled by per-tenant config.

## Two-Stage Detail

### Stage 1 — `ts_rank_cd` (keyword_repository.py:36)

```sql
ts_rank_cd(
    to_tsvector('english', dc.content),
    websearch_to_tsquery('english', :query),
    2  -- normalization: divide by document length
) AS rank_score
```

Replaces the old `ts_rank()` which had no length normalization. The third
argument `2` normalizes by document length, producing scores comparable across
documents — closer to BM25 behavior at the SQL level.

### Stage 2 — In-app BM25 (domain/retrieval/bm25_reranker.py)

Pure Python BM25 implementation. Key design:

| Component | Approach |
|-----------|----------|
| Term frequency | Simple word split + count (re.findall on content text) |
| Document length | Word count of content text |
| IDF | Local IDF computed from the candidate set (N = candidate pool size) |
| Formula | Standard BM25: `Σ IDF(q_i) * (f(q_i,d) * (k1+1)) / (f(q_i,d) + k1 * (1-b + b*|d|/avgdl))` |
| Default k1 | 1.5 |
| Default b | 0.75 |

**Local IDF** means IDF is computed from only the retrieved candidates, not the
entire corpus. This is a well-known re-ranking technique and avoids the need for
global term frequency tables. It works correctly because:

- For re-ranking, only relative ordering among candidates matters
- Query terms absent from the candidate set get IDF=0 (no contribution)
- Terms appearing in all candidates get low IDF (close to 0)

## Config

Per-tenant BM25Settings in TenantConfiguration:

```python
class BM25Settings(BaseModel):
    enable_bm25: bool = True   # Enable/disable BM25 Stage 2
    k1: float = 1.5            # Term frequency saturation
    b: float = 0.75            # Length normalization (0 = no normalization, 1 = full)
```

Stage 1 (ts_rank_cd) is always on — it's the default keyword ranking function.

## When to Tune

- **k1**: Lower (1.0-1.2) for precision-oriented search, higher (1.5-2.0) for recall
- **b**: Lower (0.3-0.5) for collections where document length varies widely,
  higher (0.75-1.0) for uniform-length documents
- **Defaults** (k1=1.5, b=0.75) are standard TREC values and work well in practice

## Files

- `apps/api/src/adapters/vector/keyword_repository.py` — Stage 1 (ts_rank_cd)
- `apps/api/src/domain/retrieval/bm25_reranker.py` — Stage 2 (in-app BM25)
- `apps/api/src/domain/retrieval/search_service.py` — Pipeline wiring
- `apps/api/src/domain/abstractions/config.py` — BM25Settings per-tenant config

## Future

If the in-app BM25 becomes a bottleneck (>1000 candidates), consider:
1. Parallel BM25 scoring with ProcessPoolExecutor
2. Pre-computing and caching IDF values in Redis
3. Full PL/pgSQL BM25 with stats tables for global IDF
