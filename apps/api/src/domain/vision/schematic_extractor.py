"""Pure domain engine for architectural schematic extraction and visual topology resolution.

Hexagonal boundary rule: Pure mathematical domain logic.
Only standard library modules and domain abstractions allowed.
Zero database, ORM, framework, or external HTTP imports.
"""

import math
import re
import uuid
import xml.etree.ElementTree as ET
from typing import ClassVar

from src.domain.abstractions.graph import EntityTriple
from src.domain.abstractions.vision import (
    BaseSchematicExtractor,
    BoundingBox,
    SchematicDiagram,
    VisualConnector,
    VisualElement,
    VisualElementType,
)


class DomainSchematicExtractor(BaseSchematicExtractor):
    """Hexagonal domain engine parsing vector/layout diagrams into structured schematic topologies."""

    # Architectural ontology keywords mapping extracted labels to visual element types
    TYPE_ONTOLOGY: ClassVar[dict[VisualElementType, tuple[str, ...]]] = {
        VisualElementType.GATEWAY: (
            "gateway",
            "ingress",
            "reverse proxy",
            "proxy",
            "load balancer",
            "alb",
            "nlb",
            "cloudflare",
            "envoy",
            "nginx",
            "traefik",
            "cdn",
            "edge",
        ),
        VisualElementType.DATABASE: (
            "database",
            "postgres",
            "postgresql",
            "mysql",
            "mariadb",
            "mongodb",
            "neo4j",
            "sqlite",
            "rds",
            "dynamodb",
            "cockroach",
            "firestore",
            "pgvector",
        ),
        VisualElementType.CACHE: (
            "redis",
            "memcached",
            "valkey",
            "cache",
            "l1 cache",
            "l2 cache",
        ),
        VisualElementType.QUEUE: (
            "kafka",
            "rabbitmq",
            "sqs",
            "nats",
            "celery",
            "event bus",
            "pubsub",
            "queue",
            "broker",
        ),
        VisualElementType.ACTOR: (
            "user",
            "client",
            "browser",
            "mobile",
            "admin",
            "operator",
            "frontend",
            "customer",
            "caller",
        ),
        VisualElementType.DATA_STORE: (
            "s3",
            "bucket",
            "blob",
            "storage",
            "vault",
            "lakehouse",
            "gcs",
            "r2",
        ),
        VisualElementType.SERVICE: (
            "service",
            "api",
            "worker",
            "backend",
            "engine",
            "orchestrator",
            "copilot",
            "agent",
            "model",
            "fastapi",
            "node",
            "microservice",
        ),
    }

    PROTOCOL_KEYWORDS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("https", "HTTPS"),
        ("http", "HTTP"),
        ("grpc", "gRPC"),
        ("rest", "REST"),
        ("sql", "SQL"),
        ("amqp", "AMQP"),
        ("websocket", "WebSocket"),
        ("wss", "WSS"),
        ("tcp", "TCP"),
        ("sse", "SSE"),
        ("kafka", "Kafka Event"),
    )

    async def extract_schematic(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str = "image/png",
    ) -> SchematicDiagram:
        """Parse diagram bytes (SVG XML, JSON-topology, or text layout) into a structured SchematicDiagram."""
        diagram_id = f"diag_{uuid.uuid4().hex[:12]}"
        is_svg = filename.lower().endswith(".svg") or "svg" in mime_type.lower()

        if is_svg or file_content.strip().startswith(b"<svg"):
            return self.parse_svg_schematic(file_content.decode("utf-8", errors="ignore"), diagram_id, filename)

        # Non-SVG files (PNG/JPG layout metadata or plain structured blueprint description)
        text_content = file_content.decode("utf-8", errors="ignore")
        return self.parse_text_layout_schematic(text_content, diagram_id, filename)

    def parse_svg_schematic(
        self,
        svg_xml: str,
        diagram_id: str,
        filename: str,
    ) -> SchematicDiagram:
        """Parse vector SVG canvas extracting shapes as components and lines/paths as connectors."""
        width = 1920.0
        height = 1080.0

        try:
            # Strip XML namespace prefixes for robust standard library parsing
            clean_xml = re.sub(r'\sxmlns="[^"]+"', "", svg_xml, count=1)
            root = ET.fromstring(clean_xml)

            viewbox = root.attrib.get("viewBox") or root.attrib.get("viewbox")
            if viewbox:
                parts = [float(p) for p in re.split(r"[\s,]+", viewbox.strip()) if p]
                if len(parts) >= 4:
                    width = parts[2]
                    height = parts[3]
            else:
                width = float(root.attrib.get("width", 1920.0))
                height = float(root.attrib.get("height", 1080.0))
        except Exception:
            root = None

        if root is None or width <= 0.0 or height <= 0.0:
            width = 1920.0
            height = 1080.0

        elements: list[VisualElement] = []
        element_id_counter = 0

        # Heuristic 1: Extract <rect>, <circle>, <g> with labels or nested text
        if root is not None:
            for elem in root.iter():
                tag = elem.tag.lower().split("}")[-1]

                if tag in {"rect", "circle", "g", "ellipse"}:
                    # Look for associated label in text child or title or id
                    label = elem.attrib.get("id", "").replace("_", " ").strip()
                    nested_text = "".join(elem.itertext()).strip()
                    if nested_text:
                        label = nested_text

                    if not label or len(label) < 2 or label.lower() in {"canvas", "layer", "background"}:
                        continue

                    # Extract coordinates
                    x = float(elem.attrib.get("x", 0.0))
                    y = float(elem.attrib.get("y", 0.0))
                    w = float(elem.attrib.get("width", 160.0))
                    h = float(elem.attrib.get("height", 80.0))

                    if tag == "circle":
                        cx = float(elem.attrib.get("cx", 0.0))
                        cy = float(elem.attrib.get("cy", 0.0))
                        r = float(elem.attrib.get("r", 40.0))
                        x, y, w, h = cx - r, cy - r, r * 2, r * 2

                    ymin = max(0.0, min(1.0, y / height))
                    xmin = max(0.0, min(1.0, x / width))
                    ymax = max(ymin + 0.01, min(1.0, (y + h) / height))
                    xmax = max(xmin + 0.01, min(1.0, (x + w) / width))

                    element_id_counter += 1
                    el_id = f"elem_{element_id_counter}"
                    el_type = self.classify_label(label)

                    elements.append(
                        VisualElement(
                            element_id=el_id,
                            label=label,
                            element_type=el_type,
                            bounding_box=BoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax, confidence=0.95),
                            properties={"svg_tag": tag},
                        )
                    )

        # Fallback if no SVG shapes with text were detected: parse text lines
        if not elements:
            elements = self._extract_fallback_components(svg_xml, width, height)

        # Deduplicate overlapping bounding boxes (IoU > 0.8)
        elements = self._deduplicate_elements(elements)

        # Resolve connectors between visual elements
        connectors = self._resolve_connectors(elements, svg_xml)

        summary = self._synthesize_narrative(elements, connectors, filename)

        return SchematicDiagram(
            diagram_id=diagram_id,
            filename=filename,
            width=width,
            height=height,
            elements=elements,
            connectors=connectors,
            summary=summary,
        )

    def parse_text_layout_schematic(
        self,
        content: str,
        diagram_id: str,
        filename: str,
    ) -> SchematicDiagram:
        """Parse structured architecture description, ASCII boxes, or textual flowcharts."""
        width = 1920.0
        height = 1080.0

        elements: list[VisualElement] = []
        connectors: list[VisualConnector] = []
        element_map: dict[str, VisualElement] = {}

        # Scan for explicit flow definitions: [Component A] -->|HTTPS| [Component B], [A] -> [B], or A -> B
        bracket_pat = re.compile(
            r"\[([^\]]+)\]\s*[-=.]+(?:\|([^|]+)\|)?[-=.]*>\s*(?:\|([^|]+)\|)?\s*\[([^\]]+)\]"
        )
        plain_pat = re.compile(
            r"([A-Z][a-zA-Z0-9_\s]{1,30})\s*(?:--?>|->)\s*([A-Z][a-zA-Z0-9_\s]{1,30})"
        )

        counter = 0
        raw_edges: list[tuple[str, str, str]] = []

        for match in bracket_pat.finditer(content):
            src = match.group(1).strip()
            edge = (match.group(2) or match.group(3) or "").strip()
            tgt = match.group(4).strip()
            if src and tgt:
                raw_edges.append((src, edge, tgt))

        if not raw_edges:
            for match in plain_pat.finditer(content):
                src = match.group(1).strip()
                tgt = match.group(2).strip()
                if src and tgt and not src.startswith("[") and not tgt.endswith("]"):
                    raw_edges.append((src, "", tgt))

        # Collect unique component labels
        unique_labels: set[str] = set()
        for src, _, tgt in raw_edges:
            unique_labels.add(src)
            unique_labels.add(tgt)

        # If no flow patterns, extract capitalized technical terms
        if not unique_labels:
            candidates = re.findall(r"\b([A-Z][a-zA-Z0-9]{2,}(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", content)
            for cand in candidates:
                cand_clean = cand.strip()
                if len(cand_clean) > 3 and self.classify_label(cand_clean) != VisualElementType.UNKNOWN:
                    unique_labels.add(cand_clean)

        # Position elements on a canonical 2D topological grid
        total = max(1, len(unique_labels))
        cols = math.ceil(math.sqrt(total * 1.5))
        rows = math.ceil(total / cols) if cols > 0 else 1

        for idx, label in enumerate(sorted(unique_labels)):
            counter += 1
            el_id = f"elem_{counter}"
            el_type = self.classify_label(label)

            col = idx % cols
            row = idx // cols

            # Normalized grid layout with spacing
            box_w = 0.85 / max(cols, 1)
            box_h = 0.85 / max(rows, 1)

            xmin = 0.08 + col * (box_w + 0.02)
            ymin = 0.08 + row * (box_h + 0.02)
            xmax = min(1.0, xmin + box_w)
            ymax = min(1.0, ymin + box_h)

            el = VisualElement(
                element_id=el_id,
                label=label,
                element_type=el_type,
                bounding_box=BoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax, confidence=0.90),
            )
            elements.append(el)
            element_map[label.lower()] = el

        # Wire connectors
        conn_counter = 0
        for src_label, edge_label, tgt_label in raw_edges:
            src_el = element_map.get(src_label.lower())
            tgt_el = element_map.get(tgt_label.lower())
            if src_el and tgt_el and src_el.element_id != tgt_el.element_id:
                conn_counter += 1
                protocol = self._infer_protocol(edge_label)
                connectors.append(
                    VisualConnector(
                        connector_id=f"conn_{conn_counter}",
                        source_element_id=src_el.element_id,
                        target_element_id=tgt_el.element_id,
                        label=edge_label or (protocol or "ROUTES_TO"),
                        directionality="directed",
                        protocol=protocol,
                        confidence=0.95,
                    )
                )

        summary = self._synthesize_narrative(elements, connectors, filename)

        return SchematicDiagram(
            diagram_id=diagram_id,
            filename=filename,
            width=width,
            height=height,
            elements=elements,
            connectors=connectors,
            summary=summary,
        )

    def classify_label(self, label: str) -> VisualElementType:
        """Classify visual element label into semantic architecture categories."""
        clean = label.lower().strip()
        for el_type, keywords in self.TYPE_ONTOLOGY.items():
            for kw in keywords:
                if kw in clean:
                    return el_type
        return VisualElementType.SERVICE if len(clean) > 2 else VisualElementType.UNKNOWN

    def _infer_protocol(self, label: str) -> str | None:
        """Extract network protocol identifier from connector text label."""
        if not label:
            return None
        low = label.lower()
        for kw, proto in self.PROTOCOL_KEYWORDS:
            if kw in low:
                return proto
        return None

    def _extract_fallback_components(self, text: str, width: float, height: float) -> list[VisualElement]:
        """Extract text tokens and bounding positions as fallback components."""
        matches = re.findall(r"<text[^>]*x=[\"']([\d\.]+)[\"'][^>]*y=[\"']([\d\.]+)[\"'][^>]*>([^<]+)</text>", text)
        elements = []
        counter = 0
        for x_str, y_str, label in matches:
            clean_label = label.strip()
            if len(clean_label) < 2:
                continue
            counter += 1
            x = float(x_str)
            y = float(y_str)
            ymin = max(0.0, min(1.0, (y - 30.0) / height))
            xmin = max(0.0, min(1.0, (x - 20.0) / width))
            ymax = max(ymin + 0.01, min(1.0, (y + 30.0) / height))
            xmax = max(xmin + 0.01, min(1.0, (x + 180.0) / width))

            elements.append(
                VisualElement(
                    element_id=f"elem_{counter}",
                    label=clean_label,
                    element_type=self.classify_label(clean_label),
                    bounding_box=BoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax, confidence=0.85),
                )
            )
        return elements

    def _deduplicate_elements(self, elements: list[VisualElement]) -> list[VisualElement]:
        """Remove duplicate detected visual elements with high bounding-box IoU overlap."""
        unique: list[VisualElement] = []
        for el in elements:
            is_dup = False
            for u in unique:
                if el.label.lower() == u.label.lower() or el.bounding_box.iou(u.bounding_box) > 0.8:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(el)
        return unique

    def _resolve_connectors(self, elements: list[VisualElement], svg_content: str) -> list[VisualConnector]:
        """Infer directional connectors by matching vector line paths between visual elements."""
        connectors: list[VisualConnector] = []
        if len(elements) < 2:
            return connectors

        # Heuristic 1: Extract SVG line / path coordinates
        line_matches = re.findall(
            r"<line[^>]*x1=[\"']([\d\.]+)[\"'][^>]*y1=[\"']([\d\.]+)[\"'][^>]*x2=[\"']([\d\.]+)[\"'][^>]*y2=[\"']([\d\.]+)[\"']",
            svg_content,
        )

        conn_counter = 0
        for x1_s, y1_s, x2_s, y2_s in line_matches:
            x1, y1 = float(x1_s), float(y1_s)
            x2, y2 = float(x2_s), float(y2_s)

            # Find closest element to (x1, y1) and (x2, y2)
            src = self._find_closest_element(x1, y1, elements)
            tgt = self._find_closest_element(x2, y2, elements)

            if src and tgt and src.element_id != tgt.element_id:
                conn_counter += 1
                connectors.append(
                    VisualConnector(
                        connector_id=f"conn_{conn_counter}",
                        source_element_id=src.element_id,
                        target_element_id=tgt.element_id,
                        label="CONNECTS_TO",
                        directionality="directed",
                        confidence=0.85,
                    )
                )

        # Fallback if no SVG lines: connect gateways to services, services to databases/caches
        if not connectors:
            gateways = [e for e in elements if e.element_type == VisualElementType.GATEWAY]
            services = [e for e in elements if e.element_type == VisualElementType.SERVICE]
            datastores = [
                e
                for e in elements
                if e.element_type in {VisualElementType.DATABASE, VisualElementType.CACHE, VisualElementType.QUEUE}
            ]

            for gw in gateways:
                for svc in services:
                    conn_counter += 1
                    connectors.append(
                        VisualConnector(
                            connector_id=f"conn_{conn_counter}",
                            source_element_id=gw.element_id,
                            target_element_id=svc.element_id,
                            label="ROUTES_TO",
                            protocol="HTTPS",
                            confidence=0.90,
                        )
                    )

            for svc in services:
                for ds in datastores:
                    conn_counter += 1
                    proto = "SQL" if ds.element_type == VisualElementType.DATABASE else "TCP"
                    connectors.append(
                        VisualConnector(
                            connector_id=f"conn_{conn_counter}",
                            source_element_id=svc.element_id,
                            target_element_id=ds.element_id,
                            label="PERSISTS_IN" if ds.element_type == VisualElementType.DATABASE else "STORES_IN",
                            protocol=proto,
                            confidence=0.90,
                        )
                    )

        return connectors

    def _find_closest_element(self, x: float, y: float, elements: list[VisualElement]) -> VisualElement | None:
        """Find the visual element whose bounding box center is closest to a coordinate."""
        closest = None
        min_dist = float("inf")

        for el in elements:
            cx = (el.bounding_box.xmin + el.bounding_box.xmax) / 2.0 * 1920.0
            cy = (el.bounding_box.ymin + el.bounding_box.ymax) / 2.0 * 1080.0
            dist = math.hypot(x - cx, y - cy)
            if dist < min_dist:
                min_dist = dist
                closest = el

        return closest if min_dist < 400.0 else None

    def _synthesize_narrative(
        self,
        elements: list[VisualElement],
        connectors: list[VisualConnector],
        filename: str,
    ) -> str:
        """Synthesize an algorithmic summary of the architectural schematic topology."""
        el_by_id = {e.element_id: e for e in elements}
        counts: dict[VisualElementType, int] = {}
        for e in elements:
            counts[e.element_type] = counts.get(e.element_type, 0) + 1

        parts = [
            f"Schematic blueprint '{filename}' defines an architecture with {len(elements)} visual components and {len(connectors)} communication flows."
        ]

        # Breakdown summary
        type_summaries = []
        for t, count in sorted(counts.items(), key=lambda x: x[0].value):
            type_summaries.append(f"{count} {t.value}(s)")
        if type_summaries:
            parts.append("Identified entities: " + ", ".join(type_summaries) + ".")

        # Key flows
        flow_samples = []
        for c in connectors[:5]:
            src = el_by_id.get(c.source_element_id)
            tgt = el_by_id.get(c.target_element_id)
            if src and tgt:
                proto_str = f" via {c.protocol}" if c.protocol else ""
                flow_samples.append(f"{src.label} --[{c.label}{proto_str}]--> {tgt.label}")

        if flow_samples:
            parts.append("Core topology paths: " + "; ".join(flow_samples) + ".")

        return " ".join(parts)

    def extract_triples_from_diagram(
        self,
        diagram: SchematicDiagram,
        tenant_id: str,
        document_id: str | None = None,
    ) -> list[EntityTriple]:
        """Convert diagram elements and directional connectors into EntityTriples with visual provenance."""
        triples: list[EntityTriple] = []
        el_by_id = {e.element_id: e for e in diagram.elements}

        # 1. Connectors as relational triples
        for conn in diagram.connectors:
            src = el_by_id.get(conn.source_element_id)
            tgt = el_by_id.get(conn.target_element_id)
            if not src or not tgt:
                continue

            pred = conn.label.strip().replace(" ", "_").upper() or "CONNECTS_TO"
            triples.append(
                EntityTriple(
                    triple_id=f"triple_{uuid.uuid4().hex[:12]}",
                    subject=src.label,
                    predicate=pred,
                    object=tgt.label,
                    document_id=document_id or diagram.document_id,
                    confidence=min(src.confidence, tgt.confidence, conn.confidence),
                    metadata={
                        "diagram_id": diagram.diagram_id,
                        "source": "visual_schematic",
                        "protocol": conn.protocol,
                        "source_bounding_box": src.bounding_box.to_list(),
                        "target_bounding_box": tgt.bounding_box.to_list(),
                        "directionality": conn.directionality,
                    },
                )
            )

        # 2. Component ontological classification triples
        for elem in diagram.elements:
            if elem.element_type != VisualElementType.UNKNOWN:
                triples.append(
                    EntityTriple(
                        triple_id=f"triple_{uuid.uuid4().hex[:12]}",
                        subject=elem.label,
                        predicate="IS_TYPE",
                        object=elem.element_type.value.upper(),
                        document_id=document_id or diagram.document_id,
                        confidence=elem.confidence,
                        metadata={
                            "diagram_id": diagram.diagram_id,
                            "source": "visual_schematic",
                            "bounding_box": elem.bounding_box.to_list(),
                        },
                    )
                )

        return triples
