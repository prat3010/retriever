"""Verify System Memory Script for Retriever Meta-RAG.

Queries System Tenant `00000000-0000-0000-0000-000000000000` stats and executes
a test hybrid vector search over ingested codebase ASTs, documentation, and ADRs.
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

from sqlalchemy import func, select

# Ensure apps/api root is on sys.path
API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentChunkDb, DocumentDb, VectorRecordDb
from src.adapters.vector.vector_repository import PgVectorSearchAdapter
from src.scripts.ingest_system_memory import (
    SYSTEM_TENANT_ID,
    generate_fallback_embedding,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_system_memory")


async def verify_stats() -> dict[str, int]:
    """Retrieve System Tenant document, chunk, and vector counts."""
    async with tenant_session(tenant_id=SYSTEM_TENANT_ID, bypass_rls=True) as session:
        doc_count = (await session.execute(
            select(func.count()).select_from(DocumentDb).where(DocumentDb.tenant_id == uuid.UUID(SYSTEM_TENANT_ID))
        )).scalar() or 0

        chunk_count = (await session.execute(
            select(func.count()).select_from(DocumentChunkDb).where(DocumentChunkDb.tenant_id == uuid.UUID(SYSTEM_TENANT_ID))
        )).scalar() or 0

        vector_count = (await session.execute(
            select(func.count()).select_from(VectorRecordDb).where(VectorRecordDb.tenant_id == uuid.UUID(SYSTEM_TENANT_ID))
        )).scalar() or 0

    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "vectors": vector_count,
    }


async def test_search_query(query: str, top_k: int = 3) -> None:
    """Execute test vector search query against system tenant memory."""
    logger.info("Testing search query: '%s'", query)
    query_vector = generate_fallback_embedding(query, dim=768)

    adapter = PgVectorSearchAdapter()
    results = await adapter.search_similar(
        tenant_id=SYSTEM_TENANT_ID,
        embedding=query_vector,
        top_k=top_k,
        filters=[],
        tags=[],
    )

    logger.info("Found %d matching system memory chunks:", len(results))
    for idx, r in enumerate(results, 1):
        file_path = r.meta_data.get("file_path", "unknown")
        chunk_type = r.meta_data.get("chunk_type", "chunk")
        symbol_name = r.meta_data.get("symbol_name", "")
        print(f"\n--- Result #{idx} (Score: {r.score:.4f}) ---")
        print(f"File: {file_path} | Type: {chunk_type} | Symbol: {symbol_name}")
        snippet = r.content[:200].replace('\n', ' ')
        print(f"Content: {snippet}...")


async def main() -> None:
    logger.info("=== Verifying System Memory ===")
    stats = await verify_stats()
    logger.info("System Tenant Stats: %d documents, %d chunks, %d vector records", stats["documents"], stats["chunks"], stats["vectors"])

    if stats["chunks"] > 0:
        await test_search_query("proxy telemetry country IP header")
        await test_search_query("AST chunking python")
    else:
        logger.warning("No system chunks found. Run ingest_system_memory.py first!")


if __name__ == "__main__":
    asyncio.run(main())
