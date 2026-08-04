"""Domain service for extracting entity relationship triples from document text chunks."""

import re

from src.domain.abstractions.graph import EntityTriple

# Regular expression pattern to capture Subject-Verb-Object relationships in text
RELATION_PATTERNS = [
    re.compile(
        r"(?P<sub>[A-Z][a-zA-Z0-9_\s]{1,40})\s+(?P<pred>is|uses|leads|manages|built|created|integrates|runs|contains|depends on|owns|maintains|deploys|author of)\s+(?P<obj>[A-Z][a-zA-Z0-9_\s]{1,40})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<sub>[A-Z][a-zA-Z0-9_]{1,30})\s*[:\=]\s*(?P<obj>[A-Z][a-zA-Z0-9_\s]{1,40})",
        re.IGNORECASE,
    ),
]


class GraphExtractor:
    """Extracts entity relationship triples from text chunks during document ingestion."""

    def extract_triples(
        self, text: str, chunk_id: str | None = None
    ) -> list[EntityTriple]:
        """Parse text and extract subject-predicate-object relationship triples."""
        if not text or not text.strip():
            return []

        triples: list[EntityTriple] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            for pattern in RELATION_PATTERNS:
                for match in pattern.finditer(line_str):
                    sub = match.group("sub").strip()
                    pred = (
                        match.group("pred").strip().upper()
                        if "pred" in match.groupdict() and match.group("pred")
                        else "DEFINES"
                    )
                    obj = match.group("obj").strip()

                    if (
                        len(sub) > 1
                        and len(obj) > 1
                        and sub.lower() != obj.lower()
                    ):
                        key = (sub.lower(), pred, obj.lower())
                        if key not in seen_keys:
                            seen_keys.add(key)
                            triples.append(
                                EntityTriple(
                                    subject=sub,
                                    predicate=pred,
                                    object=obj,
                                    chunk_id=chunk_id,
                                    confidence=0.9,
                                )
                            )

        return triples
