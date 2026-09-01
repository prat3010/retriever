"""Domain abstractions for 2D/3D Embedding Space Dimensionality Reduction & Visualization."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ProjectedPoint(BaseModel):
    """Projected 2D or 3D coordinate representing a document chunk in latent space."""

    chunk_id: str = Field(..., description="Unique identifier of the document chunk")
    document_id: str = Field(default="", description="ID of the parent document")
    document_title: str = Field(default="", description="Name or title of the parent document")
    coordinates: list[float] = Field(..., description="Projected coordinates [x, y] or [x, y, z]")
    cluster_id: int = Field(default=-1, description="Assigned semantic topic cluster ID (-1 for outlier)")
    cluster_label: str = Field(default="Unclassified", description="Synthesized topic label")
    text_preview: str = Field(default="", description="Short snippet of the chunk text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")


class ProjectionCentroid(BaseModel):
    """Centroid coordinate for a topic cluster in the reduced 2D/3D manifold."""

    cluster_id: int = Field(..., description="Cluster identifier")
    cluster_label: str = Field(..., description="Cluster topic name")
    coordinates: list[float] = Field(..., description="Centroid coordinates [x, y] or [x, y, z]")
    chunk_count: int = Field(default=0, description="Total chunks in this cluster")


class EmbeddingProjectionRequest(BaseModel):
    """Configuration payload for dimensionality reduction."""

    method: str = Field(default="pca", description="Dimensionality reduction algorithm ('pca' | 'tsne' | 'umap')")
    dimensions: int = Field(default=3, ge=2, le=3, description="Target dimension count (2 or 3)")
    perplexity: float = Field(default=30.0, ge=2.0, le=100.0, description="t-SNE perplexity parameter")
    n_neighbors: int = Field(default=15, ge=2, le=100, description="UMAP nearest neighbors parameter")
    min_dist: float = Field(default=0.1, ge=0.0, le=1.0, description="UMAP minimum distance parameter")
    normalize: bool = Field(default=True, description="Scale coordinates to [-100, 100] bounding space")
    query_vector: list[float] | None = Field(default=None, description="Optional search query vector to project")


class EmbeddingProjectionResponse(BaseModel):
    """Result of embedding space projection with cluster metadata and metrics."""

    tenant_id: str
    total_points: int
    dimensions: int
    method_used: str
    points: list[ProjectedPoint] = Field(default_factory=list)
    centroids: list[ProjectionCentroid] = Field(default_factory=list)
    variance_explained: list[float] | None = Field(default=None, description="Explained variance ratio (for PCA)")
    silhouette_score: float | None = Field(default=None, description="Cluster separation quality score (-1.0 to 1.0)")
    query_point: ProjectedPoint | None = Field(default=None, description="Projected query vector coordinate")


class BaseEmbeddingProjector(ABC):
    """Abstract port for dimensionality reduction of latent embeddings."""

    @abstractmethod
    def project_embeddings(
        self,
        tenant_id: str,
        chunk_ids: list[str],
        chunk_texts: list[str],
        document_ids: list[str],
        document_titles: list[str],
        embeddings: list[list[float]],
        cluster_ids: list[int] | None = None,
        cluster_labels: dict[int, str] | None = None,
        request: EmbeddingProjectionRequest | None = None,
    ) -> EmbeddingProjectionResponse:
        """Project high-dimensional embeddings down to 2D/3D coordinates."""
        pass
