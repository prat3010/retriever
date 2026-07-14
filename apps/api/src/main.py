import hashlib
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Security,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text

from src.adapters.api.security import (
    get_current_user_id,
    verify_admin_key,
    verify_scopes,
    verify_tenant_isolation,
)
from src.adapters.broker.celery_publisher import celery_app
from src.adapters.cache.config_cache import RedisTenantConfigCache, redis_client
from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.adapters.cognitive.reranker_adapter import CohereRerankerAdapter
from src.adapters.database.audit_repository import SqlAuditLogRepository
from src.adapters.database.config_repository import SqlConfigRegistry
from src.adapters.database.connection import engine, tenant_session
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.database.inference_repository import (
    SqlChatSessionRepository,
    SqlInferenceLogWriter,
    SqlPromptTemplateRegistry,
)
from src.adapters.database.models import DocumentChunkDb, DocumentDb
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.adapters.database.user_repository import SqlUserRepository
from src.adapters.storage.local_storage import LocalStorage
from src.adapters.telemetry.rate_limiter_dep import rate_limit
from src.adapters.telemetry.setup import init_telemetry
from src.adapters.vector.keyword_repository import PgKeywordSearchAdapter
from src.adapters.vector.vector_repository import PgVectorSearchAdapter
from src.config import settings
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.exceptions import (
    AuthenticationError,
    PromptTemplateNotFoundError,
    TenantIsolationViolationError,
)
from src.domain.abstractions.inference import PromptTemplate
from src.domain.abstractions.retrieval import SearchQuery
from src.domain.abstractions.tenant import Tenant
from src.domain.config.config_service import ConfigurationService
from src.domain.inference.citation_validator import CitationValidator
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.inference.prompt_builder import PromptBuilder
from src.domain.retrieval.search_service import HybridSearchService


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.opentelemetry import OpenTelemetryIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(),
                OpenTelemetryIntegration(),
            ],
        )
    yield
    # Flush pending telemetry on shutdown
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.flush()
    try:
        from src.adapters.telemetry.setup import get_tracer
        tracer = get_tracer()
        if tracer:
            tracer.force_flush()
    except Exception:
        pass


app = FastAPI(
    title="Retriever Core Platform",
    description="Headless Multi-Tenant AI Knowledge Platform Memory Layer API",
    version="0.1.0",
    lifespan=lifespan,
)

# Initialise telemetry subsystems at import time
init_telemetry(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
audit_logger = SqlAuditLogRepository()
tenant_registry = SqlTenantRegistry()
identity_provider = SqlIdentityProvider()
user_repository = SqlUserRepository()
config_service = ConfigurationService(
    registry=SqlConfigRegistry(),
    cache=RedisTenantConfigCache(),
    env_secrets=dict(os.environ),
)
local_storage = LocalStorage()

# Initialize search service
search_service = HybridSearchService(
    vector_search=PgVectorSearchAdapter(),
    keyword_search=PgKeywordSearchAdapter(),
    embedder=OpenAIEmbeddingAdapter(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    ),
    reranker=CohereRerankerAdapter(api_key=settings.COHERE_API_KEY),
)

# Initialize inference service
session_repo = SqlChatSessionRepository()
template_registry = SqlPromptTemplateRegistry()
log_writer = SqlInferenceLogWriter()

inference_orchestrator = InferenceOrchestrator(
    llm_provider=OpenAILLMAdapter(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    ),
    prompt_builder=PromptBuilder(template_registry=template_registry),
    citation_validator=CitationValidator(),
    session_repo=session_repo,
    log_writer=log_writer,
)

# Exception Handlers mapping to HTTP Responses
@app.exception_handler(TenantIsolationViolationError)
async def handle_isolation_violation(request, exc):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=str(exc),
    )

@app.exception_handler(AuthenticationError)
async def handle_auth_error(request, exc):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=str(exc),
    )


# --- Request/Response DTOs ---

class HealthResponse(BaseModel):
    status: str
    environment: str


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    tier: str = Field(default="standard")
    isolation_level: str = Field(default="logical")

class CreatePromptRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(...)
    is_system_prompt: bool = False

class PreviewPromptRequest(BaseModel):
    name: str = "default"
    query: str = Field(default="What is the capital of France?")
    context: str | None = None


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="client", pattern="^(admin|client)$")
    expires_in_days: int | None = Field(default=None, ge=1)


class ApiKeyCreatedResponse(BaseModel):
    apiKey: str
    keyId: str
    tenantId: str
    prefix: str
    role: str
    status: str
    expiresAt: str | None = None


class CreateUserRequest(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class UserResponse(BaseModel):
    userId: str
    tenantId: str
    externalId: str
    displayName: str | None
    isActive: bool
    createdAt: str


class TenantListItem(BaseModel):
    tenantId: str
    name: str
    status: str
    tier: str
    createdAt: str


class PaginatedTenantList(BaseModel):
    items: list[TenantListItem]
    total: int


class DocumentResponse(BaseModel):
    documentId: str
    filename: str
    fileSize: int
    mimeType: str
    status: str
    createdAt: str
    updatedAt: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResultItem(BaseModel):
    chunkId: str
    documentId: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchMetaResponse(BaseModel):
    strategy: str
    totalCandidates: int
    returnedResults: int
    durationMs: float


class SearchResponseDto(BaseModel):
    query: str
    results: list[SearchResultItem]
    searchMeta: SearchMetaResponse


# --- API Routes ---

@app.get("/health/liveness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def liveness_probe() -> HealthResponse:
    """Liveness probe to confirm the API server process is running."""
    return HealthResponse(status="alive", environment=settings.ENVIRONMENT)


@app.get("/health/readiness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def readiness_probe() -> HealthResponse:
    """Readiness probe to confirm database and cache infrastructure connection endpoints are alive."""
    try:
        # Stateful query check on Postgres engine pool
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Stateful ping check on Redis cluster connection pool
        await redis_client.ping()

        return HealthResponse(status="ready", environment=settings.ENVIRONMENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {e!s}",
        ) from e


@app.post(
    "/v1/tenants",
    status_code=status.HTTP_201_CREATED,
    response_model=Tenant,
    dependencies=[Depends(verify_admin_key)],
)
async def create_tenant(
    payload: CreateTenantRequest,
) -> Tenant:
    """Register a new tenant workspace bounds (System-wide Admin)."""
    tenant = await tenant_registry.create_tenant(
        name=payload.name,
        tier=payload.tier,
        isolation_level=payload.isolation_level,
    )
    await audit_logger.write(tenant.tenant_id, "tenant.created", f"Tenant '{payload.name}' created")
    return tenant


@app.put(
    "/v1/config/global",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def update_global_config(
    payload: TenantConfiguration,
) -> dict[str, str]:
    """Update global system-wide configurations (Admin only)."""
    await config_service.update_global_config(payload)
    await audit_logger.write("global", "config.updated", "Global configuration updated")
    return {"status": "updated", "scope": "global"}


@app.get(
    "/v1/config/global",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_admin_key)],
)
async def get_global_config() -> TenantConfiguration:
    """Get global configurations with secrets redacted (Admin only)."""
    config = await config_service.get_global_config()
    return config.redact_secrets()


@app.put(
    "/v1/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def update_tenant_config(
    tenantId: str,
    payload: TenantConfiguration,
) -> dict[str, str]:
    """Update / override configuration settings for the tenant workspace."""
    await config_service.update_tenant_config(tenantId, payload)
    return {"tenantId": tenantId, "status": "updated"}


@app.get(
    "/v1/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_tenant_config(tenantId: str) -> TenantConfiguration:
    """Get configuration settings for the tenant workspace (secrets redacted)."""
    config = await config_service.get_tenant_config(tenantId)
    return config.redact_secrets()


@app.post(
    "/v1/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatedResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def generate_api_key(
    tenantId: str,
    payload: CreateApiKeyRequest,
) -> ApiKeyCreatedResponse:
    """Generate a new Bearer API credential token for the tenant."""
    raw_key, metadata = await identity_provider.create_api_key(
        tenant_id=tenantId,
        name=payload.name,
        expires_in_days=payload.expires_in_days,
        role=payload.role,
    )
    return ApiKeyCreatedResponse(
        apiKey=raw_key,
        keyId=metadata.key_id,
        tenantId=metadata.tenant_id,
        prefix=metadata.prefix,
        role=metadata.role,
        status=metadata.status,
        expiresAt=metadata.expires_at,
    )


# --- Admin API Endpoints ---


@app.get(
    "/v1/admin/tenants",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTenantList,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_tenants(
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedTenantList:
    """List all tenants with optional search and pagination (System-wide Admin)."""
    tenants, total = await tenant_registry.list_tenants(search=search, limit=limit, offset=offset)
    return PaginatedTenantList(
        items=[
            TenantListItem(
                tenantId=str(t.tenant_id),
                name=t.name,
                status=t.status,
                tier=t.tier,
                createdAt=t.created_at,
            )
            for t in tenants
        ],
        total=total,
    )


@app.get(
    "/v1/admin/tenants/{tenantId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_tenant(tenantId: str) -> dict:
    """Get tenant details (System-wide Admin)."""
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


@app.delete(
    "/v1/admin/tenants/{tenantId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_deactivate_tenant(tenantId: str) -> dict[str, str]:
    """Deactivate a tenant (System-wide Admin)."""
    found = await tenant_registry.deactivate_tenant(tenantId)
    if not found:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    await audit_logger.write(tenantId, "tenant.deactivated", "Tenant deactivated")
    return {"status": "deactivated", "tenantId": tenantId}


@app.get(
    "/v1/admin/tenants/{tenantId}/users",
    status_code=status.HTTP_200_OK,
    response_model=list[UserResponse],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_users(tenantId: str) -> list[UserResponse]:
    """List users in a tenant (System-wide Admin)."""
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


@app.post(
    "/v1/admin/tenants/{tenantId}/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_user(tenantId: str, payload: CreateUserRequest) -> UserResponse:
    """Create a user in a tenant (System-wide Admin)."""
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


@app.get(
    "/v1/admin/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_api_keys(tenantId: str) -> list[dict]:
    """List API keys for a tenant (System-wide Admin)."""
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


@app.post(
    "/v1/admin/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_api_key(tenantId: str, payload: CreateApiKeyRequest) -> dict:
    """Create an API key for a tenant with role (System-wide Admin)."""
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


@app.delete(
    "/v1/admin/tenants/{tenantId}/api-keys/{keyId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_revoke_api_key(tenantId: str, keyId: str) -> dict[str, str]:
    """Revoke an API key for a tenant (System-wide Admin)."""
    found = await identity_provider.revoke_api_key(tenantId, keyId)
    if not found:
        raise HTTPException(status_code=404, detail="API key not found.")
    await audit_logger.write(tenantId, "api_key.revoked", f"API key '{keyId}' revoked")
    return {"status": "revoked", "keyId": keyId}


@app.get(
    "/v1/admin/tenants/{tenantId}/documents",
    status_code=status.HTTP_200_OK,
    response_model=list[DocumentResponse],
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_documents(tenantId: str) -> list[DocumentResponse]:
    """List all documents for a tenant (System-wide Admin)."""
    async with tenant_session(bypass_rls=True) as session:
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == uuid.UUID(tenantId),
            DocumentDb.is_deleted == False
        ).order_by(DocumentDb.created_at.desc())
        res = await session.execute(stmt)
        docs = res.scalars().all()
        return [
            DocumentResponse(
                documentId=str(d.document_id),
                filename=d.filename,
                fileSize=d.file_size,
                mimeType=d.mime_type,
                status=d.status,
                createdAt=d.created_at.isoformat(),
                updatedAt=d.updated_at.isoformat()
            )
            for d in docs
        ]


@app.get(
    "/v1/admin/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_tenant_config(tenantId: str) -> TenantConfiguration:
    """Get tenant configuration with secrets (System-wide Admin)."""
    return await config_service.get_tenant_config(tenantId)


@app.put(
    "/v1/admin/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_tenant_config(tenantId: str, payload: TenantConfiguration) -> dict[str, str]:
    """Update tenant configuration (System-wide Admin)."""
    await config_service.update_tenant_config(tenantId, payload)
    await audit_logger.write(tenantId, "config.updated", "Tenant configuration updated")
    return {"tenantId": tenantId, "status": "updated"}


@app.get(
    "/v1/admin/audit-logs",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_audit_logs(
    tenantId: str | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List audit log entries with optional filters (System-wide Admin)."""
    items, total = await audit_logger.list(
        tenant_id=tenantId, action=action, limit=limit, offset=offset,
    )
    return {"items": items, "total": total}


@app.get(
    "/v1/admin/tenants/{tenantId}/prompts",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_list_prompts(tenantId: str) -> list[dict]:
    """List all prompt templates for a tenant (System-wide Admin)."""
    templates = await template_registry.list_templates(tenantId, bypass_rls=True)
    return [
        {
            "name": t.name,
            "content": t.content,
            "isSystemPrompt": t.is_system_prompt,
        }
        for t in templates
    ]


@app.post(
    "/v1/admin/tenants/{tenantId}/prompts",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_create_prompt(tenantId: str, payload: CreatePromptRequest) -> dict:
    """Create a new prompt template for a tenant (System-wide Admin)."""
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


@app.get(
    "/v1/admin/tenants/{tenantId}/prompts/{name}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_get_prompt(tenantId: str, name: str) -> dict:
    """Get a named prompt template for a tenant (System-wide Admin)."""
    template = await template_registry.get_template(tenantId, name, bypass_rls=True)
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return {
        "name": template.name,
        "content": template.content,
        "isSystemPrompt": template.is_system_prompt,
    }


@app.put(
    "/v1/admin/tenants/{tenantId}/prompts/{name}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_update_prompt(tenantId: str, name: str, payload: CreatePromptRequest) -> dict:
    """Update a named prompt template (System-wide Admin)."""
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


@app.delete(
    "/v1/admin/tenants/{tenantId}/prompts/{name}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_delete_prompt(tenantId: str, name: str) -> dict[str, str]:
    """Delete a named prompt template (System-wide Admin)."""
    found = await template_registry.delete_template(tenantId, name, bypass_rls=True)
    if not found:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return {"name": name, "status": "deleted"}


@app.post(
    "/v1/admin/tenants/{tenantId}/prompts/preview",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def admin_preview_prompt(tenantId: str, payload: PreviewPromptRequest) -> dict:
    """Preview a rendered prompt template (no LLM call)."""
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


# --- Document Ingestion & Storage Endpoints ---

@app.post(
    "/v1/tenants/{tenantId}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"]), Depends(rate_limit(scope="ingest", max_requests=20))],
)
async def upload_document(
    tenantId: str,
    file: UploadFile = File(...),
) -> dict:
    """Upload and schedule document text chunking extraction pipeline."""
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # 1. Deduplication: Check for active duplicates within the same tenant workspace
    async with tenant_session(tenant_id=tenantId) as session:
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == uuid.UUID(tenantId),
            DocumentDb.file_hash == file_hash,
            DocumentDb.is_deleted == False
        )
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return {
                "documentId": str(existing.document_id),
                "status": "pending",
                "fileHash": file_hash,
                "createdAt": existing.created_at.isoformat(),
            }

    # 2. Save file to isolated tenant folder
    storage_path = await local_storage.save_file(tenantId, file.filename, content)

    # 3. Create document database entry
    import datetime
    now = datetime.datetime.now(datetime.UTC)
    doc_id = uuid.uuid4()
    async with tenant_session(tenant_id=tenantId) as session:
        db_doc = DocumentDb(
            document_id=doc_id,
            tenant_id=uuid.UUID(tenantId),
            filename=file.filename,
            file_hash=file_hash,
            storage_path=storage_path,
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            status="PENDING",
            created_at=now,
            updated_at=now
        )
        session.add(db_doc)
        await session.commit()
        created_str = db_doc.created_at.isoformat()

    # 4. Submit to Celery worker for parsing and embedding
    celery_app.send_task(
        "process_document",
        args=[str(doc_id), tenantId, storage_path],
        queue="ingestion.parse",
    )

    return {
        "documentId": str(doc_id),
        "status": "pending",
        "fileHash": file_hash,
        "createdAt": created_str,
    }


@app.get(
    "/v1/tenants/{tenantId}/documents",
    status_code=status.HTTP_200_OK,
    response_model=list[DocumentResponse],
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def list_documents(tenantId: str) -> list[DocumentResponse]:
    """List all ingestion records belonging to the tenant."""
    async with tenant_session(tenant_id=tenantId) as session:
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == uuid.UUID(tenantId),
            DocumentDb.is_deleted == False
        )
        res = await session.execute(stmt)
        docs = res.scalars().all()

        return [
            DocumentResponse(
                documentId=str(d.document_id),
                filename=d.filename,
                fileSize=d.file_size,
                mimeType=d.mime_type,
                status=d.status,
                createdAt=d.created_at.isoformat(),
                updatedAt=d.updated_at.isoformat()
            )
            for d in docs
        ]


@app.get(
    "/v1/tenants/{tenantId}/documents/{documentId}",
    status_code=status.HTTP_200_OK,
    response_model=DocumentResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_document(tenantId: str, documentId: str) -> DocumentResponse:
    """Retrieve document metadata processing pipeline status."""
    async with tenant_session(tenant_id=tenantId) as session:
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == uuid.UUID(tenantId),
            DocumentDb.document_id == uuid.UUID(documentId),
            DocumentDb.is_deleted == False
        )
        res = await session.execute(stmt)
        d = res.scalar_one_or_none()
        if not d:
            raise HTTPException(status_code=404, detail="Document not found.")

        return DocumentResponse(
            documentId=str(d.document_id),
            filename=d.filename,
            fileSize=d.file_size,
            mimeType=d.mime_type,
            status=d.status,
            createdAt=d.created_at.isoformat(),
            updatedAt=d.updated_at.isoformat()
        )


@app.delete(
    "/v1/tenants/{tenantId}/documents/{documentId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def delete_document(tenantId: str, documentId: str) -> dict[str, str]:
    """Delete document source file, cascade chunks, and mark records deleted."""
    async with tenant_session(tenant_id=tenantId) as session:
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == uuid.UUID(tenantId),
            DocumentDb.document_id == uuid.UUID(documentId),
            DocumentDb.is_deleted == False
        )
        res = await session.execute(stmt)
        d = res.scalar_one_or_none()
        if not d:
            raise HTTPException(status_code=404, detail="Document not found.")

        # 1. Soft delete / update is_deleted flag in db
        d.is_deleted = True

        # 2. Delete raw storage file
        await local_storage.delete_file(d.storage_path)

        # 3. Hard delete associated chunks from document_chunks table
        await session.execute(
            delete(DocumentChunkDb).where(DocumentChunkDb.document_id == uuid.UUID(documentId))
        )

        await session.commit()
        return {"status": "deleted", "documentId": documentId}


# --- Search & Retrieval Endpoints ---

@app.post(
    "/v1/tenants/{tenantId}/search",
    status_code=status.HTTP_200_OK,
    response_model=SearchResponseDto,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"]), Depends(rate_limit(scope="search", max_requests=120))],
)
async def search_documents(
    tenantId: str,
    payload: SearchRequest,
) -> SearchResponseDto:
    """Execute hybrid search across tenant document vectors and keyword indexes."""
    # Resolve tenant configuration for feature flags and retrieval settings
    tenant_config = await config_service.get_tenant_config(tenantId)

    query = SearchQuery(
        query=payload.query,
        tenant_id=tenantId,
        top_k=payload.limit,
        filters=payload.filters,
        enable_hybrid=tenant_config.feature_flags.enable_hybrid_search,
        enable_reranking=tenant_config.feature_flags.enable_reranking,
        rrf_k=tenant_config.retrieval_settings.rrf_k,
        reranking_threshold=tenant_config.retrieval_settings.reranking_threshold,
    )

    response = await search_service.search(query)

    return SearchResponseDto(
        query=response.query,
        results=[
            SearchResultItem(
                chunkId=r.chunk_id,
                documentId=r.document_id,
                content=r.content,
                score=r.score,
                metadata=r.metadata,
            )
            for r in response.results
        ],
        searchMeta=SearchMetaResponse(
            strategy=response.search_meta.strategy,
            totalCandidates=response.search_meta.total_candidates,
            returnedResults=response.search_meta.returned_results,
            durationMs=response.search_meta.duration_ms,
        ),
    )


# --- Chat & Inference Endpoints ---


class CreateSessionResponse(BaseModel):
    sessionId: str
    createdAt: str


class ChatMessageRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    stream: bool = True


@app.post(
    "/v1/tenants/{tenantId}/chat/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateSessionResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"]), Depends(rate_limit(scope="chat", max_requests=30))],
)
async def create_chat_session(
    tenantId: str,
    user_id: str | None = Depends(get_current_user_id),
) -> CreateSessionResponse:
    """Create a new chat session for grounded inference."""
    session = await inference_orchestrator.create_session(tenantId, user_id)
    return CreateSessionResponse(
        sessionId=session.session_id,
        createdAt=session.created_at,
    )


@app.post(
    "/v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"]), Depends(rate_limit(scope="chat", max_requests=30))],
)
async def send_chat_message(
    tenantId: str,
    sessionId: str,
    payload: ChatMessageRequest,
    user_id: str | None = Depends(get_current_user_id),
    x_llm_key: str | None = Header(None, alias="X-LLM-Key"),
):
    """Send a message to a chat session and get a grounded inference response.

    When ``stream=true`` (default), returns a Server-Sent Events stream.
    When ``stream=false``, returns a JSON response.
    """
    # Verify session belongs to tenant
    session = await inference_orchestrator.get_session(sessionId, tenantId)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Retrieve tenant config for inference parameters
    tenant_config = await config_service.get_tenant_config(tenantId)

    # Override LLM API key if X-LLM-Key header is provided
    if x_llm_key:
        tenant_config.ai_provider.api_key = x_llm_key

    # Execute hybrid search for grounding context
    search_query = SearchQuery(
        query=payload.query,
        tenant_id=tenantId,
        top_k=tenant_config.retrieval_settings.top_k,
        enable_hybrid=tenant_config.feature_flags.enable_hybrid_search,
        enable_reranking=tenant_config.feature_flags.enable_reranking,
        rrf_k=tenant_config.retrieval_settings.rrf_k,
        reranking_threshold=tenant_config.retrieval_settings.reranking_threshold,
    )
    search_response = await search_service.search(search_query)

    if not payload.stream:
        response = await inference_orchestrator.generate(
            tenant_id=tenantId,
            session_id=sessionId,
            query=payload.query,
            context_chunks=search_response.results,
            tenant_config=tenant_config,
            user_id=user_id,
        )
        return {
            "content": response.content,
            "usage": response.usage.model_dump(),
            "finish_reason": response.finish_reason,
        }

    # Streaming response via SSE
    from fastapi.responses import StreamingResponse

    async def event_stream():
        async for event in inference_orchestrator.generate_stream(
            tenant_id=tenantId,
            session_id=sessionId,
            query=payload.query,
            context_chunks=search_response.results,
            tenant_config=tenant_config,
            user_id=user_id,
        ):
            import json
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Retriever Core Platform API. Visit /docs for Swagger UI."}


