#!/usr/bin/env python3
"""
Retriever — High-Performance M4 Local Embedding & Supabase Vector Ingestor
==========================================================================
Uses Apple M4 Metal GPU acceleration for layout-aware chunking and batch
embedding with nomic-embed-text (2026 standards), then streams documents,
chunks, and dense 768-dim vectors directly into Supabase pgvector.

Usage:
    PYTHONPATH=apps/api uv run python scripts/ingest_tenant_corpus.py
"""

import asyncio
import hashlib
import json
from pathlib import Path
import os
import sys
import time
import uuid

import asyncpg
import pgvector.asyncpg

# Ensure apps/api is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
API_SRC = REPO_ROOT / "apps" / "api"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from src.adapters.cognitive.ollama_embedding_adapter import OllamaEmbeddingAdapter  # noqa: E402
from src.domain.ingestion.chunker_factory import ChunkerFactory  # noqa: E402

# Terminal styling
BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
MAGENTA = "\033[0;35m"
RED = "\033[0;31m"
DIM = "\033[2m"
NC = "\033[0m"

DB_URL = (
    os.environ.get("DATABASE_DIRECT_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql://localhost:5432/retriever"
).replace("postgresql+asyncpg://", "postgresql://")


def discover_tenant_bundles(tenants_dir: Path) -> list[dict]:
    """Dynamically discover tenant bundles with tenant.json manifests."""
    bundles = []
    if tenants_dir.is_dir():
        for entry in sorted(tenants_dir.iterdir()):
            manifest = entry / "tenant.json"
            if entry.is_dir() and manifest.is_file():
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    docs_dir = entry / "documents" if (entry / "documents").is_dir() else entry
                    bundles.append({
                        "name": data.get("name", entry.name),
                        "tenant_id": uuid.UUID(str(data["tenant_id"])),
                        "dir": docs_dir,
                    })
                except Exception as err:
                    print(f"  ⚠️ Skipping {entry.name}: {err}")
    return bundles


async def ingest_tenant(
    conn: asyncpg.Connection,
    tenant_info: dict,
    embedder: OllamaEmbeddingAdapter,
    chunker,
) -> dict:
    t_name = tenant_info["name"]
    t_id = tenant_info["tenant_id"]
    source_dir: Path = tenant_info["dir"]

    print(f"\n{CYAN}{BOLD}📂 Processing Tenant: {t_name}{NC}")
    print(f"   UUID: {DIM}{t_id}{NC}")
    print(f"   Directory: {source_dir.relative_to(REPO_ROOT)}")

    files = sorted(source_dir.glob("*.md"))
    if not files:
        print(f"   {YELLOW}No markdown files found in {source_dir}{NC}")
        return {"docs": 0, "chunks": 0, "vectors": 0}

    tenant_docs_to_insert = []
    tenant_chunks_to_insert = []
    tenant_chunk_texts = []
    chunk_to_doc_map = []

    print(f"   Found {len(files)} markdown document(s). Parsing structure...")

    for f in files:
        content = f.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        doc_id = uuid.uuid4()
        file_size = len(content.encode("utf-8"))

        raw_chunks = chunker.split_text_with_offsets(content, 500, 100)
        prefix = f"[Document: {f.name}]\n"

        tenant_docs_to_insert.append(
            (
                doc_id,
                t_id,
                f.name,
                file_hash,
                f"tenants/{t_id}/{f.name}",
                file_size,
                "text/markdown",
                "INDEXED",
                ["2026_corpus", "layout_aware"],
                False,
            )
        )

        for idx, c in enumerate(raw_chunks):
            chunk_id = uuid.uuid4()
            raw_content = c["content"]
            chunk_content = (
                f"{prefix}{raw_content}"
                if not raw_content.startswith("[Document:")
                else raw_content
            )
            meta = c.get("metadata") or {}
            meta_json = json.dumps(meta)

            tenant_chunks_to_insert.append(
                (
                    chunk_id,
                    doc_id,
                    t_id,
                    chunk_content,
                    len(chunk_content.split()),
                    idx,
                    None,  # parent_chunk_id
                    meta_json,
                )
            )
            tenant_chunk_texts.append(chunk_content)
            chunk_to_doc_map.append((chunk_id, doc_id))

        print(
            f"   • {f.name:50s} → {len(raw_chunks):2d} layout-aware chunks ({file_size / 1024:.1f} KB)"
        )

    print(
        f"\n   ⚡ {MAGENTA}Generating 768-dim embeddings via Apple M4 GPU (Ollama Metal)...{NC}"
    )
    t_embed_start = time.time()
    embeddings = await embedder.embed_batch(tenant_chunk_texts)
    t_embed_end = time.time()
    embed_duration = t_embed_end - t_embed_start
    print(
        f"   {GREEN}✓ Generated {len(embeddings)} normalized vectors in {embed_duration:.2f}s "
        f"({(embed_duration / len(embeddings)) * 1000:.1f}ms/chunk)!{NC}"
    )

    tenant_vectors_to_insert = []
    for (chunk_id, _), emb in zip(chunk_to_doc_map, embeddings, strict=True):
        tenant_vectors_to_insert.append((chunk_id, t_id, emb))

    print("   💾 Inserting records directly into Supabase pgvector...")
    t_db_start = time.time()

    async with conn.transaction():
        # 1. Insert documents
        await conn.executemany(
            """
            INSERT INTO public.documents (
                document_id, tenant_id, filename, file_hash, storage_path,
                file_size, mime_type, status, tags, is_deleted, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now(), now())
            """,
            tenant_docs_to_insert,
        )

        # 2. Insert document chunks
        await conn.executemany(
            """
            INSERT INTO public.document_chunks (
                chunk_id, document_id, tenant_id, content, token_count,
                chunk_index, parent_chunk_id, meta_data, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, now())
            """,
            tenant_chunks_to_insert,
        )

        # 3. Insert vector records
        await conn.executemany(
            """
            INSERT INTO public.vector_records (
                chunk_id, tenant_id, embedding, created_at
            ) VALUES ($1, $2, $3, now())
            """,
            tenant_vectors_to_insert,
        )

    t_db_end = time.time()
    print(
        f"   {GREEN}✓ Committed {len(tenant_docs_to_insert)} documents, "
        f"{len(tenant_chunks_to_insert)} chunks, and "
        f"{len(tenant_vectors_to_insert)} vectors to Supabase in {t_db_end - t_db_start:.2f}s!{NC}"
    )

    return {
        "docs": len(tenant_docs_to_insert),
        "chunks": len(tenant_chunks_to_insert),
        "vectors": len(tenant_vectors_to_insert),
    }


async def main():
    print(f"\n{BOLD}{CYAN}======================================================================{NC}")
    print(f"{BOLD}{CYAN}🚀 Retriever — M4 Apple Silicon & Supabase pgvector Ingestion Engine{NC}")
    print(f"{BOLD}{CYAN}======================================================================{NC}")

    t_total_start = time.time()

    print(f"🔌 Connecting to Supabase PostgreSQL at {DB_URL.split('@')[-1]}...")
    conn = await asyncpg.connect(DB_URL, ssl="require")
    await pgvector.asyncpg.register_vector(conn)
    print(f"{GREEN}✓ Connected and pgvector type codec registered.{NC}")

    chunker = ChunkerFactory.get_chunker("layout_aware")
    embedder = OllamaEmbeddingAdapter(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
        batch_size=32,
    )

    total_stats = {"docs": 0, "chunks": 0, "vectors": 0}

    tenants = discover_tenant_bundles(REPO_ROOT / "data" / "tenants")
    if not tenants:
        print(f"{YELLOW}No tenant bundles with tenant.json found in data/tenants/{NC}")

    try:
        for tenant_info in tenants:
            stats = await ingest_tenant(conn, tenant_info, embedder, chunker)
            total_stats["docs"] += stats["docs"]
            total_stats["chunks"] += stats["chunks"]
            total_stats["vectors"] += stats["vectors"]
    finally:
        await embedder.client.aclose()
        await conn.close()

    t_total_end = time.time()
    print(f"\n{BOLD}{CYAN}======================================================================{NC}")
    print(f"{BOLD}{GREEN}🎉 ALL INGESTION COMPLETED SUCCESSFULLY IN {t_total_end - t_total_start:.2f}s!{NC}")
    print(f"   • Total Documents Indexed: {BOLD}{total_stats['docs']}{NC}")
    print(f"   • Total Layout Chunks:     {BOLD}{total_stats['chunks']}{NC}")
    print(f"   • Total 768-Dim Vectors:   {BOLD}{total_stats['vectors']}{NC}")
    print(f"{BOLD}{CYAN}======================================================================{NC}\n")


if __name__ == "__main__":
    asyncio.run(main())
