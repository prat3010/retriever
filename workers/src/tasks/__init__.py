import asyncio
import json
import os
import uuid
import random
import pika
import pdfplumber
import tiktoken
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from workers.src.main import app

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/retriever"
)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
EXCHANGE_NAME = "document.processing"
ROUTING_PARSED = "document.event.parsed"
ROUTING_INDEXED = "document.event.indexed"
ROUTING_FAILED = "document.event.failed"


def _publish_event(envelope: dict, routing_key: str) -> None:
    """Publish a structured event to the document.processing exchange."""
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(envelope).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        connection.close()


def _build_envelope(event_type: str, payload: dict, trace_id: str = "") -> dict:
    import uuid as _uuid
    from datetime import datetime, timezone
    return {
        "eventId": f"evt_{_uuid.uuid4().hex}",
        "eventType": event_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "traceId": trace_id,
        "payload": payload,
    }


async def process_document_async(document_id: str, tenant_id: str, storage_path: str) -> None:
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "UPDATE documents SET status = 'PARSING', updated_at = NOW() WHERE document_id = :doc_id"
            ),
            {"doc_id": document_id},
        )

    try:
        chunk_size = 500
        chunk_overlap = 100

        async with engine.begin() as conn:
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

        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text_content)

        chunks_to_insert = []
        chunk_ids = []
        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_content = encoding.decode(chunk_tokens)
            cid = str(uuid.uuid4())
            chunk_ids.append(cid)

            chunks_to_insert.append({
                "chunk_id": cid,
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

            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'INDEXING', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

        # Publish DocumentParsedEvent
        parsed_payload = {
            "documentId": document_id,
            "tenantId": tenant_id,
            "chunkIds": chunk_ids,
        }
        envelope = _build_envelope("DOCUMENT_PARSED", parsed_payload)
        _publish_event(envelope, ROUTING_PARSED)

    except Exception as e:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'FAILED', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )
        # Publish DocumentFailedEvent
        failed_payload = {
            "documentId": document_id,
            "tenantId": tenant_id,
            "failurePhase": "PARSING",
            "errorMessage": str(e),
        }
        envelope = _build_envelope("DOCUMENT_FAILED", failed_payload)
        _publish_event(envelope, ROUTING_FAILED)
        raise e
    finally:
        await engine.dispose()


@app.task(name="tasks.parse_document", max_retries=3, default_retry_delay=10,
          autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300, retry_jitter=True)
def parse_document(document_id: str, tenant_id: str, storage_path: str) -> str:
    asyncio.run(process_document_async(document_id, tenant_id, storage_path))
    return f"Document parsed: {document_id} for Tenant: {tenant_id}"


async def _generate_embeddings_async(document_id: str, tenant_id: str) -> None:
    engine = create_async_engine(DATABASE_URL)
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            result = await conn.execute(
                sa.text(
                    "SELECT chunk_id, content FROM document_chunks WHERE document_id = :doc_id ORDER BY chunk_index"
                ),
                {"doc_id": document_id},
            )
            chunks = result.fetchall()

        if not chunks:
            return

        import openai

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return

        client = openai.AsyncOpenAI(api_key=api_key)

        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'INDEXING', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

        batch_size = 20
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [row[1] for row in batch]
            embedding_data = await _embed_with_retry(client, texts, embedding_model)
            for chunk_row, emb in zip(batch, embedding_data):
                all_embeddings.append((str(chunk_row[0]), emb))

        async with engine.begin() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            for chunk_id, embedding in all_embeddings:
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO vector_records (chunk_id, tenant_id, embedding, created_at)
                        VALUES (:chunk_id, :tenant_id, :embedding::vector, NOW())
                        ON CONFLICT (chunk_id) DO UPDATE SET embedding = :embedding::vector
                        """
                    ),
                    {"chunk_id": chunk_id, "tenant_id": tenant_id, "embedding": embedding_str},
                )

            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'INDEXED', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

        # Publish DocumentIndexedEvent
        indexed_payload = {
            "documentId": document_id,
            "tenantId": tenant_id,
            "chunksVectorized": len(all_embeddings),
            "vectorCollection": "tenant_embeddings_v1",
        }
        envelope = _build_envelope("DOCUMENT_INDEXED", indexed_payload)
        _publish_event(envelope, ROUTING_INDEXED)

    except Exception as e:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'FAILED', updated_at = NOW() WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )
        # Publish DocumentFailedEvent
        failed_payload = {
            "documentId": document_id,
            "tenantId": tenant_id,
            "failurePhase": "EMBEDDING",
            "errorMessage": str(e),
        }
        envelope = _build_envelope("DOCUMENT_FAILED", failed_payload)
        _publish_event(envelope, ROUTING_FAILED)
        raise e
    finally:
        await engine.dispose()


async def _embed_with_retry(
    client, texts: list[str], model: str, max_retries: int = 5
) -> list[list[float]]:
    import openai

    for attempt in range(max_retries + 1):
        try:
            response = await client.embeddings.create(input=texts, model=model, timeout=30)
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except (openai.APIError, openai.APITimeoutError, openai.RateLimitError):
            if attempt == max_retries:
                raise
            sleep_seconds = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(sleep_seconds)


@app.task(
    name="tasks.generate_embeddings", max_retries=5, default_retry_delay=2,
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, retry_jitter=True,
)
def generate_embeddings(document_id: str, tenant_id: str) -> str:
    asyncio.run(_generate_embeddings_async(document_id, tenant_id))
    return f"Embeddings generated for document: {document_id}"
