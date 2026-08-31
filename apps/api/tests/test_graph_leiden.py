"""Unit tests for Milestone 73: GraphRAG Leiden Community Detection."""


from src.domain.abstractions.graph import EntityTriple
from src.domain.graph.leiden_detector import LeidenCommunityDetector


def test_leiden_empty_triples():
    """Verify detector handles empty triple lists gracefully."""
    detector = LeidenCommunityDetector()
    hierarchy = detector.detect_communities("test-tenant", [])
    assert hierarchy.total_communities == 0
    assert hierarchy.levels == {}
    assert hierarchy.modularity_score == 0.0


def test_leiden_trivial_graph():
    """Verify detector handles 1-2 node graphs without error."""
    detector = LeidenCommunityDetector()
    triples = [
        EntityTriple(subject="FastAPI", predicate="USES", object="Python"),
    ]
    hierarchy = detector.detect_communities("test-tenant", triples)
    assert hierarchy.total_communities == 1
    assert 0 in hierarchy.levels
    assert len(hierarchy.levels[0]) == 1
    assert "FastAPI" in hierarchy.levels[0][0].entities
    assert "Python" in hierarchy.levels[0][0].entities


def test_leiden_two_distinct_clusters():
    """Verify detector separates two distinct disconnected sub-clusters into different communities."""
    detector = LeidenCommunityDetector()
    triples = [
        # Cluster A: Backend & API
        EntityTriple(subject="FastAPI", predicate="USES", object="Python"),
        EntityTriple(subject="FastAPI", predicate="USES", object="Pydantic"),
        EntityTriple(subject="Python", predicate="RUNS_ON", object="Uvicorn"),
        # Cluster B: Frontend & Web
        EntityTriple(subject="Next.js", predicate="USES", object="React"),
        EntityTriple(subject="React", predicate="USES", object="TypeScript"),
        EntityTriple(subject="Next.js", predicate="STYLED_WITH", object="TailwindCSS"),
    ]

    hierarchy = detector.detect_communities("test-tenant", triples, max_levels=2)

    assert hierarchy.total_communities >= 2
    assert 0 in hierarchy.levels
    level_0_comms = hierarchy.levels[0]

    # Check that FastAPI and React are in separate communities
    fastapi_comm = next(c for c in level_0_comms if "FastAPI" in c.entities)

    react_comm = next(c for c in level_0_comms if "React" in c.entities)

    assert fastapi_comm.community_id != react_comm.community_id
    assert "React" not in fastapi_comm.entities
    assert "TypeScript" not in fastapi_comm.entities
    assert "Pydantic" in fastapi_comm.entities
    assert hierarchy.modularity_score > 0.0



def test_leiden_hierarchical_levels():
    """Verify detector creates multi-level hierarchy (Level 0 -> Level 1)."""
    detector = LeidenCommunityDetector(resolution=1.0)
    
    # Dense interconnected network of multiple sub-domains
    triples = [
        # Core Platform
        EntityTriple(subject="AuthService", predicate="AUTHENTICATES", object="User"),
        EntityTriple(subject="AuthService", predicate="ISSUES", object="JWT"),
        EntityTriple(subject="User", predicate="HAS_ROLE", object="Admin"),
        # Storage Subsystem
        EntityTriple(subject="DocumentStore", predicate="PERSISTS", object="PDFDocument"),
        EntityTriple(subject="DocumentStore", predicate="USES", object="MinIO"),
        EntityTriple(subject="PDFDocument", predicate="HAS", object="VectorEmbedding"),
        # Bridge
        EntityTriple(subject="AuthService", predicate="PROTECTS", object="DocumentStore"),
    ]

    hierarchy = detector.detect_communities("test-tenant", triples, max_levels=3)

    assert hierarchy.total_communities >= 1
    assert 0 in hierarchy.levels
    assert hierarchy.modularity_score >= 0.0
    for lvl, comms in hierarchy.levels.items():
        assert len(comms) > 0
        for c in comms:
            assert c.tenant_id == "test-tenant"
            assert c.level == lvl
            assert len(c.entities) > 0
