"""Golden Benchmark Evaluation Dataset (2026 Standards).

A verified golden test suite for automated RAG regression testing across multi-domain
enterprise tasks: security, financial terms, architecture, and SLAs.
Conforms strictly to Hexagonal Architecture boundaries.
"""

from pydantic import BaseModel, Field


class GoldenEvalItem(BaseModel):
    """A verified golden benchmark evaluation question with contexts and ground truth."""

    question_id: str
    domain: str
    question: str
    ground_truth_answer: str
    key_facts: list[str] = Field(default_factory=list)
    golden_contexts: list[str] = Field(default_factory=list)
    distractor_contexts: list[str] = Field(default_factory=list)
    relevant_chunk_ids: list[str] = Field(default_factory=list)


GOLDEN_BENCHMARK_DATASET: list[GoldenEvalItem] = [
    GoldenEvalItem(
        question_id="gold_sec_001",
        domain="security",
        question="How does Retriever enforce multi-tenant vector isolation at the database layer?",
        ground_truth_answer="Retriever enforces multi-tenant vector isolation using PostgreSQL Row-Level Security (RLS) on all vector tables. Database sessions set the current tenant_id via tenant_session, preventing cross-tenant data leakage.",
        key_facts=[
            "Retriever uses PostgreSQL Row-Level Security (RLS)",
            "Sessions set current tenant_id via tenant_session",
            "Prevents cross-tenant data leakage",
        ],
        golden_contexts=[
            "Retriever enforces strict multi-tenancy isolation using PostgreSQL Row-Level Security (RLS). Every query execution runs inside tenant_session which binds the tenant_id to the database connection.",
            "All vector tables (vector_records, vector_records_1024, vector_records_1536) enforce RLS policies preventing cross-tenant leakage.",
        ],
        distractor_contexts=[
            "The web dashboard is built using Next.js 16 with Tailwind CSS.",
            "Redis cache stores API key rate limit quotas for 60 seconds.",
        ],
        relevant_chunk_ids=["chunk_sec_01", "chunk_sec_02"],
    ),
    GoldenEvalItem(
        question_id="gold_fin_002",
        domain="finance",
        question="What are the invoice payment terms and late penalty fees?",
        ground_truth_answer="Invoices are due within Net 30 days from issuance. Payments delayed beyond 30 days incur a 1.5% monthly late fee.",
        key_facts=[
            "Payment due within Net 30 days",
            "Late fee is 1.5% monthly",
        ],
        golden_contexts=[
            "Standard commercial invoices carry Net 30 payment terms from date of invoice issuance.",
            "Any overdue balances exceeding 30 calendar days incur a statutory finance fee of 1.5% per month until settled.",
        ],
        distractor_contexts=[
            "Customers can pay via credit card, wire transfer, or ACH.",
            "The billing currency can be set to USD or INR based on tenant region.",
        ],
        relevant_chunk_ids=["chunk_fin_01", "chunk_fin_02"],
    ),
    GoldenEvalItem(
        question_id="gold_sla_003",
        domain="sla",
        question="What is the guaranteed uptime SLA and p95 latency budget for search queries?",
        ground_truth_answer="The production search API guarantees 99.95% uptime availability with a p95 query latency budget under 250 milliseconds.",
        key_facts=[
            "99.95% uptime availability SLA",
            "p95 query latency budget under 250ms",
        ],
        golden_contexts=[
            "The production enterprise tier guarantees 99.95% monthly uptime SLA for all search API endpoints.",
            "Hybrid dense-sparse search queries are engineered to execute within a p95 latency budget of 250ms under peak load.",
        ],
        distractor_contexts=[
            "Documents can be ingested asynchronously via Celery worker queues.",
            "Document storage supports local disk or S3 compatible object storage.",
        ],
        relevant_chunk_ids=["chunk_sla_01", "chunk_sla_02"],
    ),
    GoldenEvalItem(
        question_id="gold_arch_004",
        domain="architecture",
        question="Which retrieval algorithms form Retriever's hybrid search fusion pipeline?",
        ground_truth_answer="Retriever's hybrid search combines HNSW dense vector search, BM25 sparse keyword search, and reciprocal rank fusion (RRF) with optional ColBERT MaxSim reranking.",
        key_facts=[
            "HNSW dense vector search",
            "BM25 sparse keyword search",
            "Reciprocal rank fusion (RRF)",
            "ColBERT MaxSim reranking",
        ],
        golden_contexts=[
            "The hybrid search engine fuses HNSW pgvector similarity scores with BM25 lexical keyword matching using Reciprocal Rank Fusion (RRF).",
            "Top-k candidate documents from RRF are reranked using a ColBERT MaxSim late-interaction cross-encoder model for optimal semantic precision.",
        ],
        distractor_contexts=[
            "Docker compose configures PostgreSQL with pgvector extension pre-installed.",
            "Prometheus metrics track total requests and error rates.",
        ],
        relevant_chunk_ids=["chunk_arch_01", "chunk_arch_02"],
    ),
    GoldenEvalItem(
        question_id="gold_ingest_005",
        domain="ingestion",
        question="How does layout-aware chunking prevent table fragmentation?",
        ground_truth_answer="Layout-aware chunking preserves tables as atomic semantic units within token limits. When tables exceed chunk boundaries, it partitions along row boundaries and repeats table headers in every continuation chunk.",
        key_facts=[
            "Preserves tables as atomic semantic units",
            "Partitions oversized tables along row boundaries",
            "Repeats table headers in every continuation chunk",
        ],
        golden_contexts=[
            "The LayoutAwareChunker detects markdown tables and preserves them as atomic blocks within chunk limits.",
            "For tables exceeding chunk size, it splits rows while re-injecting the header and delimiter line into each continuation chunk to preserve column context.",
        ],
        distractor_contexts=[
            "PDF layout parsing uses pdfplumber to extract table bounding boxes.",
            "Source code is parsed using Python AST and treesitter.",
        ],
        relevant_chunk_ids=["chunk_ingest_01", "chunk_ingest_02"],
    ),
]
