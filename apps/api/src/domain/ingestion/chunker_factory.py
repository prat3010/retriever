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

            chunks.append(
                {
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
                }
            )

            chunk_index += 1
            step = max(1, chunk_size - chunk_overlap)
            start_token += step

            # Advance search_start_char slightly for overlapping text
            next_start_tokens = tokens[
                start_token : min(start_token + step, len(tokens))
            ]
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

                chunks.append(
                    {
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
                    }
                )
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

            chunks.append(
                {
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
                }
            )

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
        parent_chunks = self.sliding.split_text_with_offsets(
            text, parent_size, chunk_overlap
        )

        child_size = max(64, chunk_size // 2)
        all_chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for p_idx, p_chunk in enumerate(parent_chunks):
            parent_id = str(uuid.uuid4())
            p_content = p_chunk["content"]
            p_start_char = p_chunk["start_char_idx"]

            # Store Parent Chunk
            all_chunks.append(
                {
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
                }
            )
            chunk_index += 1

            # Sub-chunk parent content into smaller child chunks
            c_sub_chunks = self.sliding.split_text_with_offsets(
                p_content, child_size, max(0, chunk_overlap // 2)
            )

            for c_chunk in c_sub_chunks:
                child_id = str(uuid.uuid4())
                c_start = p_start_char + c_chunk["start_char_idx"]
                c_end = p_start_char + c_chunk["end_char_idx"]

                all_chunks.append(
                    {
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
                    }
                )
                chunk_index += 1

        return all_chunks


class ContextualChunker(BaseChunker):
    """Decorator chunker implementing Anthropic Contextual Retrieval.

    Prepends document-level contextual headers (e.g. document title, summary, or section scope)
    to chunk content before vector embedding to prevent orphan chunk syndrome.
    """

    def __init__(
        self, base_chunker: BaseChunker | None = None, context_prefix: str = ""
    ) -> None:
        self.base_chunker = base_chunker or SlidingChunker()
        self.context_prefix = context_prefix.strip()
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def split_text_with_offsets(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> list[dict[str, Any]]:
        base_chunks = self.base_chunker.split_text_with_offsets(
            text, chunk_size, chunk_overlap
        )
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

            contextual_chunks.append(
                {
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
                }
            )

        return contextual_chunks


class LayoutAwareChunker(BaseChunker):
    """Layout-aware structured chunker preserving tables, forms, and section hierarchy.

    Prevents table mutilation by:
    1. Keeping tables atomic when within chunk bounds.
    2. Slicing oversized tables along row boundaries while re-injecting the header
       and delimiter row into every continuation chunk.
    3. Preserving form/key-value blocks as atomic units.
    4. Propagating heading hierarchy (breadcrumbs) into chunk metadata.
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.encoding = tiktoken.get_encoding(encoding_name)

    def split_text_with_offsets(
        self, text: str, chunk_size: int = 500, chunk_overlap: int = 100
    ) -> list[dict[str, Any]]:
        if not text.strip():
            return []

        chunks: list[dict[str, Any]] = []
        chunk_index = 0
        search_start_char = 0

        # Regex patterns for structural elements
        table_pattern = re.compile(r"^[ \t]*\|(.+)\|[ \t]*$")
        separator_pattern = re.compile(r"^[ \t]*\|([ \t]*:?-+:?[ \t]*\|)+[ \t]*$")
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
        kv_pattern = re.compile(
            r"^[ \t]*([A-Za-z0-9][A-Za-z0-9 _\-\./#]{1,40}?)[ \t]*[:=][ \t]+(.+)$"
        )

        lines = text.splitlines(keepends=True)
        i = 0
        n = len(lines)

        heading_stack: list[str] = []
        pending_headings: list[str] = []

        def add_chunk(
            content: str,
            meta: dict[str, Any],
            override_start_char: int | None = None,
            override_end_char: int | None = None,
        ):
            nonlocal chunk_index, search_start_char
            trimmed_content = content.strip()
            if not trimmed_content:
                return

            if override_start_char is not None and override_end_char is not None and override_start_char >= 0:
                start_char_idx = override_start_char
                end_char_idx = override_end_char
                search_start_char = max(search_start_char, end_char_idx)
            else:
                char_pos = text.find(trimmed_content, search_start_char)
                if char_pos == -1:
                    char_pos = text.find(trimmed_content)
                if char_pos == -1:
                    char_pos = search_start_char
                start_char_idx = char_pos
                end_char_idx = start_char_idx + len(trimmed_content)
                search_start_char = max(search_start_char, end_char_idx)

            token_count = len(self.encoding.encode(trimmed_content))
            meta["strategy"] = "layout_aware"
            if heading_stack:
                meta["section_path"] = " > ".join(heading_stack)

            chunks.append(
                {
                    "content": trimmed_content,
                    "token_count": token_count,
                    "char_count": len(trimmed_content),
                    "chunk_index": chunk_index,
                    "start_char_idx": start_char_idx,
                    "end_char_idx": end_char_idx,
                    "meta_data": meta,
                }
            )
            chunk_index += 1

        while i < n:
            raw_line = lines[i]
            line_stripped = raw_line.strip()

            if not line_stripped:
                i += 1
                continue

            # 1. Heading check
            h_match = heading_pattern.match(line_stripped)
            if h_match:
                level = len(h_match.group(1))
                title = h_match.group(2).strip()
                if level <= len(heading_stack):
                    heading_stack = heading_stack[: level - 1]
                heading_stack.append(title)
                pending_headings.append(line_stripped)
                i += 1
                continue

            # 2. Markdown Table check
            if table_pattern.match(line_stripped):
                table_lines = [line_stripped]
                i += 1
                while i < n and (
                    table_pattern.match(lines[i].strip())
                    or separator_pattern.match(lines[i].strip())
                ):
                    table_lines.append(lines[i].strip())
                    i += 1

                headers: list[str] = []
                if len(table_lines) >= 2:
                    raw_header = table_lines[0].strip().strip("|").split("|")
                    headers = [h.strip() for h in raw_header]

                prefix = ("\n\n".join(pending_headings) + "\n\n") if pending_headings else ""
                pending_headings = []

                full_table_text = prefix + "\n".join(table_lines)
                table_tokens = len(self.encoding.encode(full_table_text))

                if table_tokens <= chunk_size or len(table_lines) <= 3:
                    add_chunk(
                        full_table_text,
                        {
                            "element_type": "table",
                            "is_table": True,
                            "headers": headers,
                            "rows_count": max(0, len(table_lines) - 2),
                        },
                    )
                else:
                    header_line = table_lines[0]
                    separator_line = table_lines[1]
                    header_block = f"{header_line}\n{separator_line}"
                    data_rows = table_lines[2:]
                    header_tokens = len(
                        self.encoding.encode(f"{prefix}{header_block}")
                    )

                    current_rows: list[str] = []
                    current_tokens = header_tokens
                    part_idx = 0

                    for row in data_rows:
                        row_tokens = len(self.encoding.encode(row))
                        if current_tokens + row_tokens > chunk_size and current_rows:
                            part_content = (
                                f"{prefix}{header_block}\n"
                                + "\n".join(current_rows)
                            )
                            row_start = text.find(current_rows[0], search_start_char)
                            if row_start == -1:
                                row_start = text.find(current_rows[0])
                            row_end = (
                                text.find(current_rows[-1], row_start) + len(current_rows[-1])
                                if row_start != -1
                                else None
                            )

                            add_chunk(
                                part_content,
                                {
                                    "element_type": "table",
                                    "is_table": True,
                                    "table_continuation": part_idx > 0,
                                    "part_index": part_idx,
                                    "headers": headers,
                                    "rows_in_chunk": len(current_rows),
                                },
                                override_start_char=row_start if part_idx > 0 else None,
                                override_end_char=row_end if part_idx > 0 else None,
                            )
                            part_idx += 1
                            current_rows = []
                            current_tokens = header_tokens
                            prefix = ""

                        current_rows.append(row)
                        current_tokens += row_tokens

                    if current_rows:
                        part_content = (
                            f"{prefix}{header_block}\n" + "\n".join(current_rows)
                        )
                        row_start = text.find(current_rows[0], search_start_char)
                        if row_start == -1:
                            row_start = text.find(current_rows[0])
                        row_end = (
                            text.find(current_rows[-1], row_start) + len(current_rows[-1])
                            if row_start != -1
                            else None
                        )

                        add_chunk(
                            part_content,
                            {
                                "element_type": "table",
                                "is_table": True,
                                "table_continuation": part_idx > 0,
                                "part_index": part_idx,
                                "headers": headers,
                                "rows_in_chunk": len(current_rows),
                            },
                            override_start_char=row_start if part_idx > 0 else None,
                            override_end_char=row_end if part_idx > 0 else None,
                        )
                continue

            # 3. Form / Key-Value block check (at least 2 consecutive lines)
            if kv_pattern.match(line_stripped):
                kv_lines = [line_stripped]
                next_idx = i + 1
                while (
                    next_idx < n
                    and lines[next_idx].strip()
                    and kv_pattern.match(lines[next_idx].strip())
                ):
                    kv_lines.append(lines[next_idx].strip())
                    next_idx += 1

                if len(kv_lines) >= 2:
                    prefix = ("\n\n".join(pending_headings) + "\n\n") if pending_headings else ""
                    pending_headings = []
                    form_content = prefix + "\n".join(kv_lines)

                    fields: dict[str, str] = {}
                    for kv_line in kv_lines:
                        m = kv_pattern.match(kv_line)
                        if m:
                            fields[m.group(1).strip()] = m.group(2).strip()

                    add_chunk(
                        form_content,
                        {
                            "element_type": "form",
                            "is_form": True,
                            "fields": fields,
                            "field_count": len(fields),
                        },
                    )
                    i = next_idx
                    continue

            # 4. Narrative Paragraphs
            para_lines = []
            if pending_headings:
                para_lines.extend(pending_headings)
                pending_headings = []

            while i < n and lines[i].strip():
                if (
                    heading_pattern.match(lines[i].strip())
                    or table_pattern.match(lines[i].strip())
                    or (
                        kv_pattern.match(lines[i].strip())
                        and i + 1 < n
                        and kv_pattern.match(lines[i + 1].strip())
                    )
                ):
                    break
                para_lines.append(lines[i].strip())
                i += 1

            if para_lines:
                para_text = "\n".join(para_lines)
                para_tokens = len(self.encoding.encode(para_text))
                if para_tokens <= chunk_size:
                    add_chunk(
                        para_text,
                        {"element_type": "narrative"},
                    )
                else:
                    sliding = SlidingChunker()
                    sub_chunks = sliding.split_text_with_offsets(
                        para_text, chunk_size, chunk_overlap
                    )
                    for sc in sub_chunks:
                        add_chunk(
                            sc["content"],
                            {"element_type": "narrative", "sub_chunk": True},
                        )

            if i < n and not lines[i].strip():
                i += 1

        if pending_headings:
            add_chunk("\n\n".join(pending_headings), {"element_type": "heading"})

        return chunks


class ChunkerFactory:
    """Factory to instantiate chunking strategy implementation."""

    @staticmethod
    def get_chunker(strategy: str = "sliding", context_prefix: str = "") -> BaseChunker:
        chunker: BaseChunker
        if strategy == "semantic":
            chunker = SemanticChunker()
        elif strategy == "hierarchical":
            chunker = HierarchicalChunker()
        elif strategy in {"layout_aware", "structured"}:
            chunker = LayoutAwareChunker()
        elif strategy == "contextual":
            chunker = ContextualChunker(SlidingChunker(), context_prefix=context_prefix)
        else:
            chunker = SlidingChunker()

        if context_prefix and not isinstance(chunker, ContextualChunker):
            return ContextualChunker(chunker, context_prefix=context_prefix)
        return chunker

