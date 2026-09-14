"""Cognitive infrastructure adapter for schematic visual ingestion and diagram parsing."""

import logging
import struct

from src.domain.abstractions.graph import EntityTriple
from src.domain.abstractions.vision import (
    BaseSchematicExtractor,
    SchematicDiagram,
)
from src.domain.vision.schematic_extractor import DomainSchematicExtractor

logger = logging.getLogger(__name__)


class VisionParserAdapter(BaseSchematicExtractor):
    """Adapter bridging raw binary images, SVGs, and diagram documents to domain schematic models."""

    def __init__(self, extractor: DomainSchematicExtractor | None = None) -> None:
        self.extractor = extractor or DomainSchematicExtractor()

    def _probe_image_dimensions(self, file_content: bytes, mime_type: str) -> tuple[float, float]:
        """Extract intrinsic pixel dimensions from raw image binary headers."""
        if len(file_content) < 24:
            return 1920.0, 1080.0

        try:
            # 1. PNG Header (IHDR chunk at offset 16)
            if file_content.startswith(b"\x89PNG\r\n\x1a\n") and len(file_content) >= 24:
                w, h = struct.unpack(">II", file_content[16:24])
                if w > 0 and h > 0:
                    return float(w), float(h)

            # 2. GIF Header
            if file_content.startswith((b"GIF87a", b"GIF89a")) and len(file_content) >= 10:
                w, h = struct.unpack("<HH", file_content[6:10])
                if w > 0 and h > 0:
                    return float(w), float(h)

            # 3. JPEG SOF markers
            if file_content.startswith(b"\xff\xd8"):
                idx = 2
                length = len(file_content)
                while idx < length - 8:
                    marker, = struct.unpack(">H", file_content[idx:idx + 2])
                    idx += 2
                    if marker in {0xFFC0, 0xFFC2}:  # Baseline / Progressive SOF
                        seg_len, = struct.unpack(">H", file_content[idx:idx + 2])
                        h, w = struct.unpack(">HH", file_content[idx + 3:idx + 7])
                        if w > 0 and h > 0:
                            return float(w), float(h)
                    elif 0xFFD0 <= marker <= 0xFFD9 or marker == 0xFF01:
                        pass
                    else:
                        seg_len, = struct.unpack(">H", file_content[idx:idx + 2])
                        idx += seg_len
        except Exception as exc:
            logger.debug(f"Binary image dimension probe fallback to default canvas: {exc}")

        return 1920.0, 1080.0

    async def extract_schematic(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str = "image/png",
    ) -> SchematicDiagram:
        """Extract structured schematic blueprint from image bytes or SVG vectors."""
        diagram = await self.extractor.extract_schematic(file_content, filename, mime_type)

        # Update dimensions from binary image headers if default
        if not filename.lower().endswith(".svg") and not file_content.strip().startswith(b"<svg"):
            w, h = self._probe_image_dimensions(file_content, mime_type)
            diagram.width = w
            diagram.height = h

        return diagram

    def extract_triples_from_diagram(
        self,
        diagram: SchematicDiagram,
        tenant_id: str,
        document_id: str | None = None,
    ) -> list[EntityTriple]:
        """Delegate triple extraction to domain engine."""
        return self.extractor.extract_triples_from_diagram(diagram, tenant_id, document_id)
