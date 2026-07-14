"""Celery task definitions for Retriever background processing.

Process lifecycle:
  DocumentUploadedEvent (API) -> process_document [queue: ingestion.parse]
    -> DocumentParsedEvent (self-published) -> generate_embeddings [queue: knowledge.embed]
      -> DocumentIndexedEvent (self-published)
"""

import asyncio
import json
import os
import uuid as _uuid
from datetime import datetime, timezone

import pika
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from celery import Task

from processing_core import extract_text_from_file, chunk_text, chunk_recursive, chunk_semantic, embed_with_retry
from workers.src.celery_app import celery_app

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/retriever"
)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
EXCHANGE_NAME = "document.processing"
ROUTING_PARSED = "document.event.parsed"
ROUTING_INDEXED = "document.event.indexed"
ROUTING_FAILED = "document.event.failed"


# ── Event publishing helpers (keep pika here — Celery tasks self-publish) ──


def _publish_event(envelope: dict, routing_key: str) -> None:
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
    return {
        "eventId": f"evt_{_uuid.uuid4().hex}",
        "eventType": event_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "traceId": trace_id,
        "payload": payload,
    }


# ── Celery tasks ──────────────────────────────────────────────────────────


# Module-level engine — one per worker process. Swap via set_engine() for tests.
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL)
    return _engine


def set_engine(engine: AsyncEngine) -> None:
    global _engine
    _engine = engine


class DatabaseTask(Task):
    """Base task that provides DB engine access and UTC now."""
    pass


async def _run_process_document(document_id: str, tenant_id: str, storage_path: str) -> None:
    engine = get_engine()

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "UPDATE documents SET status = 'PARSING', updated_at = NOW() "
                "WHERE document_id = :doc_id"
            ),
            {"doc_id": document_id},
        )

    try:
        chunk_size = 500
        chunk_overlap = 100
        config_val = {}

        async with engine.begin() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            res = await conn.execute(
                sa.text(
                    "SELECT value FROM configurations "
                    "WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
                    "AND key = 'config_payload' ORDER BY tenant_id NULLS LAST LIMIT 1"
                ),
                {"tenant_id": tenant_id},
            )
            row = res.fetchone()
            if row:
                config_val = row[0]
                if isinstance(config_val, str):
                    config_val = json.loads(config_val)
                retrieval = config_val.get("retrieval_settings", {})
                chunk_size = retrieval.get("chunk_size", chunk_size)
                chunk_overlap = retrieval.get("chunk_overlap", chunk_overlap)

        local_path = None
        if storage_path.startswith("s3://"):
            import tempfile
            import boto3
            from botocore.config import Config

            path_parts = storage_path[5:].split("/", 1)
            bucket = path_parts[0]
            key = path_parts[1]

            endpoint_url = os.environ.get("S3_ENDPOINT_URL")
            client_opts = {}
            if endpoint_url:
                client_opts["endpoint_url"] = endpoint_url
                client_opts["config"] = Config(signature_version="s3v4", s3={"addressing_style": "path"})

            s3 = boto3.client("s3", **client_opts)
            _, ext = os.path.splitext(key)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                local_path = tmp.name

            s3.download_file(bucket, key, local_path)
            parse_target_path = local_path
        else:
            parse_target_path = storage_path

        try:
            text_content = extract_text_from_file(parse_target_path)
        finally:
            if local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception:
                    pass
        # Select splitter strategy
        chunk_cfg = config_val.get("chunking_settings", {})
        chunk_strategy = chunk_cfg.get("strategy", "fixed_window")
        chunk_size = chunk_cfg.get("chunk_size", chunk_size)
        chunk_overlap = chunk_cfg.get("chunk_overlap", chunk_overlap)
        semantic_threshold = chunk_cfg.get("semantic_threshold", 0.95)

        if chunk_strategy == "recursive":
            chunks_to_insert = chunk_recursive(
                text=text_content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                document_id=document_id,
                tenant_id=tenant_id,
            )
        elif chunk_strategy == "semantic":
            # Setup openai client for embedding sentences
            import openai
            embed_cfg = config_val.get("embedding_provider", {})
            embed_model = embed_cfg.get("model_name", "text-embedding-3-small")
            embed_api_key = embed_cfg.get("api_key", "")
            
            if embed_api_key and embed_api_key != "********":
                from processing_core import ConfigEncrypter
                enc = ConfigEncrypter()
                embed_api_key = enc.decrypt(embed_api_key)
            if not embed_api_key or embed_api_key == "********":
                embed_api_key = os.environ.get("OPENAI_API_KEY", "")
            embed_base_url = embed_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL")
            
            client_opts = {"api_key": embed_api_key}
            if embed_base_url:
                client_opts["base_url"] = embed_base_url
            
            embed_client = openai.AsyncOpenAI(**client_opts)
            
            chunks_to_insert = await chunk_semantic(
                text=text_content,
                embed_client=embed_client,
                embed_model=embed_model,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                semantic_threshold=semantic_threshold,
                document_id=document_id,
                tenant_id=tenant_id,
            )
        else:
            chunks_to_insert = chunk_text(
                text=text_content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                document_id=document_id,
                tenant_id=tenant_id,
            )

        # Metadata Extraction
        extracted_metadata = {}
        extractors_cfg = config_val.get("metadata_extractors", [])
        for ext_cfg in extractors_cfg:
            ext_name = ext_cfg.get("name")
            ext_type = ext_cfg.get("extractor_type")
            
            if ext_type == "regex":
                pattern = ext_cfg.get("pattern")
                if pattern:
                    match = re.search(pattern, text_content)
                    if match:
                        extracted_metadata[ext_name] = match.group(1) if match.groups() else match.group(0)
            
            elif ext_type == "llm":
                schema_def = ext_cfg.get("schema_definition")
                if schema_def:
                    ai_cfg = config_val.get("ai_provider", {})
                    ai_model = ai_cfg.get("default_model", "gpt-4o")
                    ai_api_key = ai_cfg.get("api_key", "")
                    
                    if ai_api_key and ai_api_key != "********":
                        from processing_core import ConfigEncrypter
                        enc = ConfigEncrypter()
                        ai_api_key = enc.decrypt(ai_api_key)
                    if not ai_api_key or ai_api_key == "********":
                        ai_api_key = os.environ.get("OPENAI_API_KEY", "")
                    ai_base_url = ai_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL")
                    
                    import openai
                    client_opts = {"api_key": ai_api_key}
                    if ai_base_url:
                        client_opts["base_url"] = ai_base_url
                    
                    ai_client = openai.AsyncOpenAI(**client_opts)
                    
                    system_prompt = (
                        "You are an expert metadata extraction assistant. Extract the following metadata schema "
                        f"from the document content: {json.dumps(schema_def)}. Return ONLY a valid JSON object matching this schema."
                    )
                    
                    try:
                        excerpt = text_content[:3000]
                        response = await ai_client.chat.completions.create(
                            model=ai_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": excerpt}
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.0
                        )
                        raw_json = response.choices[0].message.content
                        extracted_json = json.loads(raw_json)
                        for k, v in extracted_json.items():
                            extracted_metadata[f"{ext_name}_{k}"] = v
                    except Exception:
                        pass

        chunk_ids = [c["chunk_id"] for c in chunks_to_insert]

        async with engine.begin() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            for chunk in chunks_to_insert:
                chunk_meta = json.loads(chunk["meta_data"]) if chunk.get("meta_data") else {}
                chunk_meta.update(extracted_metadata)
                
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO document_chunks
                        (chunk_id, document_id, tenant_id, content, token_count,
                         chunk_index, meta_data, created_at)
                        VALUES (:chunk_id, :document_id, :tenant_id, :content,
                                :token_count, :chunk_index, CAST(:meta_data AS jsonb), NOW())
                        """
                    ),
                    {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "tenant_id": chunk["tenant_id"],
                        "content": chunk["content"],
                        "token_count": chunk["token_count"],
                        "chunk_index": chunk["chunk_index"],
                        "meta_data": json.dumps(chunk_meta),
                    },
                )

            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'INDEXING', updated_at = NOW() "
                    "WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

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
                    "UPDATE documents SET status = 'FAILED', updated_at = NOW() "
                    "WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )
        failed_payload = {
            "documentId": document_id,
            "tenantId": tenant_id,
            "failurePhase": "PARSING",
            "errorMessage": str(e),
        }
        envelope = _build_envelope("DOCUMENT_FAILED", failed_payload)
        _publish_event(envelope, ROUTING_FAILED)
        raise

# Keep async function importable for tests and legacy event_consumer
process_document_async = _run_process_document


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(self, document_id: str, tenant_id: str, storage_path: str) -> None:
    asyncio.run(_run_process_document(document_id, tenant_id, storage_path))


async def _run_generate_embeddings(document_id: str, tenant_id: str) -> None:
    engine = get_engine()
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    api_key = os.environ.get("OPENAI_API_KEY", "")

    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            res = await conn.execute(
                sa.text(
                    "SELECT value FROM configurations "
                    "WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
                    "AND key = 'config_payload' ORDER BY tenant_id NULLS LAST LIMIT 1"
                ),
                {"tenant_id": tenant_id},
            )
            row = res.fetchone()
            if row:
                config_val = row[0]
                if isinstance(config_val, str):
                    config_val = json.loads(config_val)
                embed_cfg = config_val.get("embedding_provider", {})
                embedding_model = embed_cfg.get("model_name", embedding_model)
                api_key = embed_cfg.get("api_key", api_key)
                if api_key and api_key != "********":
                    from processing_core import ConfigEncrypter
                    enc = ConfigEncrypter()
                    api_key = enc.decrypt(api_key)

                if not api_key or api_key == "********":
                    provider = embed_cfg.get("provider_name", "openai").upper()
                    env_key = f"{provider}_API_KEY"
                    api_key = os.environ.get(env_key, os.environ.get("OPENAI_API_KEY", ""))

        async with engine.connect() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            result = await conn.execute(
                sa.text(
                    "SELECT chunk_id, content FROM document_chunks "
                    "WHERE document_id = :doc_id ORDER BY chunk_index"
                ),
                {"doc_id": document_id},
            )
            chunks = result.fetchall()

        if not chunks:
            return

        import openai

        if not api_key:
            return

        client = openai.AsyncOpenAI(api_key=api_key)

        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'INDEXING', updated_at = NOW() "
                    "WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

        batch_size = 20
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [row[1] for row in batch]
            embedding_data = await embed_with_retry(client, texts, embedding_model)
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
                    {
                        "chunk_id": chunk_id,
                        "tenant_id": tenant_id,
                        "embedding": embedding_str,
                    },
                )

            await conn.execute(
                sa.text(
                    "UPDATE documents SET status = 'INDEXED', updated_at = NOW() "
                    "WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )

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
                    "UPDATE documents SET status = 'FAILED', updated_at = NOW() "
                    "WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id},
            )
        failed_payload = {
            "documentId": document_id,
            "tenantId": tenant_id,
            "failurePhase": "EMBEDDING",
            "errorMessage": str(e),
        }
        envelope = _build_envelope("DOCUMENT_FAILED", failed_payload)
        _publish_event(envelope, ROUTING_FAILED)
        raise

# Keep async function importable for legacy event_consumer
_generate_embeddings_async = _run_generate_embeddings


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    max_retries=5,
    default_retry_delay=2,
    autoretry_for=(Exception,),
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_embeddings(self, document_id: str, tenant_id: str) -> None:
    asyncio.run(_run_generate_embeddings(document_id, tenant_id))


# ── Periodic / maintenance tasks ──────────────────────────────────────────


@celery_app.task(base=DatabaseTask)
def reconcile_stalled() -> None:
    """Re-publish tasks for documents stuck in PENDING or INDEXING > 15 min."""
    engine = get_engine()

    async def _run():
        async with engine.begin() as conn:
            await conn.execute(sa.text("SET LOCAL app.bypass_rls = 'true'"))
            result = await conn.execute(
                sa.text(
                    """
                    SELECT document_id, tenant_id, storage_path, status
                    FROM documents
                    WHERE status IN ('PENDING', 'INDEXING')
                      AND updated_at < NOW() - INTERVAL '15 minutes'
                    """
                ),
            )
            stalled = result.fetchall()

        for row in stalled:
            doc_id, t_id, s_path, status = row
            if status == "PENDING":
                process_document.delay(doc_id, t_id, s_path)
            elif status == "INDEXING":
                generate_embeddings.delay(doc_id, t_id)

    asyncio.run(_run())


@celery_app.task(base=DatabaseTask)
def warm_caches() -> None:
    """Periodic cache warming — placeholder for Redis pre-heat logic."""
    pass
