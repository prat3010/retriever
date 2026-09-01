"""Unit tests for Scikit-Learn 2D/3D Embedding Space Projection Pipeline (Milestone 82)."""

try:
    import pytest
    fixture = pytest.fixture
except ImportError:
    def fixture(func):
        return func

import numpy as np

from src.adapters.cognitive.embedding_projection_adapter import (
    EmbeddingProjectionAdapter,
)
from src.domain.projection.abstractions import (
    EmbeddingProjectionRequest,
    EmbeddingProjectionResponse,
)


@fixture
def projection_adapter():
    return EmbeddingProjectionAdapter()


def test_empty_collection_projection(projection_adapter):
    """Verify empty embedding lists return clean empty response without crashing."""
    res = projection_adapter.project_embeddings(
        tenant_id="tenant-proj-1",
        chunk_ids=[],
        chunk_texts=[],
        document_ids=[],
        document_titles=[],
        embeddings=[],
        request=EmbeddingProjectionRequest(dimensions=3),
    )

    assert isinstance(res, EmbeddingProjectionResponse)
    assert res.total_points == 0
    assert res.dimensions == 3
    assert res.points == []
    assert res.centroids == []
    assert res.query_point is None


def test_minimal_samples_projection(projection_adapter):
    """Verify 1 and 2 sample collections produce valid deterministic coordinates."""
    # 1 sample
    res_1 = projection_adapter.project_embeddings(
        tenant_id="tenant-proj-2",
        chunk_ids=["c1"],
        chunk_texts=["Single test document chunk."],
        document_ids=["doc1"],
        document_titles=["SingleDoc.pdf"],
        embeddings=[[0.1, 0.2, 0.3, 0.4]],
        request=EmbeddingProjectionRequest(dimensions=3),
    )
    assert res_1.total_points == 1
    assert len(res_1.points) == 1
    assert len(res_1.points[0].coordinates) == 3

    # 2 samples
    res_2 = projection_adapter.project_embeddings(
        tenant_id="tenant-proj-2",
        chunk_ids=["c1", "c2"],
        chunk_texts=["Doc 1 text", "Doc 2 text"],
        document_ids=["doc1", "doc2"],
        document_titles=["DocA.pdf", "DocB.pdf"],
        embeddings=[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]],
        request=EmbeddingProjectionRequest(dimensions=3),
    )
    assert res_2.total_points == 2
    assert len(res_2.points) == 2
    assert len(res_2.points[0].coordinates) == 3
    assert len(res_2.points[1].coordinates) == 3


def test_pca_3d_projection_and_normalization(projection_adapter):
    """Verify PCA 3D projection on synthetic multi-topic dataset preserves geometry within bounds."""
    np.random.seed(42)

    # 3 clusters with 5 samples each (15 total, 16-dim embeddings)
    n_dim = 16
    c1 = np.random.normal(loc=[1.0] * n_dim, scale=0.1, size=(5, n_dim))
    c2 = np.random.normal(loc=[-1.0] * n_dim, scale=0.1, size=(5, n_dim))
    c3 = np.random.normal(loc=[0.0] * n_dim, scale=0.1, size=(5, n_dim))

    embeddings = np.vstack([c1, c2, c3]).tolist()
    chunk_ids = [f"chk_{i}" for i in range(15)]
    chunk_texts = [f"Text snippet content for chunk {i}" for i in range(15)]
    document_ids = [f"doc_{i // 5}" for i in range(15)]
    document_titles = [f"Document_{i // 5}.pdf" for i in range(15)]
    cluster_ids = [0] * 5 + [1] * 5 + [2] * 5
    cluster_labels = {0: "Authentication & OAuth", 1: "Stripe & Invoicing", 2: "RAG & Vector Search"}

    res = projection_adapter.project_embeddings(
        tenant_id="tenant-proj-3",
        chunk_ids=chunk_ids,
        chunk_texts=chunk_texts,
        document_ids=document_ids,
        document_titles=document_titles,
        embeddings=embeddings,
        cluster_ids=cluster_ids,
        cluster_labels=cluster_labels,
        request=EmbeddingProjectionRequest(method="pca", dimensions=3, normalize=True),
    )

    assert res.total_points == 15
    assert res.dimensions == 3
    assert res.method_used == "pca"
    assert len(res.points) == 15
    assert len(res.centroids) == 3
    assert res.variance_explained is not None
    assert len(res.variance_explained) == 3

    # Check coordinate bounds
    for pt in res.points:
        assert len(pt.coordinates) == 3
        for coord in pt.coordinates:
            assert -100.0 <= coord <= 100.0
        assert pt.cluster_label in cluster_labels.values()

    # Check centroid consistency
    for centroid in res.centroids:
        assert len(centroid.coordinates) == 3
        assert centroid.chunk_count == 5

    # Check silhouette score is high for well-separated clusters
    assert res.silhouette_score is not None
    assert res.silhouette_score > 0.5


def test_tsne_2d_projection(projection_adapter):
    """Verify t-SNE 2D projection executes cleanly."""
    np.random.seed(42)
    embeddings = np.random.normal(size=(10, 8)).tolist()
    chunk_ids = [f"c_{i}" for i in range(10)]
    chunk_texts = [f"Text {i}" for i in range(10)]
    document_ids = ["d1"] * 10
    document_titles = ["Doc.txt"] * 10

    res = projection_adapter.project_embeddings(
        tenant_id="tenant-proj-4",
        chunk_ids=chunk_ids,
        chunk_texts=chunk_texts,
        document_ids=document_ids,
        document_titles=document_titles,
        embeddings=embeddings,
        request=EmbeddingProjectionRequest(method="tsne", dimensions=2, perplexity=3.0),
    )

    assert res.total_points == 10
    assert res.dimensions == 2
    assert res.method_used == "tsne"
    assert len(res.points) == 10
    for pt in res.points:
        assert len(pt.coordinates) == 2


def test_dynamic_query_vector_projection(projection_adapter):
    """Verify passing a query_vector computes a valid projected query coordinate."""
    np.random.seed(42)
    n_dim = 8
    embeddings = np.random.normal(size=(12, n_dim)).tolist()
    chunk_ids = [f"c_{i}" for i in range(12)]
    chunk_texts = [f"Text {i}" for i in range(12)]
    document_ids = ["d1"] * 12
    document_titles = ["Doc.txt"] * 12

    # Query vector close to first chunk
    query_vec = list(embeddings[0])

    res = projection_adapter.project_embeddings(
        tenant_id="tenant-proj-5",
        chunk_ids=chunk_ids,
        chunk_texts=chunk_texts,
        document_ids=document_ids,
        document_titles=document_titles,
        embeddings=embeddings,
        request=EmbeddingProjectionRequest(
            method="pca",
            dimensions=3,
            query_vector=query_vec,
        ),
    )

    assert res.query_point is not None
    assert res.query_point.chunk_id == "query_vector"
    assert len(res.query_point.coordinates) == 3
    for coord in res.query_point.coordinates:
        assert -100.0 <= coord <= 100.0
