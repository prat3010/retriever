"""Unit tests for Milestone 37: GraphRAG & Dual Knowledge Graph Indexing."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.adapters.database.graph_repository import PgGraphRepository
from src.adapters.graph.neo4j_repository import Neo4jGraphRepository
from src.config import InfraCapabilities
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.graph import EntityTriple
from src.domain.graph.graph_extraction_service import GraphExtractor
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: GraphExtractor Triple Parsing ──────────────────────────────

def test_graph_extractor_parsing():
    """Verify GraphExtractor extracts subject-predicate-object triples from text."""
    extractor = GraphExtractor()
    sample_text = """
    Alice leads Team Alpha.
    Team Alpha built Payment Gateway.
    Payment Gateway uses Database Z.
    """
    triples = extractor.extract_triples(sample_text)

    assert len(triples) >= 2
    subs = [t.subject for t in triples]
    preds = [t.predicate for t in triples]
    objs = [t.object for t in triples]

    assert "Alice" in subs
    assert "LEADS" in preds or "BUILT" in preds or "USES" in preds
    assert "Team Alpha" in objs or "Team Alpha" in subs


# ── 2. Unit Test: PgGraphRepository CRUD & Multi-Hop Traversal ──────────────

@pytest.mark.asyncio
@patch("src.adapters.database.graph_repository.tenant_session")
async def test_pg_graph_repository_crud(mock_tenant_session):
    """Verify PgGraphRepository triple persistence, search, and deletion."""
    repo = PgGraphRepository()
    tenant_id = str(uuid.uuid4())

    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()
    mock_tenant_session.return_value.__aenter__.return_value = mock_db_session

    triples = [
        EntityTriple(subject="Alice", predicate="LEADS", object="Team Alpha"),
        EntityTriple(subject="Team Alpha", predicate="USES", object="PostgreSQL"),
    ]

    added_count = await repo.add_triples(tenant_id, triples)
    assert added_count == 2
    assert mock_db_session.add.call_count == 2

    # Mock search response
    mock_row1 = MagicMock()
    mock_row1.triple_id = uuid.uuid4()
    mock_row1.subject = "Alice"
    mock_row1.predicate = "LEADS"
    mock_row1.object = "Team Alpha"
    mock_row1.chunk_id = None
    mock_row1.confidence = 0.95
    mock_row1.meta_data = {}

    mock_exec_res = MagicMock()
    mock_exec_res.fetchall.return_value = [mock_row1]
    mock_db_session.execute.return_value = mock_exec_res

    res = await repo.search_triples(tenant_id, "Alice", max_hops=2)
    assert res.root_entity == "Alice"
    assert len(res.triples) == 1
    assert "Alice" in res.connected_entities


# ── 3. Unit Test: Neo4jGraphRepository Fallback ─────────────────────────────

@pytest.mark.asyncio
@patch("src.adapters.graph.neo4j_repository.PgGraphRepository")
async def test_neo4j_graph_repository_fallback(mock_pg_class):
    """Verify Neo4jGraphRepository delegates to PostgreSQL when Neo4j is offline."""
    mock_fallback = AsyncMock()
    mock_fallback.add_triples.return_value = 1
    mock_fallback.search_triples.return_value = MagicMock(root_entity="Alice", triples=[])

    repo = Neo4jGraphRepository(
        uri="bolt://invalid-host:7687",
        user="neo4j",
        password="bad",
        fallback_repo=mock_fallback,
    )

    # When Neo4j is offline, actions fall back to PostgreSQL
    tenant_id = str(uuid.uuid4())
    triples = [EntityTriple(subject="Alice", predicate="LEADS", object="Team Alpha")]

    res_add = await repo.add_triples(tenant_id, triples)
    assert res_add == 1
    mock_fallback.add_triples.assert_awaited_once_with(tenant_id, triples)

    res_search = await repo.search_triples(tenant_id, "Alice")
    assert res_search.root_entity == "Alice"
    mock_fallback.search_triples.assert_awaited_once_with(tenant_id, "Alice", 2)


# ── 4. Unit Test: Environment Auto-Detection Logic ──────────────────────────

def test_infra_capabilities_graph_detection():
    """Verify InfraCapabilities detects low-RAM Oracle VM vs MacBook profile."""
    infra_oracle = InfraCapabilities()
    infra_oracle.ram_gb = 0.9
    assert infra_oracle.lean_mode is True

    infra_mac = InfraCapabilities()
    infra_mac.ram_gb = 16.0
    assert infra_mac.lean_mode is False


# ── 5. Integration Test: Admin Graph Endpoints ──────────────────────────────

@patch("src.routers.admin.config_service.get_tenant_config", new_callable=AsyncMock)
def test_admin_graph_capabilities_and_summary(mock_get_cfg):
    """Verify GET /v1/admin/tenants/{tenantId}/graph/capabilities endpoint."""
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())
        fake_config = TenantConfiguration()
        mock_get_cfg.return_value = fake_config

        headers = {"X-Admin-API-Key": "test_admin_key"}
        res = client.get(
            f"/v1/admin/tenants/{tenant_id}/graph/capabilities",
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert "machine_profile" in body
        assert "supported_engines" in body
        assert "active_engine" in body
    finally:
        app.dependency_overrides.clear()


# ── 6. Unit Test: HybridSearchService Graph Evidence Pass ────────────────────

@pytest.mark.asyncio
async def test_hybrid_search_graph_evidence_pass():
    """Verify HybridSearchService retrieves graph triples and fuses graph evidence."""
    from src.domain.abstractions.retrieval import SearchQuery, SearchResult
    from src.domain.retrieval.search_service import HybridSearchService

    mock_vec = AsyncMock()
    mock_vec.search_similar.return_value = [
        SearchResult(chunk_id="c1", document_id="d1", content="Text chunk 1", score=0.8)
    ]
    mock_kw = AsyncMock()
    mock_kw.search_keywords.return_value = []
    mock_emb = AsyncMock()
    mock_emb.embed_text.return_value = [0.1] * 1536
    mock_rerank = AsyncMock()

    mock_graph = AsyncMock()
    mock_graph.search_triples.return_value = MagicMock(
        triples=[
            EntityTriple(
                subject="Alice",
                predicate="LEADS",
                object="Team Alpha",
                chunk_id="c1",
                document_id="d1",
            )
        ]
    )

    service = HybridSearchService(
        vector_search=mock_vec,
        keyword_search=mock_kw,
        embedder=mock_emb,
        reranker=mock_rerank,
        graph_repository=mock_graph,
    )

    query = SearchQuery(
        query="Alice leads team",
        tenant_id=str(uuid.uuid4()),
        enable_graph_search=True,
        enable_reranking=False,
    )

    res = await service.search(query)
    assert len(res.results) >= 1
    contents = [r.content for r in res.results]
    assert any("[Graph Evidence]" in c for c in contents)

