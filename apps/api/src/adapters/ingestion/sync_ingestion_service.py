import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import (
    DocumentChunkDb,
    DocumentDb,
    VectorRecord1536Db,
    VectorRecord3072Db,
    VectorRecordDb,
)
from src.domain.abstractions.retrieval import EmbeddingProvider

logger = logging.getLogger(__name__)


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

    from processing_core import (
        extract_layout_from_pdf,
        extract_text_from_file,
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    layout_meta = {"has_tables": False, "table_count": 0, "layout_parsed": False}
    try:
        if filename.lower().endswith(".pdf") or mime_type == "application/pdf":
            layout_result = extract_layout_from_pdf(tmp_path)
            text = layout_result["text"]
            layout_meta = {
                "has_tables": layout_result["has_tables"],
                "table_count": layout_result["table_count"],
                "layout_parsed": True,
            }
        else:
            text = extract_text_from_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not text:
        text = file_content.decode("utf-8", errors="ignore")

    from src.adapters.cognitive.ast_code_chunker import AstCodeChunker
    from src.domain.compliance.pii_anonymizer import PiiAnonymizer
    from src.domain.ingestion.chunker_factory import ChunkerFactory

    anonymizer = PiiAnonymizer()
    text = anonymizer.anonymize_text(text)

    ext = os.path.splitext(filename)[1].lower()
    code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp", ".rs", ".pyw"}

    if ext in code_extensions:
        ast_chunker = AstCodeChunker()
        if ext in {".py", ".pyw"}:
            raw_chunks = ast_chunker.chunk_python_ast(text, filename=filename)
        else:
            raw_chunks = ast_chunker._fallback_line_chunker(text, filename=filename)
    elif ext == ".md":
        ast_chunker = AstCodeChunker()
        raw_chunks = ast_chunker.chunk_markdown(text, filename=filename)
    else:
        hierarchical_chunker = ChunkerFactory.get_chunker("hierarchical")
        raw_chunks = hierarchical_chunker.split_text_with_offsets(text, chunk_size, chunk_overlap)

    prefix = f"[Document: {filename}]\n" if filename else ""
    chunks: list[dict] = []

    for idx, c in enumerate(raw_chunks):
        c_id = c.get("chunk_id") or str(uuid.uuid4())
        p_id = c.get("parent_chunk_id")

        raw_content = c["content"]
        content_with_prefix = (
            f"{prefix}{raw_content}" if prefix and not raw_content.startswith("[Document:") else raw_content
        )

        meta = c.get("meta_data") or c.get("metadata") or {}
        if isinstance(meta, str):
            import json

            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        meta = dict(meta)
        meta.update(layout_meta)
        if p_id:
            meta["parent_chunk_id"] = str(p_id)

        chunks.append({
            "chunk_id": str(c_id),
            "parent_chunk_id": str(p_id) if p_id else None,
            "content": content_with_prefix,
            "token_count": c.get("token_count") or len(content_with_prefix.split()),
            "chunk_index": c.get("chunk_index", idx),
            "meta_data": meta,
        })

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
            p_id = chunk_data.get("parent_chunk_id")
            parent_uuid = uuid.UUID(p_id) if p_id else None

            db_chunk = DocumentChunkDb(
                chunk_id=chunk_id,
                document_id=uuid.UUID(document_id),
                tenant_id=uuid.UUID(tenant_id),
                collection_id=collection_id,
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                chunk_index=chunk_data["chunk_index"],
                parent_chunk_id=parent_uuid,
                meta_data=chunk_data["meta_data"],
            )
            session.add(db_chunk)
        await session.flush()

        for chunk_data, embedding in zip(chunks, embeddings, strict=True):
            chunk_id = uuid.UUID(chunk_data["chunk_id"])
            dim = len(embedding)
            if dim == 1536:
                vector_cls = VectorRecord1536Db
            elif dim == 3072:
                vector_cls = VectorRecord3072Db
            else:
                vector_cls = VectorRecordDb

            db_vector = vector_cls(
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
            t_list = extractor.extract_triples(
                c_text, chunk_id=c_id, document_id=document_id
            )
            all_triples.extend(t_list)

        if all_triples and container.graph_repository:
            await container.graph_repository.add_triples(tenant_id, all_triples)
    except Exception as err:
        logger.warning(
            f"Knowledge Graph triple extraction failed during document ingestion ({err}).",
            exc_info=True,
        )

    return len(chunks)
