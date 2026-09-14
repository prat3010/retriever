"""Pure domain service for interleaved multimodal knowledge graph traversal and cross-modal linking.

Hexagonal boundary rule: Pure mathematical domain logic.
Only standard library modules and domain abstractions allowed.
Zero database, ORM, framework, or external HTTP imports.
"""

import uuid
from typing import Any

from src.domain.abstractions.graph import BaseGraphRepository, EntityTriple
from src.domain.abstractions.ingestion import DocumentChunk
from src.domain.abstractions.vision import (
    BaseMultimodalGraphService,
    BoundingBox,
    MultimodalGraphEdge,
    MultimodalGraphNode,
    MultimodalGraphQueryRequest,
    MultimodalGraphResponse,
    SchematicDiagram,
)


def _to_bounding_box(val: Any) -> BoundingBox | None:
    """Safely coerce dictionary, list, or BoundingBox instance to BoundingBox."""
    if isinstance(val, BoundingBox):
        return val
    if isinstance(val, list | tuple) and len(val) == 4:
        try:
            return BoundingBox(ymin=float(val[0]), xmin=float(val[1]), ymax=float(val[2]), xmax=float(val[3]))
        except Exception:
            return None
    if isinstance(val, dict):
        try:
            return BoundingBox(**val)
        except Exception:
            return None
    return None


class MultimodalGraphService(BaseMultimodalGraphService):
    """Domain service managing cross-modal entity linking and multi-hop visual graph traversal."""

    def __init__(self, graph_repository: BaseGraphRepository | None = None) -> None:
        self.graph_repository = graph_repository

    async def link_cross_modal_entities(
        self,
        tenant_id: str,
        document_id: str,
        diagram: SchematicDiagram,
        text_chunks: list[DocumentChunk],
    ) -> list[EntityTriple]:
        """Discover bidirectional associative edges between diagram visual elements and document text chunks."""
        cross_modal_triples: list[EntityTriple] = []
        if not diagram.elements or not text_chunks:
            return cross_modal_triples

        for elem in diagram.elements:
            elem_name = elem.label.strip()
            if len(elem_name) < 3:
                continue

            elem_lower = elem_name.lower()

            for chunk in text_chunks:
                chunk_text = chunk.content.lower()
                if elem_lower in chunk_text:
                    # Formulate cross-modal triple linking textual chunk to visual element
                    triple_id = f"xm_{uuid.uuid4().hex[:12]}"
                    cross_modal_triples.append(
                        EntityTriple(
                            triple_id=triple_id,
                            subject=elem_name,
                            predicate="DOCUMENTED_IN_CHUNK",
                            object=f"Chunk_{chunk.chunk_index}",
                            chunk_id=chunk.chunk_id,
                            document_id=document_id,
                            confidence=0.92,
                            metadata={
                                "diagram_id": diagram.diagram_id,
                                "element_id": elem.element_id,
                                "element_type": elem.element_type.value,
                                "bounding_box": elem.bounding_box.to_list(),
                                "source": "cross_modal_linking",
                                "chunk_id": chunk.chunk_id,
                                "chunk_index": chunk.chunk_index,
                            },
                        )
                    )

        return cross_modal_triples

    async def query_multimodal_graph(
        self,
        request: MultimodalGraphQueryRequest,
    ) -> MultimodalGraphResponse:
        """Execute multi-hop graph traversal traversing visual components and textual entities."""
        clean_query = request.entity_query.strip()
        nodes_dict: dict[str, MultimodalGraphNode] = {}
        edges_list: list[MultimodalGraphEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()
        cross_modal_count = 0

        # If graph repository is present, query multi-hop triples
        all_triples: list[EntityTriple] = []
        if self.graph_repository:
            search_result = await self.graph_repository.search_triples(
                tenant_id=request.tenant_id,
                entity=clean_query,
                max_hops=request.max_hops,
            )
            all_triples = search_result.triples

        for t in all_triples:
            meta = t.metadata or {}
            is_visual = meta.get("source") in {"visual_schematic", "cross_modal_linking"}
            is_cross_modal = meta.get("source") == "cross_modal_linking"
            if is_cross_modal:
                cross_modal_count += 1

            # Extract source node
            src_label = t.subject
            src_key = src_label.lower()
            if src_key not in nodes_dict:
                raw_box = meta.get("bounding_box") or meta.get("source_bounding_box")
                box_obj = _to_bounding_box(raw_box)
                nodes_dict[src_key] = MultimodalGraphNode(
                    id=src_key,
                    label=src_label,
                    node_type="visual_component" if is_visual and box_obj else "textual_entity",
                    bounding_box=box_obj,
                    diagram_id=meta.get("diagram_id"),
                    document_id=t.document_id,
                    metadata=meta,
                )

            # Extract target node
            tgt_label = t.object
            tgt_key = tgt_label.lower()
            if tgt_key not in nodes_dict:
                raw_box = meta.get("bounding_box") or meta.get("target_bounding_box")
                box_obj = _to_bounding_box(raw_box)
                nodes_dict[tgt_key] = MultimodalGraphNode(
                    id=tgt_key,
                    label=tgt_label,
                    node_type="visual_component" if is_visual and box_obj else "textual_entity",
                    bounding_box=box_obj,
                    diagram_id=meta.get("diagram_id"),
                    document_id=t.document_id,
                    metadata=meta,
                )

            # Extract edge
            edge_key = (src_key, t.predicate.upper(), tgt_key)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges_list.append(
                    MultimodalGraphEdge(
                        source=src_key,
                        target=tgt_key,
                        relation=t.predicate.upper(),
                        protocol=meta.get("protocol"),
                        is_cross_modal=is_cross_modal,
                        confidence=t.confidence,
                        metadata=meta,
                    )
                )

        # Filter by requested element types if specified
        if request.element_types:
            allowed = {et.value.lower() for et in request.element_types}
            nodes_dict = {
                k: n for k, n in nodes_dict.items() if not n.element_type or n.element_type.value.lower() in allowed
            }

        return MultimodalGraphResponse(
            root_entity=clean_query,
            nodes=list(nodes_dict.values()),
            edges=edges_list,
            cross_modal_links_count=cross_modal_count,
            triples_count=len(all_triples),
            metadata={"max_hops": request.max_hops, "tenant_id": request.tenant_id},
        )

    def format_visual_citation(
        self,
        diagram_filename: str,
        element_label: str,
        bounding_box: list[float] | None = None,
    ) -> str:
        """Format an authentic visual diagram citation with normalized bounding box."""
        if bounding_box and len(bounding_box) == 4:
            box_str = ",".join(f"{coord:.3f}" for coord in bounding_box)
            return f'[Schematic: {diagram_filename} | Box: {box_str} | "{element_label}"]'
        return f'[Schematic: {diagram_filename} | "{element_label}"]'
