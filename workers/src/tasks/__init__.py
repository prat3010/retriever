import asyncio
import json
import os
import uuid
import pdfplumber
import tiktoken
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from workers.src.main import app

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/retriever"
)


async def process_document_async(document_id: str, tenant_id: str, storage_path: str) -> None:
    engine = create_async_engine(DATABASE_URL)

    # 1. Update status to 'processing'
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "UPDATE documents SET status = 'processing', updated_at = NOW() WHERE document_id = :doc_id"
            ),
            {"doc_id": document_id},
        )

    try:
        # 2. Fetch tenant config chunking sizes (or default to 500 size, 100 overlap)
        chunk_size = 500
        chunk_overlap = 100

        async with engine.begin() as conn:
            # Bypass RLS to read configuration settings
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            res = await conn.execute(
                sa.text(
                    "SELECT value FROM configurations WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) AND key = 'retrieval' ORDER BY tenant_id NULLS LAST LIMIT 1"
                ),
                {"tenant_id": tenant_id},
            )
            row = res.fetchone()
            if row:
                config_val = row[0]
                if isinstance(config_val, str):
                    config_val = json.loads(config_val)
                chunk_size = config_val.get("chunk_size", chunk_size)
                chunk_overlap = config_val.get("chunk_overlap", chunk_overlap)

        # 3. Parse text contents preserving layout
        text_content = ""
        if storage_path.lower().endswith(".pdf"):
            text_runs = []
            with pdfplumber.open(storage_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text_runs.append(page_text)
            text_content = "\n--- Page Break ---\n".join(text_runs)
        else:
            with open(storage_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()

        # 4. Token-Aware Chunking using tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text_content)

        chunks_to_insert = []
        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_content = encoding.decode(chunk_tokens)

            chunks_to_insert.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "tenant_id": tenant_id,
                "content": chunk_content,
                "token_count": len(chunk_tokens),
                "chunk_index": chunk_index,
                "meta_data": json.dumps({"token_start": start, "token_end": end}),
            })

            chunk_index += 1
            step = max(1, chunk_size - chunk_overlap)
            start += step

        # 5. Insert chunks into PostgreSQL bypassing RLS validation context
        async with engine.begin() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))

            for chunk in chunks_to_insert:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO document_chunks 
                        (chunk_id, document_id, tenant_id, content, token_count, chunk_index, meta_data, created_at)
                        VALUES 
                        (:chunk_id, :document_id, :tenant_id, :content, :token_count, :chunk_index, CAST(:meta_data AS jsonb), NOW())
                    """
                    ),
                    chunk,
                )

            # Update document state to processed
            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'processed', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

    except Exception as e:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'failed', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )
        raise e
    finally:
        await engine.dispose()


@app.task(name="tasks.parse_document", max_retries=3)
def parse_document(document_id: str, tenant_id: str, storage_path: str) -> str:
    """Async background worker task to process layouts and chunk text contents."""
    asyncio.run(process_document_async(document_id, tenant_id, storage_path))
    return f"Document parsed: {document_id} for Tenant: {tenant_id}"


@app.task(name="tasks.generate_embeddings", max_retries=5)
def generate_embeddings(document_id: str, tenant_id: str) -> str:
    """Placeholder task for embedding generation and sync."""
    return f"Embeddings generated for document: {document_id}"

