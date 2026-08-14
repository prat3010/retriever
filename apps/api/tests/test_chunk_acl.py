"""Tests for Milestone 41: Chunk-Level Granular Access Control (ACL) & DB RLS Hardening."""


from src.adapters.vector.filter_builder import build_filter_clause
from src.domain.abstractions.ingestion import DocumentChunk
from src.domain.abstractions.retrieval import SearchQuery
from src.domain.retrieval.query_builder import build_search_query


def test_document_chunk_acl_fields() -> None:
    chunk = DocumentChunk(
        chunk_id="chk_1",
        document_id="doc_1",
        tenant_id="ten_1",
        content="Confidential financial report",
        token_count=25,
        chunk_index=0,
        allowed_roles=["finance_admin", "cfo"],
        allowed_users=["usr_100"],
        created_at="2026-08-14T00:00:00Z",
    )
    assert chunk.allowed_roles == ["finance_admin", "cfo"]
    assert chunk.allowed_users == ["usr_100"]


def test_filter_builder_acl_clause_generation() -> None:
    sql, params, _ = build_filter_clause(
        filters=[],
        tags=[],
        chunk_alias="dc",
        user_id="usr_100",
        user_role="finance_admin",
    )
    assert "allowed_users" in sql
    assert "allowed_roles" in sql
    assert params["acl_user_id"] == "usr_100"
    assert params["acl_user_role"] == "finance_admin"


def test_filter_builder_acl_clause_empty_user_context() -> None:
    sql, params, _ = build_filter_clause(
        filters=[],
        tags=[],
        chunk_alias="dc",
        user_id=None,
        user_role=None,
    )
    assert sql == ""
    assert params == {}



def test_search_query_user_context() -> None:
    query = SearchQuery(
        query="q",
        tenant_id="ten_1",
        user_id="usr_100",
        user_role="admin",
    )
    assert query.user_id == "usr_100"
    assert query.user_role == "admin"


class MockPayload:
    def __init__(self, query: str) -> None:
        self.query = query
        self.filters = []
        self.tags = []


def test_query_builder_attaches_user_context() -> None:
    class MockConfig:
        class RetrievalSettings:
            top_k = 10
            rrf_k = 60
            reranking_threshold = 0.7
            rerank_candidate_multiplier = 5
            enable_web_search = False
            web_search_provider = "tavily"
            web_search_api_key = None
            web_search_threshold = 0.65
            web_search_max_results = 5

        class FeatureFlags:
            enable_hybrid_search = True
            enable_reranking = False
            enable_query_rewriting = False
            enable_web_search = False
            enable_self_query = False
            enable_query_intent = False

        class BM25Settings:
            enable_bm25 = False

        class MMRSettings:
            enable_mmr = False

        retrieval_settings = RetrievalSettings()
        feature_flags = FeatureFlags()
        bm25_settings = BM25Settings()
        mmr_settings = MMRSettings()

    payload = MockPayload("test query")
    sq = build_search_query(
        tenantId="ten_1",
        tenant_config=MockConfig(),
        payload=payload,
        user_id="usr_123",
        user_role="legal_counsel",
    )
    assert sq.user_id == "usr_123"
    assert sq.user_role == "legal_counsel"
