from typing import Optional
import uuid
import hashlib
from fastapi import FastAPI, status, HTTPException, Header, Depends, Security, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text, select, delete
from celery import Celery

from src.config import settings
from src.domain.abstractions.exceptions import TenantIsolationViolationError, AuthenticationError
from src.domain.abstractions.tenant import Tenant
from src.domain.abstractions.config import TenantConfiguration
from src.adapters.api.security import verify_tenant_isolation, verify_admin_key, verify_scopes
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.domain.config.config_service import ConfigurationService
from src.adapters.database.connection import engine, tenant_session
from src.adapters.cache.config_cache import redis_client
from src.adapters.storage.local_storage import LocalStorage
from src.adapters.database.models import DocumentDb, DocumentChunkDb

app = FastAPI(
    title="Retriever Core Platform",
    description="Headless Multi-Tenant AI Knowledge Platform Memory Layer API",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
tenant_registry = SqlTenantRegistry()
identity_provider = SqlIdentityProvider()
config_service = ConfigurationService()
local_storage = LocalStorage()
celery_client = Celery("retriever-workers", broker=settings.RABBITMQ_URL)

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


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    expires_in_days: Optional[int] = Field(default=None, ge=1)


class ApiKeyCreatedResponse(BaseModel):
    apiKey: str
    keyId: str
    tenantId: str
    prefix: str
    status: str
    expiresAt: Optional[str] = None


class DocumentResponse(BaseModel):
    documentId: str
    filename: str
    fileSize: int
    mimeType: str
    status: str
    createdAt: str
    updatedAt: str


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
            detail=f"Readiness check failed: {str(e)}",
        )


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
    return await tenant_registry.create_tenant(
        name=payload.name,
        tier=payload.tier,
        isolation_level=payload.isolation_level,
    )


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
    )
    return ApiKeyCreatedResponse(
        apiKey=raw_key,
        keyId=metadata.key_id,
        tenantId=metadata.tenant_id,
        prefix=metadata.prefix,
        status=metadata.status,
        expiresAt=metadata.expires_at,
    )


# --- Document Ingestion & Storage Endpoints ---

@app.post(
    "/v1/tenants/{tenantId}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def upload_document(
    tenantId: str,
    file: UploadFile = File(...),
) -> DocumentResponse:
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
            return DocumentResponse(
                documentId=str(existing.document_id),
                filename=existing.filename,
                fileSize=existing.file_size,
                mimeType=existing.mime_type,
                status=existing.status,
                createdAt=existing.created_at.isoformat(),
                updatedAt=existing.updated_at.isoformat()
            )

    # 2. Save file to isolated tenant folder
    storage_path = await local_storage.save_file(tenantId, file.filename, content)

    # 3. Create document database entry
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
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
            status="uploaded",
            created_at=now,
            updated_at=now
        )
        session.add(db_doc)
        await session.commit()
        await session.refresh(db_doc)
        created_str = db_doc.created_at.isoformat()
        updated_str = db_doc.updated_at.isoformat()

    # 4. Dispatch async processing celery task
    celery_client.send_task("tasks.parse_document", args=[str(doc_id), tenantId, storage_path])

    return DocumentResponse(
        documentId=str(doc_id),
        filename=file.filename,
        fileSize=len(content),
        mimeType=file.content_type or "application/octet-stream",
        status="uploaded",
        createdAt=created_str,
        updatedAt=updated_str
    )


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


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Retriever Core Platform API. Visit /docs for Swagger UI."}


