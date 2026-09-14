"""Unit and integration test suite for Milestone 113: Multimodal Vision GraphRAG & Schematic Ingestion."""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.adapters.cognitive.vision_parser_adapter import VisionParserAdapter
from src.domain.abstractions.graph import EntityTriple
from src.domain.abstractions.ingestion import DocumentChunk
from src.domain.abstractions.vision import (
    BoundingBox,
    MultimodalGraphQueryRequest,
    VisualElementType,
)
from src.domain.vision.multimodal_graph_service import MultimodalGraphService
from src.domain.vision.schematic_extractor import DomainSchematicExtractor
from src.main import app

client = TestClient(app)

SAMPLE_SVG = """<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <rect id="API_Gateway" x="200" y="200" width="300" height="120" rx="10">
    <text x="250" y="260">API Gateway</text>
  </rect>
  <rect id="Order_Service" x="700" y="200" width="300" height="120" rx="10">
    <text x="750" y="260">Order Service</text>
  </rect>
  <circle id="PostgreSQL_Database" cx="1350" cy="260" r="80">
    <text x="1300" y="260">PostgreSQL Database</text>
  </circle>
  <circle id="Redis_Cache" cx="1350" cy="600" r="80">
    <text x="1310" y="600">Redis Cache</text>
  </circle>
  <line x1="500" y1="260" x2="700" y2="260" stroke="#000" stroke-width="2" />
  <line x1="1000" y1="260" x2="1270" y2="260" stroke="#000" stroke-width="2" />
</svg>"""

SAMPLE_FLOW_TEXT = """
[Client App] -->|HTTPS POST| [API Gateway]
[API Gateway] -->|gRPC| [Order Service]
[Order Service] -->|SQL| [PostgreSQL Database]
[Order Service] -->|TCP| [Redis Cache]
"""


# ── 1. BoundingBox Math & Invariants ──────────────────────────────────────────

def test_bounding_box_valid_and_normalization():
    """Verify BoundingBox enforces normalized coordinates and calculates IoU."""
    box1 = BoundingBox(ymin=0.1, xmin=0.1, ymax=0.5, xmax=0.5, confidence=0.98)
    assert box1.to_list() == [0.1, 0.1, 0.5, 0.5]
    assert box1.confidence == 0.98

    # Identical box IoU == 1.0
    assert pytest.approx(box1.iou(box1), 0.001) == 1.0

    # Disjoint box IoU == 0.0
    box2 = BoundingBox(ymin=0.6, xmin=0.6, ymax=0.9, xmax=0.9)
    assert box1.iou(box2) == 0.0

    # Overlapping box IoU
    box3 = BoundingBox(ymin=0.3, xmin=0.3, ymax=0.5, xmax=0.5)
    iou = box1.iou(box3)
    assert 0.0 < iou < 1.0


def test_bounding_box_invalid_invariants():
    """Verify BoundingBox raises ValueError if ymax < ymin or xmax < xmin."""
    with pytest.raises(ValueError, match="ymax"):
        BoundingBox(ymin=0.8, xmin=0.1, ymax=0.2, xmax=0.5)

    with pytest.raises(ValueError, match="xmax"):
        BoundingBox(ymin=0.1, xmin=0.8, ymax=0.5, xmax=0.2)


# ── 2. DomainSchematicExtractor Parsing ────────────────────────────────────────

@pytest.mark.asyncio
async def test_schematic_extractor_svg_parsing():
    """Verify DomainSchematicExtractor parses SVG shapes, classifies roles, and maps connectors."""
    extractor = DomainSchematicExtractor()
    diagram = await extractor.extract_schematic(
        file_content=SAMPLE_SVG.encode("utf-8"),
        filename="cloud_topology.svg",
        mime_type="image/svg+xml",
    )

    assert diagram.filename == "cloud_topology.svg"
    assert len(diagram.elements) >= 3

    labels = {e.label for e in diagram.elements}
    assert any("API Gateway" in lab for lab in labels)
    assert any("Order Service" in lab for lab in labels)
    assert any("PostgreSQL" in lab for lab in labels)

    # Verify semantic classification
    types = {e.element_type for e in diagram.elements}
    assert VisualElementType.GATEWAY in types or VisualElementType.SERVICE in types
    assert VisualElementType.DATABASE in types

    # Verify connectors detected
    assert len(diagram.connectors) >= 1

    # Verify narrative summary generated
    assert "cloud_topology.svg" in diagram.summary
    assert "visual components" in diagram.summary


@pytest.mark.asyncio
async def test_schematic_extractor_text_flow_parsing():
    """Verify DomainSchematicExtractor parses text architecture diagrams and generates grid coordinates."""
    extractor = DomainSchematicExtractor()
    diagram = await extractor.extract_schematic(
        file_content=SAMPLE_FLOW_TEXT.encode("utf-8"),
        filename="architecture_flow.txt",
        mime_type="text/plain",
    )

    assert len(diagram.elements) >= 4
    assert len(diagram.connectors) >= 3

    # Check protocol inference
    protocols = {c.protocol for c in diagram.connectors if c.protocol}
    assert "HTTPS" in protocols or "SQL" in protocols or "gRPC" in protocols

    # Check triple generation
    triples = extractor.extract_triples_from_diagram(diagram, tenant_id="t1", document_id="doc1")
    assert len(triples) >= 4
    preds = {t.predicate for t in triples}
    assert "IS_TYPE" in preds or any("ROUTES" in p or "SQL" in p or "CONNECTS" in p for p in preds)


# ── 3. Cross-Modal Linking & MultimodalGraphService ───────────────────────────

@pytest.mark.asyncio
async def test_cross_modal_linking_and_traversal():
    """Verify MultimodalGraphService links diagram elements to text chunks and traverses graph."""
    mock_graph_repo = MagicMock()
    service = MultimodalGraphService(graph_repository=mock_graph_repo)

    # Setup diagram with visual elements
    extractor = DomainSchematicExtractor()
    diagram = await extractor.extract_schematic(
        file_content=SAMPLE_FLOW_TEXT.encode("utf-8"),
        filename="system.txt",
        mime_type="text/plain",
    )

    # Setup document text chunks
    chunks = [
        DocumentChunk(
            chunk_id="chunk_1",
            document_id="doc_100",
            tenant_id="t_1",
            content="The API Gateway inspects JWT credentials and forwards valid traffic to Order Service.",
            token_count=16,
            chunk_index=0,
            created_at="2026-09-15T00:00:00Z",
        ),
        DocumentChunk(
            chunk_id="chunk_2",
            document_id="doc_100",
            tenant_id="t_1",
            content="Order Service persists customer ledger records into the PostgreSQL Database cluster.",
            token_count=14,
            chunk_index=1,
            created_at="2026-09-15T00:00:00Z",
        ),
    ]

    # Test cross-modal link discovery
    xm_triples = await service.link_cross_modal_entities(
        tenant_id="t_1",
        document_id="doc_100",
        diagram=diagram,
        text_chunks=chunks,
    )

    assert len(xm_triples) >= 2
    xm_subjects = {t.subject for t in xm_triples}
    assert any("API Gateway" in s or "Order Service" in s or "PostgreSQL" in s for s in xm_subjects)
    for xm in xm_triples:
        assert xm.metadata["source"] == "cross_modal_linking"
        assert "bounding_box" in xm.metadata

    # Test format_visual_citation
    citation = service.format_visual_citation("architecture.png", "Order Service", [0.1, 0.2, 0.4, 0.5])
    assert '[Schematic: architecture.png | Box: 0.100,0.200,0.400,0.500 | "Order Service"]' == citation


@pytest.mark.asyncio
async def test_multimodal_graph_query_traversal():
    """Verify query_multimodal_graph returns interleaved nodes and edges with bounding boxes."""
    mock_graph_repo = MagicMock()
    tenant_id = str(uuid.uuid4())

    mock_triples = [
        EntityTriple(
            triple_id="t1",
            subject="API Gateway",
            predicate="ROUTES_TO",
            object="Order Service",
            confidence=0.95,
            metadata={"source": "visual_schematic", "bounding_box": [0.1, 0.1, 0.3, 0.4], "protocol": "HTTPS"},
        ),
        EntityTriple(
            triple_id="t2",
            subject="Order Service",
            predicate="PERSISTS_IN",
            object="PostgreSQL",
            confidence=0.90,
            metadata={"source": "visual_schematic", "bounding_box": [0.5, 0.5, 0.8, 0.8], "protocol": "SQL"},
        ),
        EntityTriple(
            triple_id="t3",
            subject="Order Service",
            predicate="DOCUMENTED_IN_CHUNK",
            object="Chunk_1",
            confidence=0.92,
            metadata={"source": "cross_modal_linking", "chunk_id": "c1"},
        ),
    ]

    from src.domain.abstractions.graph import GraphSearchResult
    mock_graph_repo.search_triples = AsyncMock(
        return_value=GraphSearchResult(root_entity="API Gateway", max_hops=2, triples=mock_triples)
    )

    service = MultimodalGraphService(graph_repository=mock_graph_repo)
    req = MultimodalGraphQueryRequest(
        tenant_id=tenant_id,
        entity_query="API Gateway",
        max_hops=2,
    )
    resp = await service.query_multimodal_graph(req)

    assert resp.root_entity == "API Gateway"
    assert len(resp.nodes) >= 3
    assert len(resp.edges) == 3
    assert resp.cross_modal_links_count == 1
    assert resp.triples_count == 3

    # Check node types
    node_types = {n.node_type for n in resp.nodes}
    assert "visual_component" in node_types


# ── 4. VisionParserAdapter Binary Header Inspection ───────────────────────────

@pytest.mark.asyncio
async def test_vision_parser_adapter_dimensions():
    """Verify VisionParserAdapter extracts PNG binary dimensions from header bytes."""
    adapter = VisionParserAdapter()

    # Synthetic 800x600 PNG header (IHDR at offset 16)
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    # Chunk length (4 bytes), Chunk type 'IHDR' (4 bytes)
    # Width: 800 (0x00000320), Height: 600 (0x00000258)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x03\x20"  # 800
        b"\x00\x00\x02\x58"  # 600
        b"\x08\x02\x00\x00\x00"
    )

    w, h = adapter._probe_image_dimensions(png_bytes, "image/png")
    assert w == 800.0
    assert h == 600.0


# ── 5. FastAPI Vision Endpoints Integration ───────────────────────────────────

def test_multimodal_status_endpoint():
    """Verify GET /v1/graph/multimodal/status returns 200 OK and Battery #29 details."""
    response = client.get("/v1/graph/multimodal/status")
    assert response.status_code == 200
    data = response.json()
    assert data["battery_id"] == "multimodal_vision_graphrag"
    assert data["status"] == "active"
    assert data["milestone"] == "M113"
    assert "svg" in data["supported_formats"]


from src.adapters.api.security import verify_scopes, verify_tenant_isolation


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[verify_tenant_isolation] = lambda: "00000000-0000-0000-0000-000000000001"
    app.dependency_overrides[verify_scopes] = lambda: ["document:write", "document:read", "search:read"]
    yield
    app.dependency_overrides.pop(verify_tenant_isolation, None)
    app.dependency_overrides.pop(verify_scopes, None)


def test_extract_schematic_text_api():
    """Verify POST /v1/tenants/{tenantId}/vision/schematic/extract-text endpoint."""
    payload = {
        "content": SAMPLE_SVG,
        "filename": "test_diagram.svg",
        "document_id": "doc_999",
    }

    response = client.post(
        "/v1/tenants/00000000-0000-0000-0000-000000000001/vision/schematic/extract-text",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_diagram.svg"
    assert data["document_id"] == "doc_999"
    assert len(data["elements"]) >= 3
    assert len(data["connectors"]) >= 1


def test_extract_schematic_multipart_upload_api():
    """Verify POST /v1/tenants/{tenantId}/vision/schematic/extract multipart upload endpoint."""
    files = {
        "file": ("blueprint.svg", io.BytesIO(SAMPLE_SVG.encode("utf-8")), "image/svg+xml"),
    }

    response = client.post(
        "/v1/tenants/00000000-0000-0000-0000-000000000001/vision/schematic/extract",
        files=files,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "blueprint.svg"
    assert len(data["elements"]) >= 3


@patch("src.container.multimodal_graph_service.query_multimodal_graph")
def test_query_multimodal_graph_api(mock_query):
    """Verify POST /v1/tenants/{tenantId}/vision/graph/query endpoint."""
    from src.domain.abstractions.vision import (
        MultimodalGraphEdge,
        MultimodalGraphNode,
        MultimodalGraphResponse,
    )

    mock_query.return_value = MultimodalGraphResponse(
        root_entity="Order Service",
        nodes=[MultimodalGraphNode(id="order_service", label="Order Service", node_type="visual_component")],
        edges=[MultimodalGraphEdge(source="api_gateway", target="order_service", relation="ROUTES_TO")],
    )

    payload = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "entity_query": "Order Service",
        "max_hops": 2,
        "include_visual_boxes": True,
    }

    response = client.post(
        "/v1/tenants/00000000-0000-0000-0000-000000000001/vision/graph/query",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["root_entity"] == "Order Service"
    assert "nodes" in data
    assert "edges" in data


