import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentChunkDb, DocumentDb, VectorRecordDb
from src.domain.abstractions.retrieval import EmbeddingProvider


async def ingest_file_sync(
    tenant_id: str,
    document_id: str,
    filename: str,
    file_content: bytes,
    file_hash: str,
    mime_type: str,
    embedder: EmbeddingProvider,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> int:
    import os
    import tempfile

    from processing_core import chunk_text, extract_text_from_file

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        text = extract_text_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not text:
        text = file_content.decode("utf-8", errors="ignore")

    chunks = chunk_text(
        text=text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_id=document_id,
        tenant_id=tenant_id,
    )

    texts_to_embed = [c["content"] for c in chunks]
    embeddings = await embedder.embed_batch(texts_to_embed)

    async with tenant_session(tenant_id=tenant_id) as session:
        result = await session.execute(
            select(DocumentDb).where(DocumentDb.document_id == uuid.UUID(document_id))
        )
        doc = result.scalar_one_or_none()
        if not doc:
            doc = DocumentDb(
                document_id=uuid.UUID(document_id),
                tenant_id=uuid.UUID(tenant_id),
                filename=filename,
                file_hash=file_hash,
                storage_path="memory",
                file_size=len(file_content),
                mime_type=mime_type,
                status="INDEXING",
            )
            session.add(doc)
        else:
            await session.execute(
                delete(DocumentChunkDb).where(DocumentChunkDb.document_id == uuid.UUID(document_id))
            )

        collection_id = doc.collection_id if doc and doc.collection_id else None

        for chunk_data in chunks:
            chunk_id = uuid.UUID(chunk_data["chunk_id"])
            db_chunk = DocumentChunkDb(
                chunk_id=chunk_id,
                document_id=uuid.UUID(document_id),
                tenant_id=uuid.UUID(tenant_id),
                collection_id=collection_id,
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                chunk_index=chunk_data["chunk_index"],
                meta_data=chunk_data["meta_data"],
            )
            session.add(db_chunk)
        await session.flush()

        for chunk_data, embedding in zip(chunks, embeddings, strict=True):
            chunk_id = uuid.UUID(chunk_data["chunk_id"])
            db_vector = VectorRecordDb(
                chunk_id=chunk_id,
                tenant_id=uuid.UUID(tenant_id),
                collection_id=collection_id,
                embedding=embedding,
            )
            session.add(db_vector)
        await session.flush()

        if doc:
            doc.status = "INDEXED"
            doc.updated_at = datetime.now(UTC)
        await session.flush()

    # Knowledge Graph Triple Extraction Pass
    try:
        from src.container import container
        from src.domain.graph.graph_extraction_service import GraphExtractor

        extractor = GraphExtractor()
        all_triples = []
        for chunk_data in chunks:
            c_id = chunk_data["chunk_id"]
            c_text = chunk_data["content"]
            t_list = extractor.extract_triples(c_text, chunk_id=c_id)
            all_triples.extend(t_list)

        if all_triples and container.graph_repository:
            await container.graph_repository.add_triples(tenant_id, all_triples)
    except Exception:
        pass

    return len(chunks)
