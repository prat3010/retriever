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
    """Parent-child dual granularity chunker."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.sliding = SlidingChunker(encoding_name)

    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        # Parent chunks (large window)
        parent_size = max(128, chunk_size)
        parent_chunks = self.sliding.split_text_with_offsets(text, parent_size, chunk_overlap)

        child_size = max(64, chunk_size // 2)
        all_chunks: list[dict[str, Any]] = []
        child_index = 0

        for p_idx, p_chunk in enumerate(parent_chunks):
            p_content = p_chunk["content"]
            p_start_char = p_chunk["start_char_idx"]

            # Sub-chunk parent content
            c_sub_chunks = self.sliding.split_text_with_offsets(p_content, child_size, max(0, chunk_overlap // 2))

            for c_chunk in c_sub_chunks:
                c_start = p_start_char + c_chunk["start_char_idx"]
                c_end = p_start_char + c_chunk["end_char_idx"]

                all_chunks.append({
                    "content": c_chunk["content"],
                    "token_count": c_chunk["token_count"],
                    "char_count": len(c_chunk["content"]),
                    "chunk_index": child_index,
                    "start_char_idx": c_start,
                    "end_char_idx": c_end,
                    "meta_data": {
                        "strategy": "hierarchical",
                        "parent_chunk_index": p_idx,
                        "parent_char_start": p_start_char,
                        "parent_char_end": p_chunk["end_char_idx"],
                    },
                })
                child_index += 1

        return all_chunks


class ChunkerFactory:
    """Factory to instantiate chunking strategy implementation."""

    @staticmethod
    def get_chunker(strategy: str = "sliding") -> BaseChunker:
        if strategy == "semantic":
            return SemanticChunker()
        elif strategy == "hierarchical":
            return HierarchicalChunker()
        return SlidingChunker()
