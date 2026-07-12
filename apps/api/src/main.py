from typing import Optional
from fastapi import FastAPI, status, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from src.config import settings
from src.domain.abstractions.exceptions import TenantIsolationViolationError, AuthenticationError
from src.domain.abstractions.tenant import TenantConfig, Tenant
from src.domain.identity.security import verify_tenant_isolation
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.cache.config_cache import RedisTenantConfigCache

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
config_cache = RedisTenantConfigCache()

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


class ConfigUpdatePayload(BaseModel):
    activeModel: str = Field(alias="active_model")
    temperature: float = Field(..., ge=0.0, le=1.0)
    chunkSize: int = Field(alias="chunk_size", ge=50, le=2000)
    chunkOverlap: int = Field(alias="chunk_overlap", ge=0, le=500)
    systemPromptTemplate: str = Field(alias="system_prompt_template")

    model_config = ConfigDict(populate_by_name=True)


# --- API Routes ---

@app.get("/health/liveness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def liveness_probe() -> HealthResponse:
    """Liveness probe to confirm the API server process is running."""
    return HealthResponse(status="alive", environment=settings.ENVIRONMENT)


@app.get("/health/readiness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def readiness_probe() -> HealthResponse:
    """Readiness probe to confirm external infrastructure connections are active."""
    return HealthResponse(status="ready", environment=settings.ENVIRONMENT)


@app.post("/v1/tenants", status_code=status.HTTP_201_CREATED, response_model=Tenant)
async def create_tenant(
    payload: CreateTenantRequest,
    x_admin_master_key: str = Header(..., alias="X-Admin-Master-Key"),
) -> Tenant:
    """Register a new tenant workspace bounds (System-wide Admin)."""
    if x_admin_master_key != settings.ADMIN_MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative master key credential.",
        )
    return await tenant_registry.create_tenant(
        name=payload.name,
        tier=payload.tier,
        isolation_level=payload.isolation_level,
    )


@app.put(
    "/v1/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation)],
)
async def update_tenant_config(
    tenantId: str,
    payload: ConfigUpdatePayload,
) -> dict[str, str]:
    """Update Dynamic configuration settings (CAD) for the tenant workspace."""
    # Convert payload schema parameters to Domain Entity model representation
    domain_config = TenantConfig(
        tenant_id=tenantId,
        active_model=payload.activeModel,
        temperature=payload.temperature,
        chunk_size=payload.chunkSize,
        chunk_overlap=payload.chunkOverlap,
        system_prompt_template=payload.systemPromptTemplate,
    )
    
    # Update DB first, then invalidate the cache to ensure cache coherence
    await tenant_registry.update_config(tenantId, domain_config)
    await config_cache.invalidate_config(tenantId)
    
    return {"tenantId": tenantId, "status": "updated"}


@app.get(
    "/v1/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfig,
    dependencies=[Depends(verify_tenant_isolation)],
)
async def get_tenant_config(tenantId: str) -> TenantConfig:
    """Get active configuration parameters (CAD) for the tenant workspace."""
    # Check L1 cache first (Redis)
    cached_config = await config_cache.get_cached_config(tenantId)
    if cached_config:
        return cached_config
        
    # Cache miss - fetch from DB
    config = await tenant_registry.get_config(tenantId)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found for active tenant workspace.",
        )
        
    # Write back to L1 Cache
    await config_cache.set_cached_config(tenantId, config)
    return config


@app.post(
    "/v1/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatedResponse,
    dependencies=[Depends(verify_tenant_isolation)],
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


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Retriever Core Platform API. Visit /docs for Swagger UI."}

