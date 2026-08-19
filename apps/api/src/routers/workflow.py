"""Workflow Automation and n8n Integration Router."""

import base64
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.container import (
    config_service,
    ingest_file_sync,
    n8n_dispatcher,
    pii_anonymizer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Workflow"])


class IngestWebhookRequest(BaseModel):
    title: str = Field(..., description="Document or email title")
    content: str | None = Field(None, description="Raw text or markdown content")
    file_base64: str | None = Field(None, description="Base64 encoded binary file data (e.g. PDF/Docx)")
    filename: str | None = Field(None, description="Filename with extension if file_base64 provided")
    source: str = Field(default="n8n_webhook", description="Ingestion source (gmail, gdrive, notion, n8n)")


class ConfigureWebhookRequest(BaseModel):
    n8n_webhook_url: str = Field(..., description="Target n8n HTTP webhook endpoint URL")


@router.post(
    "/tenants/{tenantId}/ingest/webhook",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def inbound_n8n_ingest_webhook(tenantId: str, payload: IngestWebhookRequest) -> Any:
    """Inbound n8n auto-ingest webhook for Gmail, Google Drive, and Notion documents."""
    doc_id = str(uuid.uuid4())
    chunk_count = 0

    if payload.file_base64 and payload.filename:
        try:
            raw_bytes = base64.b64decode(payload.file_base64)
            chunk_count = await ingest_file_sync(
                file_content=raw_bytes,
                filename=payload.filename,
                document_id=doc_id,
                tenant_id=tenantId,
            )
        except Exception as err:
            logger.error(f"Failed to process base64 file webhook for tenant '{tenantId}': {err}")
            raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {err}") from err

    elif payload.content:
        # Inline PII anonymization pass-through
        anonymized_text = pii_anonymizer.anonymize_text(payload.content)
        raw_bytes = anonymized_text.encode("utf-8")
        filename = f"{payload.title}.md"
        try:
            chunk_count = await ingest_file_sync(
                file_content=raw_bytes,
                filename=filename,
                document_id=doc_id,
                tenant_id=tenantId,
            )
        except Exception as err:
            logger.error(f"Failed to process text content webhook for tenant '{tenantId}': {err}")
            raise HTTPException(status_code=400, detail=f"Failed to ingest content: {err}") from err

    else:
        raise HTTPException(status_code=400, detail="Must supply either 'content' or 'file_base64' and 'filename'.")

    return {
        "status": "ingested",
        "tenant_id": tenantId,
        "document_id": doc_id,
        "chunks": chunk_count,
        "source": payload.source,
    }


@router.post(
    "/admin/tenants/{tenantId}/workflow/webhooks",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def configure_n8n_webhook_url(tenantId: str, payload: ConfigureWebhookRequest) -> Any:
    """Configure active n8n outbound event webhook URL for a tenant (Admin only)."""
    config = await config_service.get_tenant_config(tenantId)
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    if not hasattr(config, "metadata") or config.metadata is None:
        config.metadata = {}

    config.metadata["n8n_webhook_url"] = payload.n8n_webhook_url
    await config_service.update_tenant_config(tenantId, config)

    # Send a test ping to n8n webhook
    ping_res = await n8n_dispatcher.dispatch_event(
        webhook_url=payload.n8n_webhook_url,
        event_type="n8n.webhook.configured",
        tenant_id=tenantId,
        payload={"message": "Retriever n8n webhook successfully linked!"},
    )

    return {
        "status": "configured",
        "tenant_id": tenantId,
        "n8n_webhook_url": payload.n8n_webhook_url,
        "ping_result": ping_res,
    }


@router.get(
    "/workflow/n8n-spec",
    status_code=status.HTTP_200_OK,
)
async def get_n8n_openapi_spec() -> Any:
    """Retrieve OpenAPI 3.0 specification tailored for n8n HTTP Nodes."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Retriever Enterprise n8n Workflow API",
            "version": "v0.51.0",
            "description": "OpenAPI specification for 1-click import into n8n HTTP Nodes.",
        },
        "servers": [{"url": "https://rag.prateeq.in"}],
        "paths": {
            "/v1/tenants/{tenantId}/ingest/webhook": {
                "post": {
                    "summary": "Inbound Document Auto-Ingest Webhook",
                    "operationId": "n8nIngestDocument",
                    "parameters": [{"name": "tenantId", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "content": {"type": "string"},
                                        "file_base64": {"type": "string"},
                                        "filename": {"type": "string"},
                                        "source": {"type": "string", "default": "n8n_webhook"},
                                    },
                                    "required": ["title"],
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Document ingested successfully"}},
                }
            }
        },
    }
