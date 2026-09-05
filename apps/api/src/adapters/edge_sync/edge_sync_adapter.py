"""Edge Sync Cloud Adapter (M98).

Connects cloud PostgreSQL pgvector storage with edge devices.
Emits differential sequence deltas and generates standalone self-contained
SQLite database bundles for sovereign offline deployments.
"""

import hashlib
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentChunkDb, DocumentDb, VectorRecordDb
from src.adapters.edge_sync.sqlite_edge_engine import SqliteEdgeEngine
from src.domain.abstractions.edge_sync import (
    ChunkSyncItem,
    EdgeBundleManifest,
    EdgeSyncAdapterProtocol,
    EdgeSyncDelta,
    VectorSyncItem,
)
from src.domain.edge_sync.delta_calculator import EdgeDeltaCalculator

logger = logging.getLogger(__name__)


class EdgeSyncAdapter(EdgeSyncAdapterProtocol):
    """Cloud-side adapter generating differential sync deltas and edge SQLite bundles."""

    def __init__(
        self,
        delta_calculator: EdgeDeltaCalculator | None = None,
        edge_engine: SqliteEdgeEngine | None = None,
    ) -> None:
        self.calculator = delta_calculator or EdgeDeltaCalculator()
        self.edge_engine = edge_engine or SqliteEdgeEngine()

    async def get_delta_for_tenant(
        self,
        tenant_id: str,
        since_seq: int = 0,
        limit: int = 500,
    ) -> EdgeSyncDelta:
        """Fetch differential sync delta for tenant from PostgreSQL."""
        t_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id

        async with tenant_session(str(t_uuid)) as session:
            # 1. Fetch chunks for tenant
            stmt_chunks = (
                select(DocumentChunkDb)
                .where(DocumentChunkDb.tenant_id == t_uuid)
                .order_by(DocumentChunkDb.created_at.asc())
                .limit(limit)
            )
            res_chunks = await session.execute(stmt_chunks)
            chunk_rows = list(res_chunks.scalars().all())

            # 2. Fetch vector embeddings for these chunks
            chunk_ids = [c.chunk_id for c in chunk_rows]
            vector_dict: dict[uuid.UUID, list[float]] = {}
            if chunk_ids:
                stmt_vecs = select(VectorRecordDb).where(
                    VectorRecordDb.chunk_id.in_(chunk_ids),
                    VectorRecordDb.tenant_id == t_uuid,
                )
                res_vecs = await session.execute(stmt_vecs)
                vec_rows = list(res_vecs.scalars().all())
                for v in vec_rows:
                    if hasattr(v.embedding, "tolist"):
                        vector_dict[v.chunk_id] = v.embedding.tolist()
                    elif isinstance(v.embedding, list | tuple):
                        vector_dict[v.chunk_id] = list(v.embedding)

            # Format items
            sync_chunks: list[ChunkSyncItem] = []
            sync_vectors: list[VectorSyncItem] = []

            for c in chunk_rows:
                meta = dict(c.meta_data) if c.meta_data else {}
                sync_chunks.append(
                    ChunkSyncItem(
                        chunk_id=str(c.chunk_id),
                        document_id=str(c.document_id),
                        chunk_index=c.chunk_index,
                        content=c.content,
                        token_count=c.token_count,
                        meta_data=meta,
                        sequence_num=since_seq + len(sync_chunks) + 1,
                    )
                )
                if c.chunk_id in vector_dict:
                    emb = vector_dict[c.chunk_id]
                    sync_vectors.append(
                        VectorSyncItem(
                            chunk_id=str(c.chunk_id),
                            embedding=emb,
                            dimension=len(emb),
                        )
                    )

            current_seq = since_seq + len(sync_chunks)

            return self.calculator.compute_delta(
                tenant_id=str(t_uuid),
                since_seq=since_seq,
                current_seq=current_seq,
                chunks=sync_chunks,
                vectors=sync_vectors,
                deleted_ids=[],
            )

    async def export_sovereign_bundle(
        self,
        tenant_id: str,
        output_path: str,
    ) -> EdgeBundleManifest:
        """Export all tenant documents, chunks, and vector embeddings into a standalone SQLite bundle."""
        t_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        bundle_id = f"bundle_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(UTC).isoformat()

        # Delete existing file at path if any
        p = Path(output_path)
        if p.exists():
            p.unlink()

        # Initialize edge schema
        self.edge_engine.initialize_schema(output_path)

        async with tenant_session(str(t_uuid)) as session:
            # 1. Fetch all documents
            res_docs = await session.execute(select(DocumentDb).where(DocumentDb.tenant_id == t_uuid))
            docs = list(res_docs.scalars().all())

            # 2. Fetch all chunks
            res_chunks = await session.execute(
                select(DocumentChunkDb)
                .where(DocumentChunkDb.tenant_id == t_uuid)
                .order_by(DocumentChunkDb.created_at.asc())
            )
            chunks = list(res_chunks.scalars().all())

            # 3. Fetch all vectors
            res_vecs = await session.execute(
                select(VectorRecordDb).where(VectorRecordDb.tenant_id == t_uuid)
            )
            vecs = list(res_vecs.scalars().all())

            chunk_items = [
                ChunkSyncItem(
                    chunk_id=str(c.chunk_id),
                    document_id=str(c.document_id),
                    chunk_index=c.chunk_index,
                    content=c.content,
                    token_count=c.token_count,
                    meta_data=dict(c.meta_data) if c.meta_data else {},
                )
                for c in chunks
            ]

            vector_items = []
            for v in vecs:
                if hasattr(v.embedding, "tolist"):
                    emb = v.embedding.tolist()
                elif isinstance(v.embedding, list | tuple):
                    emb = list(v.embedding)
                else:
                    emb = []
                vector_items.append(
                    VectorSyncItem(
                        chunk_id=str(v.chunk_id),
                        embedding=emb,
                        dimension=len(emb),
                    )
                )

            delta = self.calculator.compute_delta(
                tenant_id=str(t_uuid),
                since_seq=0,
                current_seq=len(chunk_items),
                chunks=chunk_items,
                vectors=vector_items,
                deleted_ids=[],
            )

            # Apply delta into the SQLite bundle
            self.edge_engine.apply_delta(output_path, delta)

        # Compute bundle file checksum and size
        file_bytes = p.read_bytes()
        file_size = len(file_bytes)
        file_sha256 = hashlib.sha256(file_bytes).hexdigest()

        return EdgeBundleManifest(
            bundle_id=bundle_id,
            tenant_id=str(t_uuid),
            database_engine="sqlite3",
            total_documents=len(docs),
            total_chunks=len(chunk_items),
            total_vectors=len(vector_items),
            vector_dimension=768,
            checkpoint_sequence=len(chunk_items),
            checksum_sha256=file_sha256,
            created_at=now_iso,
            file_size_bytes=file_size,
            bundle_path=str(p.resolve()),
        )

    async def create_standalone_bundle(self, tenant_id: str) -> EdgeBundleManifest:
        """Create a temporary standalone bundle and return its manifest."""
        temp_fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(temp_fd)
        return await self.export_sovereign_bundle(tenant_id=tenant_id, output_path=temp_path)
