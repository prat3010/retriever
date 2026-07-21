"""Document management routes."""
import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Security,
    UploadFile,
    status,
)

from src.adapters.api.security import verify_scopes, verify_tenant_isolation
from src.adapters.cache.config_cache import redis_client
from src.adapters.telemetry.rate_limiter_dep import rate_limit
from src.container import document_repository, inference_orchestrator, local_storage
from src.domain.abstractions.inference import ChatMessage, InferenceRequest
from src.domain.abstractions.ingestion import Document
from src.schemas.document import DocumentResponse, ExtractRequest, ExtractResponse

try:
    from src.adapters.broker.celery_publisher import celery_app
except Exception:
    celery_app = None


router = APIRouter(tags=["Documents"])


async def _check_idempotency(tenantId: str, key: str) -> dict | None:
    if redis_client is None:
        return None
    redis_key = f"idempotency:{tenantId}:{key}"
    cached = await redis_client.get(redis_key)
    if cached:
        return json.loads(cached)
    return None


async def _cache_idempotency(tenantId: str, key: str, payload: dict) -> None:
    if redis_client is None:
        return
    redis_key = f"idempotency:{tenantId}:{key}"
    await redis_client.setex(redis_key, 86400, json.dumps(payload))


@router.post(
    "/v1/tenants/{tenantId}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"]), Depends(rate_limit(scope="ingest", max_requests=20))],
)
async def upload_document(
    tenantId: str,
    file: UploadFile = File(...),
    x_idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict:
    """Upload and schedule document text chunking extraction pipeline."""
    if x_idempotency_key:
        cached = await _check_idempotency(tenantId, x_idempotency_key)
        if cached:
            return cached

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    existing = await document_repository.find_by_hash(tenantId, file_hash)
    if existing:
        response_payload = {
            "documentId": existing.document_id,
            "status": "pending",
            "fileHash": file_hash,
            "createdAt": existing.created_at,
        }
        if x_idempotency_key:
            await _cache_idempotency(tenantId, x_idempotency_key, response_payload)
        return response_payload

    storage_path = await local_storage.save_file(tenantId, file.filename, content)

    doc_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    doc = Document(
        document_id=doc_id,
        tenant_id=tenantId,
        filename=file.filename,
        file_hash=file_hash,
        storage_path=storage_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    await document_repository.create_document(tenantId, doc)

    if celery_app is not None:
        try:
            celery_app.send_task(
                "process_document",
                args=[str(doc_id), tenantId, storage_path, str(file.content_type or "")],
                queue="ingestion.parse",
            )
        except Exception:
            pass

    response_payload = {
        "documentId": str(doc_id),
        "status": "pending",
        "fileHash": file_hash,
        "createdAt": doc.created_at,
    }

    if x_idempotency_key:
        await _cache_idempotency(tenantId, x_idempotency_key, response_payload)

    return response_payload


@router.get(
    "/v1/tenants/{tenantId}/documents",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def list_documents(
    tenantId: str,
    limit: int | None = None,
    cursor: str | None = None,
) -> Any:
    """List all ingestion records belonging to the tenant."""
    if limit is not None or cursor is not None:
        limit_val = limit if limit is not None else 50
        items, next_cursor, has_more = await document_repository.list_documents_cursor(
            tenantId, limit=limit_val, cursor=cursor
        )
        return {
            "items": [
                DocumentResponse(
                    documentId=d.document_id,
                    filename=d.filename,
                    fileSize=d.file_size,
                    mimeType=d.mime_type,
                    status=d.status,
                    createdAt=d.created_at,
                    updatedAt=d.updated_at
                )
                for d in items
            ],
            "pagination": {
                "nextCursor": next_cursor,
                "limit": limit_val,
                "hasMore": has_more
            }
        }
    else:
        docs = await document_repository.list_documents(tenantId)
        return [
            DocumentResponse(
                documentId=d.document_id,
                filename=d.filename,
                fileSize=d.file_size,
                mimeType=d.mime_type,
                status=d.status,
                createdAt=d.created_at,
                updatedAt=d.updated_at
            )
            for d in docs
        ]


@router.get(
    "/v1/tenants/{tenantId}/documents/{documentId}",
    status_code=status.HTTP_200_OK,
    response_model=DocumentResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_document(tenantId: str, documentId: str) -> DocumentResponse:
    """Retrieve document metadata processing pipeline status."""
    d = await document_repository.get_document(tenantId, documentId)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentResponse(documentId=d.document_id, filename=d.filename, fileSize=d.file_size, mimeType=d.mime_type, status=d.status, createdAt=d.created_at, updatedAt=d.updated_at)


@router.delete(
    "/v1/tenants/{tenantId}/documents/{documentId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def delete_document(tenantId: str, documentId: str) -> dict[str, str]:
    """Delete document source file, cascade chunks, and mark records deleted."""
    storage_path = await document_repository.soft_delete(tenantId, documentId)
    if storage_path is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    await local_storage.delete_file(storage_path)
    return {"status": "deleted", "documentId": documentId}


@router.post(
    "/v1/tenants/{tenantId}/documents/{documentId}/extract",
    status_code=status.HTTP_200_OK,
    response_model=ExtractResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def extract_document(
    tenantId: str,
    documentId: str,
    payload: ExtractRequest,
) -> ExtractResponse:
    """Extract structured data from a document using a JSON schema."""
    chunks = await document_repository.get_document_chunks(tenantId, documentId)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found.")

    full_text = "\n".join(c.content for c in chunks)

    messages = [
        ChatMessage(
            role="system",
            content=f"Extract structured data from the document according to this JSON schema: {payload.json_schema}. Return ONLY valid JSON.",
        ),
        ChatMessage(role="user", content=full_text),
    ]

    config: dict[str, Any] = {"model": payload.model} if payload.model else {}
    response = await inference_orchestrator.llm.generate(
        InferenceRequest(messages=messages, temperature=0.1, json_schema=payload.json_schema),
        config,
    )
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail="LLM returned invalid JSON") from e

    return ExtractResponse(
        data=data,
        provider=response.finish_reason,
        model=payload.model or "default",
        inputTokens=response.usage.input_tokens,
        outputTokens=response.usage.output_tokens,
    )


@router.get(
    "/v1/tenants/{tenantId}/documents/{documentId}/download-url",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_document_download_url(
    tenantId: str,
    documentId: str,
    expiry: int = 300,
) -> Any:
    """Retrieve a temporary, secure presigned download URL for a document (Client scope)."""
    doc = await document_repository.get_document(tenantId, documentId)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        download_url = await local_storage.generate_presigned_url(doc.storage_path, expiry_seconds=expiry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {e!s}") from e

    return {
        "documentId": documentId,
        "filename": doc.filename,
        "downloadUrl": download_url,
        "expiresInSeconds": expiry,
    }
