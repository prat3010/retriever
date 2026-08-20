"""Chunking strategies and factory implementation for interactive chunking auditor."""

import re
from abc import ABC, abstractmethod
from typing import Any

import tiktoken


class BaseChunker(ABC):
    """Abstract chunker producing structured chunk dictionaries with character offsets."""

    @abstractmethod
    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        """Split text into chunk dictionaries carrying start_char_idx and end_char_idx."""
        pass


class SlidingChunker(BaseChunker):
    """Token-bounded sliding window chunker using tiktoken."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.encoding = tiktoken.get_encoding(encoding_name)

    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        tokens = self.encoding.encode(text)
        chunks: list[dict[str, Any]] = []

        start_token = 0
        chunk_index = 0
        search_start_char = 0

        while start_token < len(tokens):
            end_token = min(start_token + chunk_size, len(tokens))
            chunk_tokens = tokens[start_token:end_token]
            chunk_content = self.encoding.decode(chunk_tokens)

            # Find character position in raw text
            char_pos = text.find(chunk_content, search_start_char)
            if char_pos == -1:
                # Fallback if whitespace encoding mismatch
                char_pos = search_start_char

            start_char_idx = char_pos
            end_char_idx = start_char_idx + len(chunk_content)

            chunks.append({
                "content": chunk_content,
                "token_count": len(chunk_tokens),
                "char_count": len(chunk_content),
                "chunk_index": chunk_index,
                "start_char_idx": start_char_idx,
                "end_char_idx": end_char_idx,
                "meta_data": {
                    "token_start": start_token,
                    "token_end": end_token,
                    "strategy": "sliding",
                },
            })

            chunk_index += 1
            step = max(1, chunk_size - chunk_overlap)
            start_token += step

            # Advance search_start_char slightly for overlapping text
            next_start_tokens = tokens[start_token : min(start_token + step, len(tokens))]
            if next_start_tokens:
                next_prefix = self.encoding.decode(next_start_tokens[:5])
                next_pos = text.find(next_prefix, search_start_char)
                if next_pos != -1:
                    search_start_char = next_pos

        return chunks


class SemanticChunker(BaseChunker):
    """Paragraph and sentence boundary-aware semantic chunker."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.encoding = tiktoken.get_encoding(encoding_name)

    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        # Split into paragraphs / structural units
        paragraphs = re.split(r"(\n\n+)", text)
        units: list[tuple[str, int]] = []
        curr_offset = 0

        for segment in paragraphs:
            if segment:
                units.append((segment, curr_offset))
                curr_offset += len(segment)

        chunks: list[dict[str, Any]] = []
        chunk_index = 0
        current_unit_group: list[tuple[str, int]] = []
        current_tokens = 0

        for unit_text, unit_offset in units:
            unit_toks = len(self.encoding.encode(unit_text))

            if current_tokens + unit_toks > chunk_size and current_unit_group:
                # Flush current chunk
                combined_text = "".join(u[0] for u in current_unit_group)
                start_char = current_unit_group[0][1]
                end_char = start_char + len(combined_text)

                chunks.append({
                    "content": combined_text,
                    "token_count": current_tokens,
                    "char_count": len(combined_text),
                    "chunk_index": chunk_index,
                    "start_char_idx": start_char,
                    "end_char_idx": end_char,
                    "meta_data": {
                        "strategy": "semantic",
                        "units_count": len(current_unit_group),
                    },
                })
                chunk_index += 1
                current_unit_group = []
                current_tokens = 0

            current_unit_group.append((unit_text, unit_offset))
            current_tokens += unit_toks

        # Flush final chunk
        if current_unit_group:
            combined_text = "".join(u[0] for u in current_unit_group)
            start_char = current_unit_group[0][1]
            end_char = start_char + len(combined_text)

            chunks.append({
                "content": combined_text,
                "token_count": current_tokens,
                "char_count": len(combined_text),
                "chunk_index": chunk_index,
                "start_char_idx": start_char,
                "end_char_idx": end_char,
                "meta_data": {
                    "strategy": "semantic",
                    "units_count": len(current_unit_group),
                },
            })

        return chunks


class HierarchicalChunker(BaseChunker):
    """Parent-child dual granularity chunker emitting linked parent and child chunk records."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.sliding = SlidingChunker(encoding_name)

    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        import uuid

        # Parent chunks (large context window: at least 500 tokens or 2x chunk_size)
        parent_size = max(500, chunk_size * 2)
        parent_chunks = self.sliding.split_text_with_offsets(text, parent_size, chunk_overlap)

        child_size = max(64, chunk_size // 2)
        all_chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for p_idx, p_chunk in enumerate(parent_chunks):
            parent_id = str(uuid.uuid4())
            p_content = p_chunk["content"]
            p_start_char = p_chunk["start_char_idx"]

            # Store Parent Chunk
            all_chunks.append({
                "chunk_id": parent_id,
                "parent_chunk_id": None,
                "is_parent": True,
                "content": p_content,
                "token_count": p_chunk["token_count"],
                "char_count": len(p_content),
                "chunk_index": chunk_index,
                "start_char_idx": p_start_char,
                "end_char_idx": p_chunk["end_char_idx"],
                "meta_data": {
                    "strategy": "hierarchical",
                    "role": "parent",
                    "parent_chunk_index": p_idx,
                },
            })
            chunk_index += 1

            # Sub-chunk parent content into smaller child chunks
            c_sub_chunks = self.sliding.split_text_with_offsets(p_content, child_size, max(0, chunk_overlap // 2))

            for c_chunk in c_sub_chunks:
                child_id = str(uuid.uuid4())
                c_start = p_start_char + c_chunk["start_char_idx"]
                c_end = p_start_char + c_chunk["end_char_idx"]

                all_chunks.append({
                    "chunk_id": child_id,
                    "parent_chunk_id": parent_id,
                    "is_parent": False,
                    "content": c_chunk["content"],
                    "token_count": c_chunk["token_count"],
                    "char_count": len(c_chunk["content"]),
                    "chunk_index": chunk_index,
                    "start_char_idx": c_start,
                    "end_char_idx": c_end,
                    "meta_data": {
                        "strategy": "hierarchical",
                        "role": "child",
                        "parent_chunk_id": parent_id,
                        "parent_chunk_index": p_idx,
                        "parent_char_start": p_start_char,
                        "parent_char_end": p_chunk["end_char_idx"],
                    },
                })
                chunk_index += 1

        return all_chunks


class ContextualChunker(BaseChunker):
    """Decorator chunker implementing Anthropic Contextual Retrieval.

    Prepends document-level contextual headers (e.g. document title, summary, or section scope)
    to chunk content before vector embedding to prevent orphan chunk syndrome.
    """

    def __init__(self, base_chunker: BaseChunker | None = None, context_prefix: str = "") -> None:
        self.base_chunker = base_chunker or SlidingChunker()
        self.context_prefix = context_prefix.strip()
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        base_chunks = self.base_chunker.split_text_with_offsets(text, chunk_size, chunk_overlap)
        if not self.context_prefix:
            return base_chunks

        header = f"[Context: {self.context_prefix}]\n\n"
        header_tokens = len(self.encoding.encode(header))
        header_chars = len(header)

        contextual_chunks: list[dict[str, Any]] = []
        for chunk in base_chunks:
            new_content = f"{header}{chunk['content']}"
            new_meta = dict(chunk.get("meta_data", {}))
            new_meta["context_prepended"] = True
            new_meta["context_prefix"] = self.context_prefix

            contextual_chunks.append({
                "chunk_id": chunk.get("chunk_id"),
                "parent_chunk_id": chunk.get("parent_chunk_id"),
                "is_parent": chunk.get("is_parent", False),
                "content": new_content,
                "token_count": chunk["token_count"] + header_tokens,
                "char_count": len(new_content),
                "chunk_index": chunk["chunk_index"],
                "start_char_idx": chunk["start_char_idx"],
                "end_char_idx": chunk["end_char_idx"] + header_chars,
                "meta_data": new_meta,
            })

        return contextual_chunks


class ChunkerFactory:
    """Factory to instantiate chunking strategy implementation."""

    @staticmethod
    def get_chunker(strategy: str = "sliding", context_prefix: str = "") -> BaseChunker:
        chunker: BaseChunker
        if strategy == "semantic":
            chunker = SemanticChunker()
        elif strategy == "hierarchical":
            chunker = HierarchicalChunker()
        elif strategy == "contextual":
            chunker = ContextualChunker(SlidingChunker(), context_prefix=context_prefix)
        else:
            chunker = SlidingChunker()

        if context_prefix and not isinstance(chunker, ContextualChunker):
            return ContextualChunker(chunker, context_prefix=context_prefix)
        return chunker

