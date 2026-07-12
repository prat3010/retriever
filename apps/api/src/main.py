from typing import Optional
from fastapi import FastAPI, status, HTTPException, Header, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import text

from src.config import settings
from src.domain.abstractions.exceptions import TenantIsolationViolationError, AuthenticationError
from src.domain.abstractions.tenant import Tenant
from src.domain.abstractions.config import TenantConfiguration
from src.adapters.api.security import verify_tenant_isolation, verify_admin_key, verify_scopes
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.domain.config.config_service import ConfigurationService
from src.adapters.database.connection import engine
from src.adapters.cache.config_cache import redis_client

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


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Retriever Core Platform API. Visit /docs for Swagger UI."}


