"""Admin API routes."""
import hashlib
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from src.adapters.api.security import verify_admin_key
from src.config import settings
from src.container import (
    admin_repository,
    audit_logger,
    celery_app,
    config_service,
    document_repository,
    eval_dataset_repo,
    eval_run_repo,
    eval_service,
    feedback_repo,
    identity_provider,
    inference_orchestrator,
    ingest_file_sync,
    local_storage,
    search_service,
    template_registry,
    tenant_registry,
    user_repository,
)
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.exceptions import PromptTemplateNotFoundError
from src.domain.abstractions.inference import PromptTemplate
from src.domain.abstractions.ingestion import Document
from src.schemas.admin import (
    ApplyPresetRequest,
    CreateApiKeyRequest,
    CreatePromptRequest,
    CreateUserRequest,
    PreviewPromptRequest,
    UserResponse,
)
from src.schemas.document import DocumentResponse
from src.schemas.evaluation import (
    AddEvalQuestionRequest,
    BulkImportQuestionsRequest,
    CreateEvalDatasetRequest,
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
async def admin_process_document(tenantId: str, documentId: str) -> dict:
    doc = await document_repository.get_document(tenantId, documentId)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_content = await local_storage.read_file(doc.storage_path)
    if file_content is None:
        raise HTTPException(status_code=404, detail="Document file not found on disk.")

    chunk_count = await ingest_file_sync(
        tenant_id=tenantId,
        document_id=documentId,
        filename=doc.filename,
        file_content=file_content,
        file_hash=doc.file_hash,
        mime_type=doc.mime_type,
        embedder=search_service.embedder,
    )

    return {
        "documentId": documentId,
        "status": "indexed",
        "chunksIndexed": chunk_count,
    }


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
    doc = await document_repository.get_document(documentId, bypass_rls=True)
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
    doc = await document_repository.get_document(documentId, bypass_rls=True)
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
