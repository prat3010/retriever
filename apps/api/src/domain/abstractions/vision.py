"""Domain abstractions and interfaces for Multimodal Vision GraphRAG.

Hexagonal boundary rule: Pure domain definitions and interfaces only.
Zero database, ORM, framework, or external network client dependencies.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VisualElementType(StrEnum):
    """Semantic classifications for detected visual components in architecture diagrams."""

    SERVICE = "service"
    DATABASE = "database"
    GATEWAY = "gateway"
    QUEUE = "queue"
    CACHE = "cache"
    ACTOR = "actor"
    CONNECTOR = "connector"
    DATA_STORE = "data_store"
    BOUNDARY = "boundary"
    LABEL = "label"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    """Normalized bounding-box coordinates [ymin, xmin, ymax, xmax] in range 0.0 to 1.0."""

    ymin: float = Field(..., ge=0.0, le=1.0, description="Top coordinate (normalized)")
    xmin: float = Field(..., ge=0.0, le=1.0, description="Left coordinate (normalized)")
    ymax: float = Field(..., ge=0.0, le=1.0, description="Bottom coordinate (normalized)")
    xmax: float = Field(..., ge=0.0, le=1.0, description="Right coordinate (normalized)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence")

    @field_validator("ymax")
    @classmethod
    def validate_vertical(cls, v: float, info: Any) -> float:
        ymin = info.data.get("ymin")
        if ymin is not None and v < ymin:
            raise ValueError(f"ymax ({v}) must be greater than or equal to ymin ({ymin})")
        return v

    @field_validator("xmax")
    @classmethod
    def validate_horizontal(cls, v: float, info: Any) -> float:
        xmin = info.data.get("xmin")
        if xmin is not None and v < xmin:
            raise ValueError(f"xmax ({v}) must be greater than or equal to xmin ({xmin})")
        return v

    def to_list(self) -> list[float]:
        """Return coordinates as [ymin, xmin, ymax, xmax]."""
        return [self.ymin, self.xmin, self.ymax, self.xmax]

    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union (IoU) with another bounding box."""
        inter_ymin = max(self.ymin, other.ymin)
        inter_xmin = max(self.xmin, other.xmin)
        inter_ymax = min(self.ymax, other.ymax)
        inter_xmax = min(self.xmax, other.xmax)

        inter_w = max(0.0, inter_xmax - inter_xmin)
        inter_h = max(0.0, inter_ymax - inter_ymin)
        inter_area = inter_w * inter_h

        if inter_area == 0.0:
            return 0.0

        area_a = (self.ymax - self.ymin) * (self.xmax - self.xmin)
        area_b = (other.ymax - other.ymin) * (other.xmax - other.xmin)
        union_area = area_a + area_b - inter_area

        return inter_area / union_area if union_area > 0.0 else 0.0


class VisualElement(BaseModel):
    """A classified visual entity detected inside a technical schematic or blueprint."""

    element_id: str = Field(..., description="Unique element identifier inside the diagram")
    label: str = Field(..., description="Extracted label or service name (e.g. 'API Gateway', 'PostgreSQL')")
    element_type: VisualElementType = Field(default=VisualElementType.UNKNOWN)
    bounding_box: BoundingBox = Field(..., description="Normalized coordinates on diagram canvas")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class VisualConnector(BaseModel):
    """Directional edge or communication path between two visual diagram elements."""

    connector_id: str = Field(..., description="Unique connector identifier")
    source_element_id: str = Field(..., description="Source visual element ID")
    target_element_id: str = Field(..., description="Target visual element ID")
    label: str = Field(default="", description="Protocol, action, or payload label (e.g. 'HTTPS POST', 'gRPC')")
    directionality: str = Field(default="directed", description="'directed', 'bidirectional', or 'undirected'")
    protocol: str | None = Field(default=None, description="Inferred network/data protocol (e.g. 'SQL', 'AMQP')")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SchematicDiagram(BaseModel):
    """Complete structured representation of an architectural schematic or system blueprint."""

    diagram_id: str = Field(..., description="Unique diagram identifier")
    filename: str = Field(..., description="Origin file name (e.g. 'architecture.png', 'system_topology.svg')")
    document_id: str | None = Field(default=None, description="Parent document ID if part of multi-page doc")
    page_number: int = Field(default=1, ge=1)
    width: float = Field(default=1920.0, gt=0.0)
    height: float = Field(default=1080.0, gt=0.0)
    elements: list[VisualElement] = Field(default_factory=list)
    connectors: list[VisualConnector] = Field(default_factory=list)
    summary: str = Field(default="", description="Algorithmic architectural narrative of diagram topology")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalGraphNode(BaseModel):
    """Unified graph node representing either a visual diagram component or a textual entity."""

    id: str
    label: str
    node_type: str = Field(..., description="'visual_component', 'textual_entity', or 'table_entity'")
    element_type: VisualElementType | None = None
    bounding_box: BoundingBox | None = None
    diagram_id: str | None = None
    document_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalGraphEdge(BaseModel):
    """Directed edge between multimodal graph nodes."""

    source: str
    target: str
    relation: str
    protocol: str | None = None
    is_cross_modal: bool = Field(default=False, description="True if edge links visual element to text entity")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalGraphQueryRequest(BaseModel):
    """Query parameters for interleaved visual-textual knowledge graph traversal."""

    tenant_id: str
    entity_query: str
    max_hops: int = Field(default=2, ge=1, le=5)
    include_visual_boxes: bool = True
    element_types: list[VisualElementType] = Field(default_factory=list)


class MultimodalGraphResponse(BaseModel):
    """Result of multimodal knowledge graph traversal."""

    root_entity: str
    nodes: list[MultimodalGraphNode] = Field(default_factory=list)
    edges: list[MultimodalGraphEdge] = Field(default_factory=list)
    cross_modal_links_count: int = 0
    triples_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseSchematicExtractor(ABC):
    """Abstract Port for extracting structured components and arrows from schematic blueprints."""

    @abstractmethod
    async def extract_schematic(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str = "image/png",
    ) -> SchematicDiagram:
        """Parse raw image or SVG bytes into a structured SchematicDiagram."""
        pass

    @abstractmethod
    def extract_triples_from_diagram(
        self,
        diagram: SchematicDiagram,
        tenant_id: str,
        document_id: str | None = None,
    ) -> list[Any]:
        """Convert diagram elements and directional connectors into EntityTriples with visual provenance."""
        pass


class BaseMultimodalGraphService(ABC):
    """Abstract Port for interleaved cross-modal GraphRAG traversal and entity resolution."""

    @abstractmethod
    async def link_cross_modal_entities(
        self,
        tenant_id: str,
        document_id: str,
        diagram: SchematicDiagram,
        text_chunks: list[Any],
    ) -> list[Any]:
        """Discover bidirectional associative edges between diagram visual elements and document text chunks."""
        pass

    @abstractmethod
    async def query_multimodal_graph(
        self,
        request: MultimodalGraphQueryRequest,
    ) -> MultimodalGraphResponse:
        """Execute multi-hop graph traversal traversing visual components and textual entities."""
        pass
