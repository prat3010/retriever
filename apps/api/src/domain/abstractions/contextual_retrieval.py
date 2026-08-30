"""Contextual Retrieval Domain Abstractions.

Hexagonal boundary rule: Only standard library modules and domain abstractions allowed.
Zero infrastructure or external framework imports.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextualChunk:
    """Represents a chunk enriched with document-level contextual header."""

    chunk_id: str
    document_id: str
    tenant_id: str
    raw_content: str
    context_header: str
    contextualized_content: str
    token_count: int
    chunk_index: int
    meta_data: dict[str, Any] = field(default_factory=dict)
    parent_chunk_id: str | None = None


class ContextualHeaderGeneratorPort(ABC):
    """Port for generating situational document context headers for chunks (Anthropic Contextual Retrieval)."""

    @abstractmethod
    async def generate_context_headers(
        self,
        document_text: str,
        chunks: list[str],
        tenant_id: str,
        doc_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Generate contextual headers for a batch of chunks given the whole document text.

        Returns a list of generated context header strings of equal length to chunks.
        """
        pass

    @abstractmethod
    async def generate_context_header_single(
        self,
        document_text: str,
        chunk_content: str,
        tenant_id: str,
        doc_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Generate a contextual header for a single chunk."""
        pass
