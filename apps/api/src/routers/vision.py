"""Vision & Multimodal GraphRAG API Routes.

Exposes endpoints for architectural schematic extraction, visual component bounding boxes,
directional connector topologies, and interleaved multimodal knowledge graph traversal.
"""

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Security,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_scopes, verify_tenant_isolation
from src.container import (
    document_repository,
    graph_repository,
    multimodal_graph_service,
    schematic_extractor,
)
from src.domain.abstractions.vision import (
    MultimodalGraphQueryRequest,
    MultimodalGraphResponse,
    SchematicDiagram,
)

router = APIRouter(tags=["Vision & Multimodal GraphRAG"])


class ExtractSchematicTextRequest(BaseModel):
    """Payload for extracting schematic from text/ASCII or SVG markup without multipart upload."""

    content: str = Field(..., description="Raw SVG markup, ASCII diagram, or architecture description")
    filename: str = Field(default="architecture.svg", description="Diagram filename")
    document_id: str | None = Field(default=None, description="Optional associated document ID")


class MultimodalStatusResponse(BaseModel):
    """Health check response for Battery #29."""

    battery_id: str = "multimodal_vision_graphrag"
    status: str = "active"
    version: str = "v1.3.0-alpha1"
    milestone: str = "M113"
    supported_formats: list[str] = ["svg", "png", "jpg", "jpeg", "webp"]
    active_parameters: dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/v1/graph/multimodal/status",
    response_model=MultimodalStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_multimodal_status() -> MultimodalStatusResponse:
    """Public health check endpoint for Multimodal Vision GraphRAG (Battery #29)."""
    return MultimodalStatusResponse(
        active_parameters={
            "bounding_box_normalized": True,
            "max_hops": 3,
            "cross_modal_linking_enabled": True,
            "iou_deduplication_threshold": 0.8,
        }
    )


@router.post(
    "/v1/tenants/{tenantId}/vision/schematic/extract",
    response_model=SchematicDiagram,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(verify_tenant_isolation),
        Security(verify_scopes, scopes=["document:write"]),
    ],
)
async def extract_schematic_upload(
    tenantId: str,
    file: UploadFile = File(...),
    document_id: str | None = Query(None, alias="documentId"),
) -> SchematicDiagram:
    """Upload an architecture schematic (SVG, PNG, JPG) to extract visual elements and connectors."""
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    filename = file.filename or "schematic.png"
    mime_type = file.content_type or "image/png"

    # 1. Parse diagram
    diagram = await schematic_extractor.extract_schematic(
        file_content=content,
        filename=filename,
        mime_type=mime_type,
    )
    if document_id:
        diagram.document_id = document_id

    # 2. Extract visual entity relationship triples
    triples = schematic_extractor.extract_triples_from_diagram(
        diagram=diagram,
        tenant_id=tenantId,
        document_id=document_id,
    )

    # 3. If document_id provided, cross-link with existing document text chunks
    if document_id and document_repository:
        try:
            chunks = await document_repository.get_document_chunks(tenantId, document_id)
            if chunks:
                xm_triples = await multimodal_graph_service.link_cross_modal_entities(
                    tenant_id=tenantId,
                    document_id=document_id,
                    diagram=diagram,
                    text_chunks=chunks,
                )
                triples.extend(xm_triples)
        except Exception:
            pass

    # 4. Ingest triples into GraphRAG store
    if triples and graph_repository:
        try:
            await graph_repository.add_triples(tenantId, triples)
        except Exception:
            pass

    return diagram


@router.post(
    "/v1/tenants/{tenantId}/vision/schematic/extract-text",
    response_model=SchematicDiagram,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(verify_tenant_isolation),
        Security(verify_scopes, scopes=["document:write"]),
    ],
)
async def extract_schematic_text(
    tenantId: str,
    payload: ExtractSchematicTextRequest,
) -> SchematicDiagram:
    """Extract schematic topology from raw SVG string or ASCII architecture description."""
    if not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content string cannot be empty.",
        )

    content_bytes = payload.content.encode("utf-8")
    mime = "image/svg+xml" if payload.filename.endswith(".svg") else "text/plain"

    diagram = await schematic_extractor.extract_schematic(
        file_content=content_bytes,
        filename=payload.filename,
        mime_type=mime,
    )
    if payload.document_id:
        diagram.document_id = payload.document_id

    triples = schematic_extractor.extract_triples_from_diagram(
        diagram=diagram,
        tenant_id=tenantId,
        document_id=payload.document_id,
    )

    if triples and graph_repository:
        try:
            await graph_repository.add_triples(tenantId, triples)
        except Exception:
            pass

    return diagram


@router.post(
    "/v1/tenants/{tenantId}/vision/graph/query",
    response_model=MultimodalGraphResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(verify_tenant_isolation),
        Security(verify_scopes, scopes=["search:read"]),
    ],
)
async def query_multimodal_graph(
    tenantId: str,
    request: MultimodalGraphQueryRequest,
) -> MultimodalGraphResponse:
    """Execute multi-hop graph traversal across interleaved visual components and text entities."""
    # Ensure tenant_id in request matches authenticated route tenant
    request.tenant_id = tenantId
    return await multimodal_graph_service.query_multimodal_graph(request)


@router.get(
    "/v1/tenants/{tenantId}/vision/schematics/{documentId}",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(verify_tenant_isolation),
        Security(verify_scopes, scopes=["document:read"]),
    ],
)
async def get_document_schematic_triples(
    tenantId: str,
    documentId: str,
) -> dict[str, Any]:
    """Retrieve all visual and cross-modal triples associated with a specific document."""
    if not graph_repository:
        return {"document_id": documentId, "triples": []}

    all_triples = await graph_repository.get_all_triples(tenantId, limit=1000)
    doc_triples = [
        t
        for t in all_triples
        if t.document_id == documentId
        or (t.metadata and t.metadata.get("document_id") == documentId)
    ]

    return {
        "tenant_id": tenantId,
        "document_id": documentId,
        "total_triples": len(doc_triples),
        "triples": [t.model_dump() for t in doc_triples],
    }
