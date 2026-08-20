"""Knowledge Graph Triples Auto-Synthesis Service.

Extracts subject-predicate-object entity triples from document text chunks during ingestion,
enabling multi-hop entity graph traversal and GraphRAG evidence fusion.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityTriple:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphExtractionService:
    """Service for auto-extracting knowledge graph entity triples from text chunks."""

    TRIPLE_REGEX = re.compile(
        r"([A-Z][a-zA-Z0-9_\-\s]{1,30})\s+(is|has|uses|leads|built|supports|manages|requires|implements|extends|belongs to|relates to|contains|depends on)\s+([A-Z0-9][a-zA-Z0-9_\-\s]{1,30})",
        re.IGNORECASE,
    )

    def extract_triples(self, text: str, chunk_id: str | None = None) -> list[EntityTriple]:
        """Extract subject-predicate-object triples from plain text content."""
        if not text or not text.strip():
            return []

        triples: list[EntityTriple] = []
        seen: set[tuple[str, str, str]] = set()

        for match in self.TRIPLE_REGEX.finditer(text):
            sub, pred, obj = match.group(1).strip(), match.group(2).strip().upper(), match.group(3).strip()
            key = (sub.lower(), pred, obj.lower())
            if key not in seen and len(sub) > 1 and len(obj) > 1:
                seen.add(key)
                triples.append(
                    EntityTriple(
                        subject=sub,
                        predicate=pred,
                        object=obj,
                        confidence=0.85,
                        metadata={"chunk_id": chunk_id} if chunk_id else {},
                    )
                )

        return triples

    def format_triples_for_graph_store(self, tenant_id: str, document_id: str, chunk_id: str, triples: list[EntityTriple]) -> list[dict[str, Any]]:
        """Format extracted triples for bulk insertion into graph_triples database table."""
        return [
            {
                "tenant_id": str(tenant_id),
                "document_id": str(document_id),
                "chunk_id": str(chunk_id),
                "subject": t.subject,
                "predicate": t.predicate,
                "object": t.object,
                "confidence": t.confidence,
                "metadata": t.metadata,
            }
            for t in triples
        ]


GraphExtractor = GraphExtractionService

