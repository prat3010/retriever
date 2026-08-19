"""AST Code-Aware Chunker Adapter for Python, TypeScript, and Markdown files."""

import ast
import re
from typing import Any

from src.domain.abstractions.ingestion import TextChunker


class AstCodeChunker(TextChunker):
    """Chunks source code and markdown documents into logical AST/structural blocks."""

    def split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> list[dict[str, Any]]:
        """Fallback chunker method matching TextChunker signature."""
        return self.chunk_python_ast(text)

    def chunk_python_ast(self, code_text: str, filename: str = "script.py") -> list[dict[str, Any]]:
        """Split Python code into class and function AST nodes preserving complete definitions."""
        chunks: list[dict[str, Any]] = []
        lines = code_text.splitlines()

        try:
            tree = ast.parse(code_text, filename=filename)
        except SyntaxError:
            # Fallback to line-bounded block chunking if AST parsing fails
            return self._fallback_line_chunker(code_text, filename)

        chunk_idx = 0
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                start_line = node.lineno - 1
                end_line = getattr(node, "end_lineno", start_line + 20)
                node_lines = lines[start_line:end_line]
                content = "\n".join(node_lines).strip()

                if content:
                    docstring = ast.get_docstring(node) or ""
                    chunks.append({
                        "content": content,
                        "chunk_index": chunk_idx,
                        "token_count": len(content.split()),
                        "metadata": {
                            "symbol_name": node.name,
                            "symbol_type": node.__class__.__name__,
                            "start_line": node.lineno,
                            "end_line": end_line,
                            "docstring": docstring,
                            "filename": filename,
                        },
                    })
                    chunk_idx += 1
            elif isinstance(node, ast.Assign):
                target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if target_names:
                    start_line = node.lineno - 1
                    end_line = getattr(node, "end_lineno", start_line + 1)
                    content = "\n".join(lines[start_line:end_line]).strip()
                    if content:
                        chunks.append({
                            "content": content,
                            "chunk_index": chunk_idx,
                            "token_count": len(content.split()),
                            "metadata": {
                                "symbol_name": ", ".join(target_names),
                                "symbol_type": "Assignment",
                                "start_line": node.lineno,
                                "end_line": end_line,
                                "filename": filename,
                            },
                        })
                        chunk_idx += 1

        if not chunks and code_text.strip():
            return self._fallback_line_chunker(code_text, filename)

        return chunks

    def chunk_markdown(self, md_text: str, filename: str = "document.md") -> list[dict[str, Any]]:
        """Split Markdown text into sections bounded by headers."""
        chunks: list[dict[str, Any]] = []
        sections = re.split(r"\n(?=#{1,4}\s+)", md_text)
        chunk_idx = 0

        for sec in sections:
            cleaned = sec.strip()
            if not cleaned:
                continue

            header_match = re.match(r"^(#{1,4})\s+(.+)$", cleaned.splitlines()[0])
            title = header_match.group(2) if header_match else f"Section {chunk_idx + 1}"

            chunks.append({
                "content": cleaned,
                "chunk_index": chunk_idx,
                "token_count": len(cleaned.split()),
                "metadata": {
                    "section_title": title,
                    "filename": filename,
                },
            })
            chunk_idx += 1

        return chunks

    def _fallback_line_chunker(self, text: str, filename: str) -> list[dict[str, Any]]:
        lines = text.splitlines()
        chunks = []
        step = 40
        for i in range(0, len(lines), step):
            chunk_lines = lines[i : i + step]
            content = "\n".join(chunk_lines).strip()
            if content:
                chunks.append({
                    "content": content,
                    "chunk_index": len(chunks),
                    "token_count": len(content.split()),
                    "metadata": {"filename": filename, "start_line": i + 1, "end_line": i + len(chunk_lines)},
                })
        return chunks
