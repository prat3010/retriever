"""Domain abstractions for Unsupervised Topic Modeling and Knowledge Gap Analysis."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ClusterTopic(BaseModel):
    """Semantic cluster of related document chunks with c-TF-IDF keyword labels."""

    topic_id: int = Field(..., description="Unique cluster identifier (-1 indicates noise/outliers)")
    label: str = Field(..., description="Descriptive semantic topic name synthesized from top keywords")
    keywords: list[str] = Field(default_factory=list, description="Top-N distinctive keywords extracted via c-TF-IDF")
    chunk_ids: list[str] = Field(default_factory=list, description="Chunk IDs belonging to this semantic cluster")
    chunk_count: int = Field(default=0, description="Total number of chunks in this topic")
    centroid: list[float] = Field(default_factory=list, description="Centroid vector of the cluster in embedding space")
    coherence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Semantic coherence density score")
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGapReport(BaseModel):
    """Diagnostic audit of knowledge vault connectivity, isolated topics, and orphaned chunks."""

    tenant_id: str
    total_chunks: int
    orphan_chunk_count: int = Field(..., description="Count of chunks disconnected from all major semantic clusters")
    orphan_chunk_ids: list[str] = Field(default_factory=list, description="IDs of orphaned or low-retrieval chunks")
    sparse_topics: list[str] = Field(default_factory=list, description="Topics with underrepresented documentation")
    knowledge_coverage_score: float = Field(..., ge=0.0, le=1.0, description="Overall knowledge vault density score")
    recommendations: list[str] = Field(default_factory=list, description="Actionable documentation improvement tips")


class TopicClusteringRequest(BaseModel):
    """Configuration payload for unsupervised chunk clustering."""

    min_cluster_size: int = Field(default=2, ge=2, le=50, description="Minimum chunks required to form a cluster")
    method: str = Field(default="hdbscan", description="Clustering algorithm ('hdbscan' | 'kmeans')")
    top_k_keywords: int = Field(default=5, ge=2, le=15, description="Number of distinctive keywords per topic")


class TopicClusteringResponse(BaseModel):
    """Output summary of tenant topic clustering."""

    tenant_id: str
    total_chunks: int
    total_clusters: int
    topics: list[ClusterTopic]
    outlier_chunk_count: int
    algorithm_used: str


class BaseTopicClusterer(ABC):
    """Abstract port for unsupervised chunk clustering and topic model synthesis."""

    @abstractmethod
    def cluster_chunks(
        self,
        tenant_id: str,
        chunk_ids: list[str],
        chunk_texts: list[str],
        embeddings: list[list[float]],
        request: TopicClusteringRequest,
    ) -> TopicClusteringResponse:
        """Execute unsupervised clustering and return labeled semantic topics."""
        pass


class BaseKnowledgeGapDetector(ABC):
    """Abstract port for detecting orphaned knowledge chunks and coverage gaps."""

    @abstractmethod
    def analyze_knowledge_gaps(
        self,
        tenant_id: str,
        clustering_result: TopicClusteringResponse,
        chunk_texts: dict[str, str],
    ) -> KnowledgeGapReport:
        """Analyze clustering output and identify missing links and low-coherence topics."""
        pass
