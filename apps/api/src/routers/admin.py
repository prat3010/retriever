"""Admin API routes."""
import hashlib
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key
from src.config import settings
from src.container import (
    admin_repository,
    audit_logger,
    backup_service,
    battery_service,
    celery_app,
    compliance_certificate_service,
    config_service,
    document_repository,
    eval_dataset_repo,
    eval_run_repo,
    eval_service,
    feedback_repo,
    hard_purge_service,
    identity_provider,
    inference_orchestrator,
    ingest_file_sync,
    local_storage,
    online_eval_repo,
    pii_anonymizer,
    retention_worker,
    search_service,
    template_registry,
    tenant_registry,
    user_repository,
)
from src.domain.abstractions.backup import (
    BackupSnapshotMetadata,
    BackupTriggerRequest,
    BackupTriggerResponse,
    RestoreRequest,
    RestoreResponse,
)
from src.domain.abstractions.batteries import PlatformBatteriesResponse
from src.domain.abstractions.compliance import (
    ComplianceCertificateDTO,
    ComplianceVerificationResponse,
    MaskingMode,
    PiiCategory,
    PiiRedactionRequest,
)
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.connector import ConnectorConfig
from src.domain.abstractions.edge_router import (
    EdgeRoutingDecision,
    MultiRegionClusterStatus,
    RegionProbeResponse,
)
from src.domain.abstractions.exceptions import PromptTemplateNotFoundError
from src.domain.abstractions.experiment import ExperimentConfig
from src.domain.abstractions.inference import PromptTemplate
from src.domain.abstractions.ingestion import Document
from src.domain.connectors.registry import ConnectorRegistry
from src.domain.ingestion.chunker_factory import ChunkerFactory
from src.schemas.admin import (
    ApplyPresetRequest,
    CreateApiKeyRequest,
    CreatePromptRequest,
    CreateUserRequest,
    PreviewPromptRequest,
    UserResponse,
)
from src.schemas.chunking import (
    ChunkPreviewItem,
    ChunkPreviewRequest,
    ChunkPreviewResponse,
)
from src.schemas.connector import (
    ConnectorSyncResponse,
    CreateConnectorRequest,
    UpdateConnectorRequest,
)
from src.schemas.document import DocumentResponse
from src.schemas.evaluation import (
    AddEvalQuestionRequest,
    BulkImportQuestionsRequest,
    CreateEvalDatasetRequest,
    NliClassificationDTO,
    NliEvaluateRequest,
    NliEvaluateResponse,
    RegressionGateRequest,
    RegressionGateResponse,
    SelfTuningReportDTO,
    SlmClaimAnalysisDTO,
    SlmJudgeRequest,
    SlmJudgeResponse,
    SynthesizeDatasetRequest,
    SynthesizeDatasetResponse,
    TriggerSelfTuneRequest,
)
from src.schemas.experiment import (
    CreateExperimentRequest,
    ExperimentMetricsResponse,
    UpdateExperimentRequest,
    UpdateExperimentStatusRequest,
    VariantMetricItem,
)
from src.schemas.graph import (
    CommunityDetectRequest,
    CommunityDetectResponse,
    CommunitySummaryDTO,
    GraphCapabilitiesResponse,
    GraphEngineSwitchRequest,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphSummaryResponse,
)
from src.schemas.telemetry import (
    AlertHistoryItemDTO,
    TenantLiveTelemetryDTO,
    TestAlertRequest,
    TestAlertResponse,
)
from src.schemas.tenant import TenantListItem

router = APIRouter(prefix="/v1/admin", tags=["Admin"])



class VerifyAdminKeyResponse(BaseModel):
    valid: bool


@router.get(
    "/verify-key",
    status_code=status.HTTP_200_OK,
    response_model=VerifyAdminKeyResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def verify_admin_key_endpoint() -> VerifyAdminKeyResponse:
    return VerifyAdminKeyResponse(valid=True)


@router.get(
    "/tenants",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_tenants(
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    cursor: str | None = None,
) -> Any:
    if cursor is not None:
        query_cursor = cursor if cursor != "" else None
        items, next_cursor, has_more = await tenant_registry.list_tenants_cursor(
            search=search, limit=limit, cursor=query_cursor
        )
        return {
            "items": [
                TenantListItem(
                    tenantId=str(t.tenant_id),
                    name=t.name,
                    status=t.status,
                    tier=t.tier,
                    createdAt=t.created_at,
                )
                for t in items
            ],
            "pagination": {
                "nextCursor": next_cursor,
                "limit": limit,
                "hasMore": has_more
            }
        }
    else:
        tenants, total = await tenant_registry.list_tenants(search=search, limit=limit, offset=offset)
        return {
            "items": [
                TenantListItem(
                    tenantId=str(t.tenant_id),
                    name=t.name,
                    status=t.status,
                    tier=t.tier,
                    createdAt=t.created_at,
                )
                for t in tenants
            ],
            "total": total,
        }


@router.get(
    "/tenants/{tenantId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_tenant(tenantId: str) -> dict:
    tenant = await tenant_registry.get_tenant(tenantId)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return {
        "tenantId": str(tenant.tenant_id),
        "name": tenant.name,
        "status": tenant.status,
        "tier": tenant.tier,
        "createdAt": tenant.created_at,
    }


@router.delete(
    "/tenants/{tenantId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_deactivate_tenant(tenantId: str) -> dict[str, str]:
    found = await tenant_registry.deactivate_tenant(tenantId)
    if not found:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    await audit_logger.write(tenantId, "tenant.deactivated", "Tenant deactivated")
    return {"status": "deactivated", "tenantId": tenantId}


@router.get(
    "/tenants/{tenantId}/users",
    status_code=status.HTTP_200_OK,
    response_model=list[UserResponse],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_users(tenantId: str) -> list[UserResponse]:
    users = await user_repository.list_users(tenantId)
    return [
        UserResponse(
            userId=u.user_id,
            tenantId=u.tenant_id,
            externalId=u.external_id,
            displayName=u.display_name,
            isActive=u.is_active,
            createdAt=u.created_at,
        )
        for u in users
    ]


@router.post(
    "/tenants/{tenantId}/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_user(tenantId: str, payload: CreateUserRequest) -> UserResponse:
    try:
        user = await user_repository.create_user(
            tenant_id=tenantId,
            external_id=payload.external_id,
            display_name=payload.display_name,
        )
        await audit_logger.write(tenantId, "user.created", f"User '{payload.external_id}' created")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    return UserResponse(
        userId=user.user_id,
        tenantId=user.tenant_id,
        externalId=user.external_id,
        displayName=user.display_name,
        isActive=user.is_active,
        createdAt=user.created_at,
    )


@router.delete(
    "/tenants/{tenantId}/users/{userId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_delete_user(tenantId: str, userId: str) -> dict:
    await user_repository.deactivate_user(tenant_id=tenantId, user_id=userId)
    await audit_logger.write(tenantId, "user.deactivated", f"User '{userId}' deactivated")
    return {"status": "deactivated", "userId": userId}


@router.get(
    "/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_api_keys(tenantId: str) -> list[dict]:
    keys = await identity_provider.list_api_keys(tenantId)
    return [
        {
            "keyId": k.key_id,
            "name": k.name,
            "prefix": k.prefix,
            "role": k.role,
            "status": k.status,
            "createdAt": k.created_at,
            "expiresAt": k.expires_at,
        }
        for k in keys
    ]


@router.post(
    "/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_api_key(tenantId: str, payload: CreateApiKeyRequest) -> dict:
    raw_key, metadata = await identity_provider.create_api_key(
        tenant_id=tenantId,
        name=payload.name,
        expires_in_days=payload.expires_in_days,
        role=payload.role,
    )
    await audit_logger.write(tenantId, "api_key.created", f"API key '{payload.name}' ({payload.role}) created")
    return {
        "apiKey": raw_key,
        "keyId": metadata.key_id,
        "tenantId": metadata.tenant_id,
        "prefix": metadata.prefix,
        "role": metadata.role,
        "status": metadata.status,
        "expiresAt": metadata.expires_at,
    }


@router.delete(
    "/tenants/{tenantId}/api-keys/{keyId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_revoke_api_key(tenantId: str, keyId: str) -> dict[str, str]:
    found = await identity_provider.revoke_api_key(tenantId, keyId)
    if not found:
        raise HTTPException(status_code=404, detail="API key not found.")
    await audit_logger.write(tenantId, "api_key.revoked", f"API key '{keyId}' revoked")
    return {"status": "revoked", "keyId": keyId}


@router.get(
    "/tenants/{tenantId}/documents",
    status_code=status.HTTP_200_OK,
    response_model=list[DocumentResponse],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_documents(tenantId: str) -> list[DocumentResponse]:
    docs = await document_repository.list_documents(tenantId, bypass_rls=True)
    return [DocumentResponse(documentId=d.document_id, filename=d.filename, fileSize=d.file_size, mimeType=d.mime_type, status=d.status, createdAt=d.created_at, updatedAt=d.updated_at) for d in docs]


@router.post(
    "/tenants/{tenantId}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_upload_document(
    tenantId: str,
    file: UploadFile = File(...),
) -> dict:
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    existing = await document_repository.find_by_hash(tenantId, file_hash)
    if existing:
        return {
            "documentId": existing.document_id,
            "status": "pending",
            "fileHash": file_hash,
            "createdAt": existing.created_at,
        }

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

    return {
        "documentId": str(doc_id),
        "status": "pending",
        "fileHash": file_hash,
        "createdAt": doc.created_at,
    }


@router.post(
    "/tenants/{tenantId}/documents/ingest",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_ingest_document_sync(
    tenantId: str,
    file: UploadFile = File(...),
) -> dict:
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    doc_id = str(uuid.uuid4())

    chunk_count = await ingest_file_sync(
        tenant_id=tenantId,
        document_id=doc_id,
        filename=file.filename,
        file_content=content,
        file_hash=file_hash,
        mime_type=file.content_type or "application/octet-stream",
        embedder=search_service.embedder,
    )

    return {
        "documentId": doc_id,
        "status": "indexed",
        "fileHash": file_hash,
        "chunksIndexed": chunk_count,
    }


@router.post(
    "/tenants/{tenantId}/documents/{documentId}/process",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_process_document(
    tenantId: str,
    documentId: str,
    target_engine: Literal["laptop", "oracle", "auto"] = Query("auto", alias="targetEngine"),
) -> dict:
    doc = await document_repository.get_document(tenantId, documentId)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc.status = "PROCESSING"
    await document_repository.create_document(tenantId, doc)

    file_content = await local_storage.read_file(doc.storage_path)
    if file_content is None and settings.REMOTE_STORAGE_API_URL:
        try:
            remote_url = f"{settings.REMOTE_STORAGE_API_URL.rstrip('/')}/v1/admin/tenants/{tenantId}/documents/{documentId}/file"
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(
                    remote_url,
                    headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
                )
                if res.status_code == 200:
                    file_content = res.content
        except Exception:
            pass

    if file_content is None:
        doc.status = "FAILED"
        await document_repository.create_document(tenantId, doc)
        raise HTTPException(status_code=404, detail="Document file not found on local disk or remote storage.")

    try:
        chunk_count = await ingest_file_sync(
            tenant_id=tenantId,
            document_id=documentId,
            filename=doc.filename,
            file_content=file_content,
            file_hash=doc.file_hash,
            mime_type=doc.mime_type,
            embedder=search_service.embedder,
        )
        doc.status = "INDEXED"
        await document_repository.create_document(tenantId, doc)
        return {
            "documentId": documentId,
            "status": "indexed",
            "chunksIndexed": chunk_count,
            "targetEngine": target_engine,
        }
    except Exception as err:
        doc.status = "FAILED"
        await document_repository.create_document(tenantId, doc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {err}") from err


@router.delete(
    "/tenants/{tenantId}/documents/{documentId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_delete_document(tenantId: str, documentId: str) -> dict[str, str]:
    storage_path = await document_repository.soft_delete(tenantId, documentId)
    if storage_path is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    await local_storage.delete_file(storage_path)
    return {"status": "deleted", "documentId": documentId}


@router.get(
    "/tenants/{tenantId}/documents/{documentId}/download",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_document_download_url(tenantId: str, documentId: str) -> dict[str, str]:
    doc = await document_repository.get_document(tenantId, documentId, bypass_rls=True)
    if not doc or str(doc.tenant_id) != tenantId:
        raise HTTPException(status_code=404, detail="Document not found.")

    if settings.STORAGE_PROVIDER == "s3" and hasattr(local_storage, "generate_presigned_url"):
        try:
            url = await local_storage.generate_presigned_url(doc.storage_path)
            return {"downloadUrl": url}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate pre-signed URL: {e!s}") from e
    else:
        return {"downloadUrl": f"/v1/admin/tenants/{tenantId}/documents/{documentId}/file"}


@router.get(
    "/tenants/{tenantId}/documents/{documentId}/file",
    dependencies=[Depends(verify_admin_key)],
)
async def admin_download_document_file(tenantId: str, documentId: str) -> FileResponse:
    doc = await document_repository.get_document(tenantId, documentId, bypass_rls=True)
    if not doc or str(doc.tenant_id) != tenantId:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=404, detail="Physical file not found on local storage.")

    return FileResponse(
        path=doc.storage_path,
        filename=doc.filename,
        media_type=doc.mime_type,
    )


@router.get(
    "/platform/stats",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_platform_stats() -> dict[str, Any]:
    return await admin_repository.get_platform_stats()


@router.get(
    "/platform/batteries",
    status_code=status.HTTP_200_OK,
    response_model=PlatformBatteriesResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_platform_batteries() -> PlatformBatteriesResponse:
    return battery_service.get_platform_batteries()


@router.get(
    "/platform/backups",
    status_code=status.HTTP_200_OK,
    response_model=list[BackupSnapshotMetadata],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_backups() -> list[BackupSnapshotMetadata]:
    return await backup_service.list_snapshots()


@router.post(
    "/platform/backups/trigger",
    status_code=status.HTTP_200_OK,
    response_model=BackupTriggerResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_trigger_backup(
    payload: BackupTriggerRequest | None = None,
) -> BackupTriggerResponse:
    req = payload or BackupTriggerRequest()
    return await backup_service.create_snapshot(req)


@router.post(
    "/platform/backups/restore",
    status_code=status.HTTP_200_OK,
    response_model=RestoreResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_restore_backup(
    payload: RestoreRequest,
) -> RestoreResponse:
    return await backup_service.restore_snapshot(payload)


@router.post(
    "/platform/reset",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_platform_reset(include_system_tenant: bool = False) -> dict[str, Any]:
    deleted = await admin_repository.reset_platform(
        include_system_tenant=include_system_tenant
    )
    msg = (
        "All data cleared including system tenant."
        if include_system_tenant
        else "All non-system tenant data cleared successfully."
    )
    return {"status": "success", "message": msg, "tenantsDeleted": deleted}


@router.get(
    "/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_tenant_config(tenantId: str) -> TenantConfiguration:
    return await config_service.get_tenant_config(tenantId)


@router.put(
    "/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_tenant_config(tenantId: str, payload: TenantConfiguration) -> dict[str, str]:
    await config_service.update_tenant_config(tenantId, payload)
    await audit_logger.write(tenantId, "config.updated", "Tenant configuration updated")
    return {"tenantId": tenantId, "status": "updated"}


@router.post(
    "/tenants/{tenantId}/config/apply-preset",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def apply_industry_preset(
    tenantId: str,
    payload: ApplyPresetRequest,
) -> dict[str, str]:
    from src.domain.config.presets import get_preset_config
    preset_data = get_preset_config(payload.preset)
    if not preset_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Preset '{payload.preset}' not found. Available: legal, hr, medical, finance"
        )

    current_config = await config_service.get_tenant_config(tenantId)
    config_dict = current_config.model_dump()

    def _deep_merge(target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                _deep_merge(target[k], v)
            else:
                target[k] = v

    _deep_merge(config_dict, preset_data)

    try:
        updated_config = TenantConfiguration.model_validate(config_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to merge preset: {e!s}"
        ) from e

    await config_service.update_tenant_config(tenantId, updated_config)
    await audit_logger.write(tenantId, "config.preset_applied", f"Preset {payload.preset} applied to configuration")
    return {"tenantId": tenantId, "preset": payload.preset, "status": "applied"}


@router.get(
    "/audit-logs",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_audit_logs(
    tenantId: str | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    items, total = await audit_logger.list(
        tenant_id=tenantId, action=action, limit=limit, offset=offset,
    )
    return {"items": items, "total": total}


@router.get(
    "/tenants/{tenantId}/prompts",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_prompts(tenantId: str) -> list[dict]:
    templates = await template_registry.list_templates(tenantId, bypass_rls=True)
    return [
        {
            "name": t.name,
            "content": t.content,
            "isSystemPrompt": t.is_system_prompt,
        }
        for t in templates
    ]


@router.post(
    "/tenants/{tenantId}/prompts",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_prompt(tenantId: str, payload: CreatePromptRequest) -> dict:
    existing = await template_registry.get_template(tenantId, payload.name, bypass_rls=True)
    if existing:
        raise HTTPException(status_code=409, detail="Prompt template already exists.")
    template = PromptTemplate(
        tenant_id=tenantId,
        name=payload.name,
        content=payload.content,
        is_system_prompt=payload.is_system_prompt,
    )
    await template_registry.save_template(tenantId, template, bypass_rls=True)
    return {"name": payload.name, "status": "created"}


@router.get(
    "/tenants/{tenantId}/prompts/{name}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_prompt(tenantId: str, name: str) -> dict:
    template = await template_registry.get_template(tenantId, name, bypass_rls=True)
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return {
        "name": template.name,
        "content": template.content,
        "isSystemPrompt": template.is_system_prompt,
    }


@router.put(
    "/tenants/{tenantId}/prompts/{name}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_prompt(tenantId: str, name: str, payload: CreatePromptRequest) -> dict:
    existing = await template_registry.get_template(tenantId, name, bypass_rls=True)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    template = PromptTemplate(
        tenant_id=tenantId,
        name=name,
        content=payload.content,
        is_system_prompt=payload.is_system_prompt,
    )
    await template_registry.save_template(tenantId, template, bypass_rls=True)
    return {"name": name, "status": "updated"}


@router.delete(
    "/tenants/{tenantId}/prompts/{name}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_delete_prompt(tenantId: str, name: str) -> dict[str, str]:
    found = await template_registry.delete_template(tenantId, name, bypass_rls=True)
    if not found:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return {"name": name, "status": "deleted"}


@router.post(
    "/tenants/{tenantId}/prompts/preview",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_preview_prompt(tenantId: str, payload: PreviewPromptRequest) -> dict:
    try:
        messages = await inference_orchestrator.prompt_builder.build_messages(
            tenant_id=tenantId,
            query=payload.query,
            history=[],
            context_chunks=[{"chunk_id": "demo", "content": payload.context or "Sample context for preview."}],
            system_prompt_name=payload.name,
        )
    except PromptTemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Prompt template not found.") from None
    return {
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }


@router.post(
    "/tenants/{tenantId}/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_reindex_codebase(tenantId: str, background_tasks: BackgroundTasks) -> dict[str, str]:
    if tenantId != "00000000-0000-0000-0000-000000000000":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codebase reindexing is only supported for the System Tenant (00000000-0000-0000-0000-000000000000).",
        )

    from src.scripts.ingest_self import main as ingest_main

    background_tasks.add_task(ingest_main)

    return {"status": "accepted", "message": "Codebase reindexing started in the background."}


@router.get(
    "/tenants/{tenantId}/feedback/analytics",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_tenant_feedback_analytics(tenantId: str) -> Any:
    analytics = await feedback_repo.get_feedback_analytics(tenantId)
    return analytics


@router.get(
    "/tenants/{tenantId}/eval-datasets",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def list_eval_datasets(tenantId: str) -> Any:
    datasets = await eval_dataset_repo.list_datasets(tenantId)
    return [d.model_dump() for d in datasets]


@router.post(
    "/tenants/{tenantId}/eval-datasets",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def create_eval_dataset(tenantId: str, body: CreateEvalDatasetRequest) -> Any:
    from src.domain.abstractions.evaluation import EvalDataset
    dataset = await eval_dataset_repo.create_dataset(EvalDataset(
        tenant_id=tenantId,
        name=body.name,
        description=body.description,
    ))
    return dataset.model_dump()


@router.delete(
    "/tenants/{tenantId}/eval-datasets/{datasetId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def delete_eval_dataset(tenantId: str, datasetId: str) -> Any:
    deleted = await eval_dataset_repo.delete_dataset(tenantId, datasetId)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"status": "deleted"}


@router.get(
    "/tenants/{tenantId}/eval-datasets/{datasetId}/questions",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def list_eval_questions(tenantId: str, datasetId: str) -> Any:
    questions = await eval_dataset_repo.list_questions(datasetId)
    return [q.model_dump() for q in questions]


@router.post(
    "/tenants/{tenantId}/eval-datasets/{datasetId}/questions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def add_eval_question(tenantId: str, datasetId: str, body: AddEvalQuestionRequest) -> Any:
    from src.domain.abstractions.evaluation import EvalQuestion
    question = await eval_dataset_repo.add_question(EvalQuestion(
        dataset_id=datasetId,
        question=body.question,
        ground_truth_answer=body.ground_truth_answer,
        relevant_chunk_ids=body.relevant_chunk_ids,
    ))
    return question.model_dump()


@router.post(
    "/tenants/{tenantId}/eval-datasets/{datasetId}/import",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def bulk_import_questions(tenantId: str, datasetId: str, body: BulkImportQuestionsRequest) -> Any:
    from src.domain.abstractions.evaluation import EvalQuestion
    imported = []
    for q in body.questions:
        question = await eval_dataset_repo.add_question(EvalQuestion(
            dataset_id=datasetId,
            question=q.question,
            ground_truth_answer=q.ground_truth_answer,
            relevant_chunk_ids=q.relevant_chunk_ids,
        ))
        imported.append(question)
    return {"imported": len(imported)}


@router.post(
    "/tenants/{tenantId}/eval-datasets/{datasetId}/run",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_key)],
)
async def trigger_eval_run(tenantId: str, datasetId: str, background_tasks: BackgroundTasks) -> Any:
    background_tasks.add_task(eval_service.run_evaluation, tenantId, datasetId, "manual")
    return {"status": "accepted"}


@router.get(
    "/tenants/{tenantId}/eval-runs",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def list_eval_runs(tenantId: str) -> Any:
    runs = await eval_run_repo.list_runs(tenantId)
    return [r.model_dump() for r in runs]


@router.get(
    "/tenants/{tenantId}/eval-runs/{runId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_eval_run(tenantId: str, runId: str) -> Any:
    run = await eval_run_repo.get_run(tenantId, runId)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run.model_dump()


@router.get(
    "/tenants/{tenantId}/eval-runs/{runId}/results",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_eval_run_results(tenantId: str, runId: str) -> Any:
    results = await eval_run_repo.list_results(runId)
    return [r.model_dump() for r in results]


@router.get(
    "/tenants/{tenantId}/evaluation/online/summary",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_online_evaluation_summary(tenantId: str) -> Any:
    return await online_eval_repo.get_online_summary(tenantId)


@router.get(
    "/tenants/{tenantId}/evaluation/online/logs",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def list_online_evaluation_logs(
    tenantId: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Any:
    logs, total = await online_eval_repo.list_online_logs(tenantId, limit=limit, offset=offset)
    return {"items": logs, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/tenants/{tenantId}/evaluation/online/logs/{evalId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_online_evaluation_log(tenantId: str, evalId: str) -> Any:
    log = await online_eval_repo.get_online_log(tenantId, evalId)
    if not log:
        raise HTTPException(status_code=404, detail="Evaluation record not found.")
    return log


class AdminGroundingDiffRequest(BaseModel):
    answer: str
    contexts: list[str] = Field(default_factory=list)


@router.post(
    "/tenants/{tenantId}/evaluation/grounding-diff",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def compute_admin_grounding_diff(
    tenantId: str,
    payload: AdminGroundingDiffRequest,
) -> Any:
    from sqlalchemy import text

    from src.adapters.database.connection import tenant_session
    from src.domain.evaluation.nli_evaluator import NliEvaluator

    contexts = list(payload.contexts) if payload.contexts else []
    if not contexts:
        try:
            async with tenant_session(tenant_id=tenantId) as session:
                res = await session.execute(
                    text("SELECT content FROM document_chunks WHERE tenant_id = CAST(:tenant_id AS uuid) ORDER BY created_at DESC LIMIT 15"),
                    {"tenant_id": tenantId},
                )
                contexts = [row[0] for row in res.fetchall() if row[0]]
        except Exception:
            contexts = []

    nli = NliEvaluator()
    claims = nli.extract_claims(payload.answer)
    res = nli.evaluate_claims(claims, contexts)
    return {
        "tenant_id": tenantId,
        "total_claims": res.total_claims,
        "entailed_claims": res.entailed_claims,
        "contradicted_claims": res.contradicted_claims,
        "neutral_claims": res.neutral_claims,
        "faithfulness_score": res.faithfulness_score,
        "hallucination_index": res.hallucination_index,
        "claims": [
            {
                "claim": c.claim,
                "premise": c.premise,
                "status": c.status,
                "entailment_prob": c.entailment_prob,
                "contradiction_prob": c.contradiction_prob,
                "neutral_prob": c.neutral_prob,
            }
            for c in res.classifications
        ],
    }


class AnonymizeRequest(BaseModel):
    text: str
    types: list[str] | None = None
    categories: list[PiiCategory] | None = None
    masking_mode: MaskingMode = MaskingMode.REDACT
    custom_patterns: list[str] | None = None


@router.delete(
    "/tenants/{tenantId}/compliance/documents/{documentId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_hard_purge_document(tenantId: str, documentId: str) -> Any:
    certificate = await hard_purge_service.purge_document_with_certificate(
        tenant_id=tenantId,
        document_id=documentId,
        requester="admin_system",
        reason="Admin Hard Purge Document",
    )
    return {
        "status": "purged",
        "documentId": documentId,
        "stats": certificate.records_purged,
        "certificate": certificate.model_dump(),
    }


@router.post(
    "/tenants/{tenantId}/compliance/forget",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_forget_tenant(tenantId: str) -> Any:
    certificate = await hard_purge_service.purge_tenant_with_certificate(
        tenant_id=tenantId,
        requester="admin_system",
        reason="GDPR Article 17 Full Tenant Erasure",
    )
    return {
        "status": "tenant_purged",
        "tenantId": tenantId,
        "stats": certificate.records_purged,
        "certificate": certificate.model_dump(),
    }


@router.get(
    "/tenants/{tenantId}/compliance/certificates",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_compliance_certificates(tenantId: str) -> list[ComplianceCertificateDTO]:
    return await hard_purge_service.get_certificates(tenantId)


@router.get(
    "/compliance/verify/{certificateId}",
    status_code=status.HTTP_200_OK,
)
async def verify_compliance_certificate(certificateId: str) -> ComplianceVerificationResponse:
    cert = await hard_purge_service.get_certificate_by_id(certificateId)
    if not cert:
        return ComplianceVerificationResponse(
            certificate_id=certificateId,
            is_valid=False,
            audit_signature="",
            certificate=None,
            message="Certificate ID not found in compliance ledger.",
        )
    is_valid = compliance_certificate_service.verify_certificate(cert)
    return ComplianceVerificationResponse(
        certificate_id=certificateId,
        is_valid=is_valid,
        audit_signature=cert.sha256_audit_signature,
        certificate=cert,
        message="Cryptographic HMAC-SHA256 signature is authentic and untampered." if is_valid else "Cryptographic signature mismatch: certificate payload has been tampered.",
    )


@router.post(
    "/tenants/{tenantId}/compliance/anonymize",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_anonymize_text(tenantId: str, payload: AnonymizeRequest) -> Any:
    res = pii_anonymizer.redact(
        PiiRedactionRequest(
            text=payload.text,
            categories=payload.categories,
            masking_mode=payload.masking_mode,
            custom_patterns=payload.custom_patterns,
        )
    )
    return {
        "redacted_text": res.redacted_text,
        "original_length": res.original_length,
        "total_redacted": res.total_redacted,
        "entities_detected": [m.model_dump() for m in res.entities_detected],
    }


@router.post(
    "/tenants/{tenantId}/compliance/run-retention-purge",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_run_retention_purge(
    tenantId: str,
    retention_days: int = Query(default=90, ge=1),
) -> Any:
    res = await retention_worker.scan_and_purge_expired_documents(tenantId, retention_days)
    return {"status": "completed", "tenantId": tenantId, "result": res}




@router.get("/storage/internal/{path:path}")
async def serve_internal_storage(
    path: str,
    x_internal_key: str = Header(""),
) -> Response:
    if not x_internal_key or x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal key.")
    content = await local_storage.read_file(path)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return Response(content=content, media_type="application/octet-stream")


@router.post(
    "/tenants/{tenantId}/documents/chunk-preview",
    status_code=status.HTTP_200_OK,
    response_model=ChunkPreviewResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_chunk_preview(
    tenantId: str,
    payload: ChunkPreviewRequest,
) -> ChunkPreviewResponse:
    """Dry-run sandbox text chunking split preview for auditor inspection."""
    chunker = ChunkerFactory.get_chunker(payload.strategy)
    items_data = chunker.split_text_with_offsets(
        text=payload.text,
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
    )

    items = [
        ChunkPreviewItem(
            chunkIndex=c["chunk_index"],
            content=c["content"],
            tokenCount=c["token_count"],
            charCount=c["char_count"],
            startCharIdx=c["start_char_idx"],
            endCharIdx=c["end_char_idx"],
            metaData=c["meta_data"],
        )
        for c in items_data
    ]

    total_tokens = sum(c.tokenCount for c in items)
    total_chars = len(payload.text)
    avg_tokens = (total_tokens / len(items)) if items else 0.0

    return ChunkPreviewResponse(
        totalChunks=len(items),
        totalTokens=total_tokens,
        totalChars=total_chars,
        avgChunkTokens=round(avg_tokens, 2),
        chunks=items,
    )


# ── Experiment Management APIs ────────────────────────────────────────────────


@router.get(
    "/tenants/{tenantId}/experiments",
    status_code=status.HTTP_200_OK,
    response_model=list[ExperimentConfig],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_experiments(tenantId: str) -> list[ExperimentConfig]:
    config = await config_service.get_tenant_config(tenantId)
    return config.experiments or []


@router.post(
    "/tenants/{tenantId}/experiments",
    status_code=status.HTTP_201_CREATED,
    response_model=ExperimentConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_experiment(
    tenantId: str,
    payload: CreateExperimentRequest,
) -> ExperimentConfig:
    config = await config_service.get_tenant_config(tenantId)
    exp_id = f"exp_{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    new_exp = ExperimentConfig(
        id=exp_id,
        name=payload.name,
        description=payload.description,
        status="draft",
        variants=payload.variants,
        created_at=now,
        updated_at=now,
    )

    if not config.experiments:
        config.experiments = []
    config.experiments.append(new_exp)

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(tenantId, "experiment.created", f"Created experiment '{payload.name}' ({exp_id})")
    return new_exp


@router.get(
    "/tenants/{tenantId}/experiments/{experimentId}",
    status_code=status.HTTP_200_OK,
    response_model=ExperimentConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_experiment(tenantId: str, experimentId: str) -> ExperimentConfig:
    config = await config_service.get_tenant_config(tenantId)
    for exp in config.experiments or []:
        if exp.id == experimentId:
            return exp
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment '{experimentId}' not found.")


@router.put(
    "/tenants/{tenantId}/experiments/{experimentId}",
    status_code=status.HTTP_200_OK,
    response_model=ExperimentConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_experiment(
    tenantId: str,
    experimentId: str,
    payload: UpdateExperimentRequest,
) -> ExperimentConfig:
    config = await config_service.get_tenant_config(tenantId)
    target: ExperimentConfig | None = None
    for exp in config.experiments or []:
        if exp.id == experimentId:
            target = exp
            break

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment '{experimentId}' not found.")

    if payload.name is not None:
        target.name = payload.name
    if payload.description is not None:
        target.description = payload.description
    if payload.variants is not None:
        target.variants = payload.variants
    target.updated_at = datetime.now(UTC).isoformat()

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(tenantId, "experiment.updated", f"Updated experiment '{experimentId}'")
    return target


@router.post(
    "/tenants/{tenantId}/experiments/{experimentId}/status",
    status_code=status.HTTP_200_OK,
    response_model=ExperimentConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_experiment_status(
    tenantId: str,
    experimentId: str,
    payload: UpdateExperimentStatusRequest,
) -> ExperimentConfig:
    config = await config_service.get_tenant_config(tenantId)
    target: ExperimentConfig | None = None
    for exp in config.experiments or []:
        if exp.id == experimentId:
            target = exp
            break

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment '{experimentId}' not found.")

    target.status = payload.status
    target.updated_at = datetime.now(UTC).isoformat()

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(
        tenantId, "experiment.status_changed", f"Changed experiment '{experimentId}' status to '{payload.status}'"
    )
    return target


@router.delete(
    "/tenants/{tenantId}/experiments/{experimentId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_delete_experiment(tenantId: str, experimentId: str) -> dict[str, str]:
    config = await config_service.get_tenant_config(tenantId)
    original_count = len(config.experiments or [])
    config.experiments = [e for e in (config.experiments or []) if e.id != experimentId]

    if len(config.experiments) == original_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment '{experimentId}' not found.")

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(tenantId, "experiment.deleted", f"Deleted experiment '{experimentId}'")
    return {"status": "deleted", "experimentId": experimentId}


@router.get(
    "/tenants/{tenantId}/experiments/{experimentId}/metrics",
    status_code=status.HTTP_200_OK,
    response_model=ExperimentMetricsResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_experiment_metrics(
    tenantId: str,
    experimentId: str,
) -> ExperimentMetricsResponse:
    config = await config_service.get_tenant_config(tenantId)
    target: ExperimentConfig | None = None
    for exp in config.experiments or []:
        if exp.id == experimentId:
            target = exp
            break

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment '{experimentId}' not found.")

    # Fetch inference logs for metric calculation
    from sqlalchemy import select

    from src.adapters.database.connection import tenant_session
    from src.adapters.database.models import InferenceLogDb

    variant_metrics: list[VariantMetricItem] = []
    total_exp_requests = 0

    async with tenant_session(tenant_id=tenantId, bypass_rls=True) as session:
        stmt = select(InferenceLogDb).where(
            InferenceLogDb.tenant_id == uuid.UUID(tenantId),
            InferenceLogDb.notes.like(f"%experiment={experimentId}%"),
        )
        logs = (await session.execute(stmt)).scalars().all()
        total_exp_requests = len(logs)

        for v in target.variants:
            v_logs = [log for log in logs if log.notes and f"variant={v.id}" in log.notes]
            v_count = len(v_logs)
            v_tokens = sum((log.prompt_tokens or 0) + (log.completion_tokens or 0) for log in v_logs)
            latencies = [float(log.latency_ms) for log in v_logs if log.latency_ms is not None]

            avg_latency = (sum(latencies) / v_count) if v_count and latencies else 0.0
            if latencies:
                sorted_lat = sorted(latencies)
                p95_idx = int(len(sorted_lat) * 0.95)
                p95_latency = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
            else:
                p95_latency = 0.0

            variant_metrics.append(
                VariantMetricItem(
                    variantId=v.id,
                    variantName=v.name or v.id,
                    trafficPct=v.traffic_pct,
                    totalRequests=v_count,
                    totalTokens=v_tokens,
                    avgLatencyMs=round(avg_latency, 2),
                    p95LatencyMs=round(p95_latency, 2),
                    avgFeedbackRating=0.0,
                    errorRate=0.0,
                )
            )

    return ExperimentMetricsResponse(
        experimentId=target.id,
        experimentName=target.name or target.id,
        status=target.status,
        totalExperimentRequests=total_exp_requests,
        variants=variant_metrics,
    )


# ── SaaS Data Connector APIs ──────────────────────────────────────────────────


@router.get(
    "/tenants/{tenantId}/connectors",
    status_code=status.HTTP_200_OK,
    response_model=list[ConnectorConfig],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_connectors(tenantId: str) -> list[ConnectorConfig]:
    config = await config_service.get_tenant_config(tenantId)
    return config.connectors or []


@router.post(
    "/tenants/{tenantId}/connectors",
    status_code=status.HTTP_201_CREATED,
    response_model=ConnectorConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_connector(
    tenantId: str,
    payload: CreateConnectorRequest,
) -> ConnectorConfig:
    config = await config_service.get_tenant_config(tenantId)
    conn_id = f"conn_{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    new_conn = ConnectorConfig(
        id=conn_id,
        name=payload.name,
        connector_type=payload.connector_type,
        status="idle",
        sync_interval_minutes=payload.sync_interval_minutes,
        configuration=payload.configuration,
        created_at=now,
        updated_at=now,
    )

    if not config.connectors:
        config.connectors = []
    config.connectors.append(new_conn)

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(tenantId, "connector.created", f"Created data connector '{payload.name}' ({conn_id})")
    return new_conn


@router.get(
    "/tenants/{tenantId}/connectors/{connectorId}",
    status_code=status.HTTP_200_OK,
    response_model=ConnectorConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_connector(tenantId: str, connectorId: str) -> ConnectorConfig:
    config = await config_service.get_tenant_config(tenantId)
    for conn in config.connectors or []:
        if conn.id == connectorId:
            return conn
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connector '{connectorId}' not found.")


@router.put(
    "/tenants/{tenantId}/connectors/{connectorId}",
    status_code=status.HTTP_200_OK,
    response_model=ConnectorConfig,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_connector(
    tenantId: str,
    connectorId: str,
    payload: UpdateConnectorRequest,
) -> ConnectorConfig:
    config = await config_service.get_tenant_config(tenantId)
    target: ConnectorConfig | None = None
    for conn in config.connectors or []:
        if conn.id == connectorId:
            target = conn
            break

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connector '{connectorId}' not found.")

    if payload.name is not None:
        target.name = payload.name
    if payload.sync_interval_minutes is not None:
        target.sync_interval_minutes = payload.sync_interval_minutes
    if payload.configuration is not None:
        target.configuration = payload.configuration
    if payload.status is not None:
        target.status = payload.status
    target.updated_at = datetime.now(UTC).isoformat()

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(tenantId, "connector.updated", f"Updated connector '{connectorId}'")
    return target


@router.delete(
    "/tenants/{tenantId}/connectors/{connectorId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_delete_connector(tenantId: str, connectorId: str) -> dict[str, str]:
    config = await config_service.get_tenant_config(tenantId)
    orig_len = len(config.connectors or [])
    config.connectors = [c for c in (config.connectors or []) if c.id != connectorId]

    if len(config.connectors) == orig_len:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connector '{connectorId}' not found.")

    await config_service.update_tenant_config(tenantId, config)
    await audit_logger.write(tenantId, "connector.deleted", f"Deleted connector '{connectorId}'")
    return {"status": "deleted", "connectorId": connectorId}


@router.post(
    "/tenants/{tenantId}/connectors/{connectorId}/sync",
    status_code=status.HTTP_200_OK,
    response_model=ConnectorSyncResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_trigger_connector_sync(
    tenantId: str,
    connectorId: str,
) -> ConnectorSyncResponse:
    start_time = datetime.now(UTC)
    config = await config_service.get_tenant_config(tenantId)
    target: ConnectorConfig | None = None
    for conn in config.connectors or []:
        if conn.id == connectorId:
            target = conn
            break

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Connector '{connectorId}' not found.")

    target.status = "syncing"
    await config_service.update_tenant_config(tenantId, config)

    try:
        connector = ConnectorRegistry.get_connector(target.connector_type)
        discovered = await connector.fetch_documents(target)

        ingested_count = 0
        for doc in discovered:
            await ingest_file_sync(
                tenant_id=tenantId,
                filename=doc.filename,
                content_bytes=doc.content.encode("utf-8"),
                mime_type=doc.mime_type,
                tags=["connector", target.connector_type],
            )
            ingested_count += 1

        end_time = datetime.now(UTC)
        duration_ms = (end_time - start_time).total_seconds() * 1000.0

        target.status = "idle"
        target.last_sync_at = end_time.isoformat()
        await config_service.update_tenant_config(tenantId, config)

        await audit_logger.write(
            tenantId,
            "connector.synced",
            f"Synced connector '{connectorId}' (Discovered: {len(discovered)}, Ingested: {ingested_count})",
        )

        return ConnectorSyncResponse(
            connectorId=connectorId,
            status="completed",
            documentsDiscovered=len(discovered),
            documentsIngested=ingested_count,
            durationMs=round(duration_ms, 2),
            message=f"Successfully synced {ingested_count} documents from {target.name}.",
        )
    except Exception as err:
        target.status = "failed"
        await config_service.update_tenant_config(tenantId, config)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connector sync failed: {err!s}",
        ) from err


# ── GraphRAG & Knowledge Graph Management ───────────────────────────────────────

@router.get(
    "/tenants/{tenantId}/graph/capabilities",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=GraphCapabilitiesResponse,
)
async def get_graph_capabilities(tenantId: str) -> GraphCapabilitiesResponse:
    """Check hardware RAM profile, supported graph engines, and active status."""
    import sys

    from src.config import InfraCapabilities
    from src.container import container

    infra = InfraCapabilities.detect()
    config = await config_service.get_tenant_config(tenantId)
    active_engine = config.graph_settings.graph_engine

    neo4j_online = False
    if hasattr(container.graph_repository, "is_online"):
        try:
            neo4j_online = await container.graph_repository.is_online()
        except Exception:
            neo4j_online = False

    if not infra.neo4j_viable:
        return GraphCapabilitiesResponse(
            machine_profile="oracle_vm_lean",
            supported_engines=["postgres"],
            active_engine="postgres",
            neo4j_status="unsupported",
            message="Neo4j engine is disabled on LEAN Oracle VM to safeguard RAM (< 2 GB). Running PostgreSQL Recursive SQL.",
        )

    profile_name = "expanded_vps" if "linux" in sys.platform.lower() else "macbook"
    message = (
        "Dual-engine support active. Neo4j is online and active."
        if neo4j_online
        else "Dual-engine support active. Neo4j is offline; queries fall back seamlessly to PostgreSQL Recursive CTEs."
    )
    return GraphCapabilitiesResponse(
        machine_profile=profile_name,
        supported_engines=["postgres", "neo4j"],
        active_engine=active_engine,
        neo4j_status="online" if neo4j_online else "offline",
        message=message,
    )


@router.post(
    "/tenants/{tenantId}/graph/engine",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def switch_graph_engine(tenantId: str, payload: GraphEngineSwitchRequest) -> dict[str, Any]:
    """1-Click switch active graph engine ('postgres' | 'neo4j')."""
    from src.config import InfraCapabilities

    infra = InfraCapabilities.detect()
    if payload.engine == "neo4j" and not infra.neo4j_viable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neo4j engine cannot be activated on LEAN Oracle VM (RAM < 2GB limit).",
        )

    if payload.engine not in ["postgres", "neo4j"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid graph engine '{payload.engine}'. Allowed: postgres, neo4j.",
        )

    config = await config_service.get_tenant_config(tenantId)
    config.graph_settings.graph_engine = payload.engine
    await config_service.update_tenant_config(tenantId, config)

    await audit_logger.write(tenantId, "graph.engine_switched", f"Switched graph engine to {payload.engine}")
    return {"tenantId": tenantId, "activeEngine": payload.engine, "status": "updated"}


@router.get(
    "/tenants/{tenantId}/graph",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=GraphSummaryResponse,
)
async def get_graph_summary(tenantId: str) -> GraphSummaryResponse:
    """Retrieve tenant knowledge graph statistics."""
    from src.container import container

    summary = await container.graph_repository.get_graph_summary(tenantId)
    return GraphSummaryResponse(
        tenant_id=summary["tenant_id"],
        total_triples=summary["total_triples"],
        unique_entities=summary.get("unique_entities", 0),
        storage_engine=summary.get("storage_engine", "postgres"),
        neo4j_status=summary.get("neo4j_status"),
    )


@router.post(
    "/tenants/{tenantId}/graph/query",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=GraphQueryResponse,
)
async def query_knowledge_graph(tenantId: str, payload: GraphQueryRequest) -> GraphQueryResponse:
    """Execute multi-hop entity graph query."""
    from src.container import container

    res = await container.graph_repository.search_triples(
        tenant_id=tenantId,
        entity=payload.entity,
        max_hops=payload.max_hops,
    )
    return GraphQueryResponse(
        root_entity=res.root_entity,
        max_hops=res.max_hops,
        triples=res.triples,
        connected_entities=res.connected_entities,
    )


@router.delete(
    "/tenants/{tenantId}/graph/triples/{tripleId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def delete_graph_triple(tenantId: str, tripleId: str) -> dict[str, Any]:
    """Delete a single knowledge graph triple."""
    from src.container import container

    deleted = await container.graph_repository.delete_triple(tenantId, tripleId)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triple '{tripleId}' not found.",
        )
    return {"tenantId": tenantId, "tripleId": tripleId, "status": "deleted"}


@router.post(
    "/tenants/{tenantId}/graph/communities/detect",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=CommunityDetectResponse,
)
async def detect_graph_communities(
    tenantId: str, payload: CommunityDetectRequest
) -> CommunityDetectResponse:
    """Execute Leiden community detection and hierarchical summarization for a tenant."""
    from src.container import container
    from src.domain.graph.community_summarizer import CommunitySummarizer
    from src.domain.graph.leiden_detector import LeidenCommunityDetector

    triples = await container.graph_repository.get_all_triples(tenantId, limit=1000)
    detector = LeidenCommunityDetector(
        resolution=payload.resolution,
        min_community_size=payload.min_community_size,
    )
    hierarchy = detector.detect_communities(
        tenant_id=tenantId, triples=triples, max_levels=payload.max_levels
    )

    summarizer = CommunitySummarizer()
    dto_levels: dict[int, list[CommunitySummaryDTO]] = {}

    for lvl, comms in hierarchy.levels.items():
        dto_list = []
        for c in comms:
            if payload.generate_summaries and not c.summary:
                await summarizer.summarize_community(c)
            dto_list.append(
                CommunitySummaryDTO(
                    community_id=c.community_id,
                    level=c.level,
                    title=c.title,
                    entities=c.entities,
                    triple_count=len(c.triples),
                    weight=c.weight,
                    summary=c.summary,
                )
            )
        dto_levels[lvl] = dto_list

    return CommunityDetectResponse(
        tenant_id=tenantId,
        total_communities=hierarchy.total_communities,
        modularity_score=hierarchy.modularity_score,
        levels=dto_levels,
        metadata=hierarchy.metadata,
    )


@router.get(
    "/tenants/{tenantId}/graph/communities",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=CommunityDetectResponse,
)
async def get_graph_communities(tenantId: str) -> CommunityDetectResponse:
    """Fetch current hierarchical entity communities for a tenant."""
    return await detect_graph_communities(
        tenantId, CommunityDetectRequest(max_levels=3, generate_summaries=True)
    )


@router.post(
    "/tenants/{tenantId}/eval/self-tune",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=SelfTuningReportDTO,
)
async def trigger_self_tune(
    tenantId: str, payload: TriggerSelfTuneRequest
) -> SelfTuningReportDTO:
    """Analyze evaluation telemetry and dynamically compute/apply self-tuning parameter adjustments."""
    from src.container import container
    from src.domain.evaluation.online_evaluator import QualityMetrics
    from src.domain.evaluation.self_tuner import SelfTuningEngine

    tuner = SelfTuningEngine()
    config_service = container.configuration_service
    tenant_cfg = await config_service.get_tenant_config(tenantId)

    # Query live evaluation telemetry from online_eval_repo with resilient fallback
    metric_sample = QualityMetrics(
        context_precision=0.75,
        answer_relevance=0.85,
        faithfulness=0.80,
    )
    try:
        online_summary = await online_eval_repo.get_online_summary(tenantId)
        if online_summary and online_summary.get("total_evaluations", 0) > 0:
            metric_sample = QualityMetrics(
                context_precision=float(online_summary["avg_context_precision"]),
                answer_relevance=float(online_summary["avg_faithfulness"]),
                faithfulness=float(online_summary["avg_faithfulness"]),
            )
    except Exception:
        pass

    if payload.apply_changes:
        report = await tuner.tune_and_apply(tenantId, [metric_sample], config_service)
    else:
        current_settings = {
            "top_k": tenant_cfg.retrieval_settings.top_k,
            "reranking_threshold": tenant_cfg.retrieval_settings.reranking_threshold,
            "rrf_k": getattr(tenant_cfg.retrieval_settings, "rrf_k", 60),
            "enable_hybrid": tenant_cfg.feature_flags.enable_hybrid_search,
            "enable_reranking": tenant_cfg.feature_flags.enable_reranking,
            "enable_graph_search": tenant_cfg.feature_flags.enable_graph_rag,
        }
        report = tuner.calculate_tuning(tenantId, [metric_sample], current_settings)


    return SelfTuningReportDTO(
        tenant_id=report.tenant_id,
        status=report.status,
        current_settings=report.current_settings,
        recommended_settings=report.recommended_settings,
        adjustments=report.adjustments,
        average_faithfulness=report.average_faithfulness,
        average_precision=report.average_precision,
        hallucination_index=report.hallucination_index,
        confidence_score=report.confidence_score,
    )


@router.post(
    "/eval/nli",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=NliEvaluateResponse,
)
async def evaluate_nli_claims(payload: NliEvaluateRequest) -> NliEvaluateResponse:
    """Evaluate semantic Natural Language Inference (NLI) claim entailment against premises."""
    from src.domain.evaluation.nli_evaluator import NliEvaluator

    evaluator = NliEvaluator()
    res = evaluator.evaluate_claims(payload.claims, payload.contexts)

    return NliEvaluateResponse(
        total_claims=res.total_claims,
        entailed_claims=res.entailed_claims,
        contradicted_claims=res.contradicted_claims,
        neutral_claims=res.neutral_claims,
        faithfulness_score=res.faithfulness_score,
        hallucination_index=res.hallucination_index,
        classifications=[
            NliClassificationDTO(
                claim=c.claim,
                premise=c.premise,
                entailment_prob=c.entailment_prob,
                contradiction_prob=c.contradiction_prob,
                neutral_prob=c.neutral_prob,
                status=c.status,
            )
            for c in res.classifications
        ],
    )


@router.post(
    "/eval/slm-judge",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=SlmJudgeResponse,
)
async def evaluate_slm_judge(payload: SlmJudgeRequest) -> SlmJudgeResponse:
    """Run structured SLM-as-a-judge reasoning to verify answer grounding."""
    from src.domain.evaluation.slm_judge import SlmJudgeEngine

    judge = SlmJudgeEngine()
    result = await judge.judge_response(
        query=payload.query,
        answer=payload.answer,
        contexts=payload.contexts,
    )

    return SlmJudgeResponse(
        verdict=result.verdict,
        faithfulness_score=result.faithfulness_score,
        claim_analyses=[
            SlmClaimAnalysisDTO(
                claim=a.claim,
                status=a.status,
                evidence_span=a.evidence_span,
                confidence=a.confidence,
                rationale=a.rationale,
            )
            for a in result.claim_analyses
        ],
        reasoning=result.reasoning,
        latency_ms=result.latency_ms,
    )


@router.get(
    "/telemetry/trace-context",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_trace_context() -> dict[str, Any]:
    """Retrieve current distributed tracing configuration, active auto-instrumentations, and sample W3C traceparent."""
    from src.adapters.telemetry.auto_instrumentation import registry
    from src.adapters.telemetry.otel_tracer import OTelTracer

    return {
        "status": "active",
        "w3c_propagation_enabled": True,
        "active_trace_id": OTelTracer.get_current_trace_id(),
        "active_span_id": OTelTracer.get_current_span_id(),
        "traceparent_sample": OTelTracer.get_current_traceparent(),
        "auto_instrumentation": registry.get_status(),
    }


@router.get(
    "/tenants/{tenantId}/telemetry/live",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=TenantLiveTelemetryDTO,
)
async def get_live_tenant_telemetry(tenantId: str) -> TenantLiveTelemetryDTO:
    """Query live real-time multi-tenant database aggregations for usage, storage, cache, feedback, and SLA latencies."""
    from src.adapters.database.telemetry_repository import SqlTelemetryRepository
    from src.domain.telemetry.telemetry_service import LiveTelemetryService

    repo = SqlTelemetryRepository()
    service = LiveTelemetryService(repository=repo)
    telemetry = await service.get_live_telemetry(tenantId)

    return TenantLiveTelemetryDTO(
        tenant_id=telemetry.tenant_id,
        monthly_tokens_used=telemetry.monthly_tokens_used,
        documents_count=telemetry.documents_count,
        storage_bytes_used=telemetry.storage_bytes_used,
        cache_hits=telemetry.cache_hits,
        latency_saved_ms=telemetry.latency_saved_ms,
        cost_saved_usd=telemetry.cost_saved_usd,
        thumbs_up=telemetry.thumbs_up,
        thumbs_down=telemetry.thumbs_down,
        satisfaction_rate=telemetry.satisfaction_rate,
        avg_faithfulness=telemetry.avg_faithfulness,
        avg_precision=telemetry.avg_precision,
        hallucination_index=telemetry.hallucination_index,
        p99_latency_ms=telemetry.p99_latency_ms,
    )


@router.post(
    "/tenants/{tenantId}/alerts/test",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=TestAlertResponse,
)
async def dispatch_test_tenant_alert(tenantId: str, payload: TestAlertRequest) -> TestAlertResponse:
    """Send a test incident alert to verify webhook integration (Slack, Discord, Custom Webhook)."""
    from src.domain.telemetry.alert_service import AlertService

    alert_svc = AlertService()
    res = await alert_svc.dispatch_test_alert(
        tenant_id=tenantId,
        channel=payload.channel,
        webhook_url=payload.webhook_url,
    )

    return TestAlertResponse(
        status=res["status"],
        channel=res["channel"],
        webhook_url=res["webhook_url"],
        formatted_payload=res["formatted_payload"],
        timestamp=res["timestamp"],
    )


@router.get(
    "/tenants/{tenantId}/alerts/history",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=list[AlertHistoryItemDTO],
)
async def get_tenant_alert_history(tenantId: str) -> list[AlertHistoryItemDTO]:
    """Retrieve historical SLA incident alerts dispatched for a tenant."""
    from src.domain.telemetry.alert_service import AlertService

    alert_svc = AlertService()
    history = alert_svc.get_alert_history(tenant_id=tenantId)

    return [
        AlertHistoryItemDTO(
            alert_id=a.alert_id,
            tenant_id=a.tenant_id,
            rule_name=a.rule_name,
            severity=a.severity,
            title=a.title,
            description=a.description,
            metrics=a.metrics,
            timestamp=a.timestamp,
        )
        for a in history
    ]


@router.post(
    "/tenants/{tenantId}/datasets/synthesize",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
    response_model=SynthesizeDatasetResponse,
)
async def synthesize_golden_dataset(
    tenantId: str,
    payload: SynthesizeDatasetRequest,
) -> SynthesizeDatasetResponse:
    """Synthesize high-coverage golden benchmark Q&A pairs from document chunks."""
    from datetime import UTC, datetime

    from src.domain.evaluation.synthetic_generator import SyntheticDatasetGenerator

    generator = SyntheticDatasetGenerator()
    candidates = await generator.synthesize_from_chunks(
        chunks=payload.chunks, count_per_chunk=payload.count_per_chunk
    )
    dataset, questions = generator.format_dataset(tenantId, payload.name, candidates)

    try:
        await eval_dataset_repo.create_dataset(dataset)
        for q in questions:
            await eval_dataset_repo.add_question(q)
    except Exception:
        pass


    return SynthesizeDatasetResponse(
        dataset_id=dataset.dataset_id,
        tenant_id=dataset.tenant_id,
        name=dataset.name,
        question_count=len(questions),
        questions=[
            {
                "question_id": q.question_id,
                "question": q.question,
                "ground_truth_answer": q.ground_truth_answer,
                "relevant_chunk_ids": q.relevant_chunk_ids,
            }
            for q in questions
        ],
        created_at=dataset.created_at or datetime.now(UTC).isoformat(),
    )


@router.post(
    "/tenants/{tenantId}/eval/regression-gate",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=RegressionGateResponse,
)
async def run_regression_gate(
    tenantId: str,
    payload: RegressionGateRequest,
) -> RegressionGateResponse:
    """Evaluate cognitive accuracy scores against CI/CD regression gate thresholds."""
    from src.domain.abstractions.evaluation import (
        AggregateScores,
        DeepEvalScores,
        RagasScores,
        RegressionGateThresholds,
    )
    from src.domain.evaluation.regression_gate import RegressionGateEngine

    engine = RegressionGateEngine()
    agg_scores = AggregateScores(
        ragas=RagasScores(
            faithfulness=payload.faithfulness,
            context_precision=payload.context_precision,
            answer_relevancy=payload.answer_relevancy,
        ),
        deepeval=DeepEvalScores(
            hallucination=payload.hallucination,
        ),
    )

    thresh = RegressionGateThresholds(
        min_faithfulness=payload.thresholds.get("min_faithfulness", 0.90),
        min_context_precision=payload.thresholds.get("min_context_precision", 0.85),
        min_answer_relevancy=payload.thresholds.get("min_answer_relevancy", 0.85),
        max_hallucination=payload.thresholds.get("max_hallucination", 0.10),
    )

    report = engine.evaluate_gate(agg_scores, thresholds=thresh)

    return RegressionGateResponse(
        passed=report.passed,
        scores=report.scores,
        thresholds=report.thresholds,
        violations=report.violations,
        summary_markdown=report.summary_markdown,
        timestamp=report.timestamp,
    )


# ── M79 LoRA Domain Adapter & Embedding Calibration Endpoints ────────────────

class LoraTrainPair(BaseModel):
    query: str
    positive_chunk: str


class LoraTrainRequest(BaseModel):
    name: str = Field(default="Architecture Domain Adapter")
    domain_tag: str = Field(default="software_architecture")
    pairs: list[LoraTrainPair] = Field(default_factory=list)
    rank: int = Field(default=8, ge=2, le=64)
    epochs: int = Field(default=15, ge=1, le=100)
    learning_rate: float = Field(default=1e-3, ge=1e-5, le=1e-1)


class LoraAdapterDTO(BaseModel):
    adapter_id: str
    tenant_id: str
    name: str
    domain_tag: str
    rank: int
    loss_score: float | None = None
    created_at: str


class LoraTrainResponse(BaseModel):
    adapter_id: str
    tenant_id: str
    name: str
    rank: int
    loss_score: float
    message: str


@router.post(
    "/tenants/{tenantId}/lora/train",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=LoraTrainResponse,
)
async def train_lora_domain_adapter(
    tenantId: str,
    payload: LoraTrainRequest,
) -> LoraTrainResponse:
    """Train a Low-Rank Adaptation (LoRA) projection layer on domain contrastive pairs."""
    import uuid

    from sqlalchemy import text

    from src.adapters.database.connection import tenant_session
    from src.container import embedder
    from src.domain.embeddings.lora_adapter import (
        ContrastiveTrainer,
        LoraAdapterConfig,
        LoraEmbeddingAdapter,
    )

    pairs = payload.pairs
    # Defensive auto-fallback: if pairs empty, synthesize contrastive pairs from document chunks
    if not pairs:
        try:
            async with tenant_session(tenant_id=tenantId) as session:
                res = await session.execute(
                    text("SELECT content FROM document_chunks WHERE tenant_id = CAST(:tenant_id AS uuid) ORDER BY created_at DESC LIMIT 10"),
                    {"tenant_id": tenantId},
                )
                chunks = [row[0] for row in res.fetchall() if row[0] and len(row[0]) > 20]
                pairs = [
                    LoraTrainPair(
                        query=c[:80],
                        positive_chunk=c,
                    )
                    for c in chunks
                ]
        except Exception:
            pairs = []

    if len(pairs) < 2:
        # Create minimal synthetic pairs for domain calibration
        pairs = [
            LoraTrainPair(query="software architecture system design", positive_chunk="Modular scalable system architecture and microservices domain."),
            LoraTrainPair(query="commercial legal SOW escrow contracts", positive_chunk="Commercial milestone deliverables, payment escrow and legal agreement terms."),
        ]

    # Generate embeddings
    q_embeds: list[list[float]] = []
    p_embeds: list[list[float]] = []
    for p in pairs:
        qe = await embedder.embed_text(p.query)
        pe = await embedder.embed_text(p.positive_chunk)
        if qe and pe:
            q_embeds.append(qe)
            p_embeds.append(pe)

    dim = len(q_embeds[0]) if q_embeds else 768
    adapter = LoraEmbeddingAdapter(dim=dim, rank=payload.rank)
    trainer = ContrastiveTrainer(
        LoraAdapterConfig(
            dim=dim,
            rank=payload.rank,
            learning_rate=payload.learning_rate,
            epochs=payload.epochs,
        )
    )
    loss = trainer.train(q_embeds, p_embeds, adapter, epochs=payload.epochs, lr=payload.learning_rate)

    adapter_id = str(uuid.uuid4())
    weights_data = adapter.state_dict()

    async with tenant_session(tenant_id=tenantId) as session:
        import json
        await session.execute(
            text(
                """
                INSERT INTO tenant_lora_adapters (adapter_id, tenant_id, name, domain_tag, rank, loss_score, weights_json, created_at)
                VALUES (CAST(:aid AS uuid), CAST(:tid AS uuid), :name, :tag, :rank, :loss, CAST(:weights AS jsonb), NOW())
                """
            ),
            {
                "aid": adapter_id,
                "tid": tenantId,
                "name": payload.name,
                "tag": payload.domain_tag,
                "rank": payload.rank,
                "loss": loss,
                "weights": json.dumps(weights_data),
            },
        )
        await session.commit()

    return LoraTrainResponse(
        adapter_id=adapter_id,
        tenant_id=tenantId,
        name=payload.name,
        rank=payload.rank,
        loss_score=round(loss, 4),
        message="LoRA domain adapter trained and persisted successfully.",
    )


@router.get(
    "/tenants/{tenantId}/lora/adapters",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
    response_model=list[LoraAdapterDTO],
)
async def list_lora_adapters(tenantId: str) -> list[LoraAdapterDTO]:
    """List all trained LoRA embedding adapters for the tenant."""
    from sqlalchemy import text

    from src.adapters.database.connection import tenant_session

    async with tenant_session(tenant_id=tenantId) as session:
        res = await session.execute(
            text(
                """
                SELECT adapter_id, tenant_id, name, domain_tag, rank, loss_score, created_at
                FROM tenant_lora_adapters
                WHERE tenant_id = CAST(:tid AS uuid)
                ORDER BY created_at DESC
                """
            ),
            {"tid": tenantId},
        )
        rows = res.fetchall()

    return [
        LoraAdapterDTO(
            adapter_id=str(r[0]),
            tenant_id=str(r[1]),
            name=r[2],
            domain_tag=r[3],
            rank=r[4],
            loss_score=r[5],
            created_at=r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6]),
        )
        for r in rows
    ]


@router.post(
    "/tenants/{tenantId}/lora/adapters/{adapterId}/activate",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def activate_lora_adapter(tenantId: str, adapterId: str) -> dict[str, str]:
    """Activate a trained LoRA adapter in the tenant configuration."""
    from sqlalchemy import text

    from src.adapters.database.connection import tenant_session

    async with tenant_session(tenant_id=tenantId) as session:
        await session.execute(
            text(
                """
                UPDATE tenant_configs
                SET active_lora_adapter = :aid
                WHERE tenant_id = CAST(:tid AS uuid)
                """
            ),
            {"aid": adapterId, "tid": tenantId},
        )
        await session.commit()

    return {"status": "success", "message": f"Adapter {adapterId} activated for tenant {tenantId}."}


# ── Milestone 83: Telemetry Anomaly Sentinel & Abuse Guard ──────────────────


@router.get(
    "/telemetry/anomalies",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def list_telemetry_anomalies(
    tenant_id: str | None = Query(None, description="Filter by tenant UUID"),
    risk_level: str | None = Query(None, description="Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)"),
    status: str | None = Query(None, description="Filter by status (active, resolved)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List detected telemetry anomalies across all tenants with filtering."""
    from src.container import anomaly_sentinel_service

    items, total = await anomaly_sentinel_service.list_anomalies(
        tenant_id=tenant_id,
        risk_level=risk_level,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "items": items,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/telemetry/anomalies/scan",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def trigger_anomaly_scan(
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trigger an on-demand telemetry anomaly scan across inference logs."""
    from src.container import anomaly_sentinel_service

    req = request or {}
    lookback = int(req.get("lookback_minutes", 60))
    tenant_id = req.get("tenant_id")
    auto_quarantine = bool(req.get("auto_quarantine", True))

    scores = await anomaly_sentinel_service.scan_telemetry(
        lookback_minutes=lookback,
        tenant_id=tenant_id,
        auto_quarantine=auto_quarantine,
    )

    anomalies = [s for s in scores if s.is_anomaly]
    quarantined = [s for s in anomalies if s.risk_level == "CRITICAL" and s.entity_type == "api_key"]

    return {
        "status": "completed",
        "total_evaluated": len(scores),
        "anomalies_detected": len(anomalies),
        "quarantined_count": len(quarantined),
        "scores": [s.model_dump(mode="json") for s in scores],
    }


@router.post(
    "/telemetry/anomalies/{anomaly_id}/resolve",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def resolve_telemetry_anomaly(
    anomaly_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve or dismiss a flagged security anomaly."""
    from src.container import anomaly_sentinel_service

    notes = (body or {}).get("notes", "Resolved by administrator")
    success = await anomaly_sentinel_service.resolve_anomaly(
        anomaly_id=anomaly_id,
        resolved_by="admin",
        notes=notes,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found or update failed.",
        )
    return {"status": "success", "anomaly_id": anomaly_id, "resolved": True}


@router.post(
    "/api-keys/{key_id}/quarantine",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def quarantine_api_key(
    key_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Manually quarantine an API key to suspend access immediately."""
    from src.container import anomaly_sentinel_service

    tenant_id = body.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_id is required.",
        )
    reason = body.get("reason", "Manual administrator quarantine")
    level = body.get("level", "CRITICAL")

    success = await anomaly_sentinel_service.quarantine_key(
        key_id=key_id,
        tenant_id=tenant_id,
        reason=reason,
        level=level,
    )
    return {"status": "success", "key_id": key_id, "quarantined": success}


@router.post(
    "/api-keys/{key_id}/unquarantine",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def unquarantine_api_key(
    key_id: str,
) -> dict[str, Any]:
    """Restore a quarantined API key to active status."""
    from src.container import anomaly_sentinel_service

    success = await anomaly_sentinel_service.unquarantine_key(
        key_id=key_id,
        resolved_by="admin",
    )
    return {"status": "success", "key_id": key_id, "active": success}


# ---------------------------------------------------------------------------
# Milestone 89: Geo-Distributed Multi-Region Edge Vector Read-Replicas
# ---------------------------------------------------------------------------

@router.get(
    "/platform/regions",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_cluster_regions() -> MultiRegionClusterStatus:
    """Retrieve global edge routing cluster topology, active regions, and health."""
    from src.container import edge_router_service
    return edge_router_service.get_cluster_status()


@router.post(
    "/platform/regions/probe",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def probe_cluster_regions() -> RegionProbeResponse:
    """Trigger an active RTT latency probe across all configured regional endpoints."""
    from src.container import read_replica_adapter
    return await read_replica_adapter.probe_regional_health()


@router.get(
    "/platform/regions/preview",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def preview_edge_routing(
    country: str = Query("US", description="ISO-3166 alpha-2 country code to simulate"),
) -> EdgeRoutingDecision:
    """Preview the Geo-IP dynamic routing decision and estimated latency reduction."""
    from src.container import edge_router_service
    return edge_router_service.resolve_region(country)
