"""Database repository adapter for compliance, hard purges, and SLA data retention scans."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import (
    DocumentChunkDb,
    DocumentDb,
    GraphTripleDb,
    OnlineEvaluationDb,
    SemanticCacheDb,
    VectorRecord1536Db,
    VectorRecord3072Db,
    VectorRecordDb,
)


class SqlComplianceRepository:
    """PostgreSQL implementation of compliance database operations."""

    async def get_expired_document_ids(
        self, tenant_id: str, cutoff_date: datetime
    ) -> list[str]:
        """Fetch document IDs created before cutoff_date."""
        tenant_uuid = UUID(tenant_id)
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(DocumentDb.document_id).where(
                DocumentDb.tenant_id == tenant_uuid,
                DocumentDb.created_at < cutoff_date,
            )
            res = await session.execute(stmt)
            return [str(r[0]) for r in res.fetchall()]

    async def purge_document_db_records(
        self, tenant_id: str, document_id: str
    ) -> tuple[int, int, int, str | None]:
        """Purge chunks, vectors, and document DB records. Returns (chunks, vectors, doc_purged, storage_path)."""
        tenant_uuid = UUID(tenant_id)
        doc_uuid = UUID(document_id)

        chunks_count = 0
        vectors_count = 0
        doc_purged = 0
        storage_path: str | None = None

        async with tenant_session(tenant_id=tenant_id) as session:
            chunk_stmt = select(DocumentChunkDb.chunk_id).where(
                DocumentChunkDb.tenant_id == tenant_uuid,
                DocumentChunkDb.document_id == doc_uuid,
            )
            res_chunks = await session.execute(chunk_stmt)
            chunk_uuids = [r[0] for r in res_chunks.fetchall()]

            if chunk_uuids:
                for vec_model in (VectorRecordDb, VectorRecord1536Db, VectorRecord3072Db):
                    vec_del = delete(vec_model).where(
                        vec_model.tenant_id == tenant_uuid,
                        vec_model.chunk_id.in_(chunk_uuids),
                    )
                    v_res = await session.execute(vec_del)
                    vectors_count += v_res.rowcount or 0

                chunk_del = delete(DocumentChunkDb).where(
                    DocumentChunkDb.tenant_id == tenant_uuid,
                    DocumentChunkDb.document_id == doc_uuid,
                )
                c_res = await session.execute(chunk_del)
                chunks_count = c_res.rowcount or 0

            doc_stmt = select(DocumentDb).where(
                DocumentDb.tenant_id == tenant_uuid,
                DocumentDb.document_id == doc_uuid,
            )
            doc_res = await session.execute(doc_stmt)
            doc_obj = doc_res.scalar_one_or_none()

            if doc_obj:
                storage_path = doc_obj.storage_path
                doc_del = delete(DocumentDb).where(
                    DocumentDb.tenant_id == tenant_uuid,
                    DocumentDb.document_id == doc_uuid,
                )
                d_res = await session.execute(doc_del)
                doc_purged = d_res.rowcount or 0

            await session.commit()

        return chunks_count, vectors_count, doc_purged, storage_path

    async def purge_full_tenant_db(self, tenant_id: str) -> dict[str, int]:
        """Purge all database tables for target tenant."""
        tenant_uuid = UUID(tenant_id)
        stats = {
            "documents_purged": 0,
            "chunks_purged": 0,
            "vectors_purged": 0,
            "cache_purged": 0,
            "graph_triples_purged": 0,
            "evaluations_purged": 0,
        }

        async with tenant_session(tenant_id=tenant_id) as session:
            for vec_model in (VectorRecordDb, VectorRecord1536Db, VectorRecord3072Db):
                v_res = await session.execute(
                    delete(vec_model).where(vec_model.tenant_id == tenant_uuid)
                )
                stats["vectors_purged"] += v_res.rowcount or 0

            sc_res = await session.execute(
                delete(SemanticCacheDb).where(SemanticCacheDb.tenant_id == tenant_uuid)
            )
            stats["cache_purged"] = sc_res.rowcount or 0

            eval_res = await session.execute(
                delete(OnlineEvaluationDb).where(OnlineEvaluationDb.tenant_id == tenant_uuid)
            )
            stats["evaluations_purged"] = eval_res.rowcount or 0

            gt_res = await session.execute(
                delete(GraphTripleDb).where(GraphTripleDb.tenant_id == tenant_uuid)
            )
            stats["graph_triples_purged"] = gt_res.rowcount or 0

            c_res = await session.execute(
                delete(DocumentChunkDb).where(DocumentChunkDb.tenant_id == tenant_uuid)
            )
            stats["chunks_purged"] = c_res.rowcount or 0

            d_res = await session.execute(
                delete(DocumentDb).where(DocumentDb.tenant_id == tenant_uuid)
            )
            stats["documents_purged"] = d_res.rowcount or 0

            await session.commit()

        return stats
