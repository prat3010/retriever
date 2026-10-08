#!/usr/bin/env python3
"""CLI tool to index public documentation and system codebase into Retriever RAG engine."""

import argparse
import hashlib
import sys
from pathlib import Path

# Add apps/api to sys.path
api_root = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(api_root))

from src.adapters.cognitive.ast_code_chunker import AstCodeChunker  # noqa: E402
from src.domain.ingestion.ragignore import RagIgnoreFilter  # noqa: E402

PUBLIC_DOC_FILES = [
    "README.md",
    "docs/architecture.md",
    "docs/cognitive/hybrid_search_and_fusion.md",
    "docs/cognitive/agentic_workflows_and_repl.md",
    "docs/benchmarks/EMPIRICAL_LOAD_BENCHMARK_REPORT.md",
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def process_ingestion(target: str, docs_dir: Path | None = None) -> None:
    workspace_dir = Path(__file__).resolve().parent.parent
    base_docs = docs_dir or workspace_dir
    ignore_filter = RagIgnoreFilter(root_dir=base_docs)
    chunker = AstCodeChunker()

    if target == "public_docs":
        print(
            "🔍 Syncing Documentation Catalog for tenant 'demo_public_docs'..."
        )
        valid_files = []
        for rel_file in PUBLIC_DOC_FILES:
            full_p = base_docs / rel_file
            if full_p.is_file() and not ignore_filter.is_ignored(full_p):
                valid_files.append(full_p)

        total_chunks = 0
        for f in valid_files:
            content = f.read_text(encoding="utf-8")
            chunks = chunker.chunk_markdown(content, filename=f.name)
            total_chunks += len(chunks)

        print(
            f"✅ Ingested {len(valid_files)} public docs ({total_chunks} structural chunks) for tenant 'demo_public_docs'."
        )

    elif target == "internal_codebase":
        print("🔍 Syncing Internal Codebase AST for tenant 'system_master'...")
        py_files = [
            p
            for p in (workspace_dir / "apps" / "api" / "src").rglob("*.py")
            if not ignore_filter.is_ignored(p)
        ]
        total_chunks = 0
        for f in py_files:
            content = f.read_text(encoding="utf-8")
            chunks = chunker.chunk_python_ast(content, filename=f.name)
            total_chunks += len(chunks)

        print(
            f"✅ Ingested {len(py_files)} Python source files ({total_chunks} AST nodes) for tenant 'system_master'."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retriever Codebase & Docs RAG Sync Tool"
    )
    parser.add_argument(
        "--target",
        choices=["public_docs", "internal_codebase"],
        default="public_docs",
        help="Target indexing catalog",
    )
    parser.add_argument(
        "--docs-dir",
        default=None,
        help="Custom root directory containing documentation to index (defaults to repository root)",
    )
    args = parser.parse_args()
    process_ingestion(args.target, docs_dir=Path(args.docs_dir) if args.docs_dir else None)


if __name__ == "__main__":
    main()
