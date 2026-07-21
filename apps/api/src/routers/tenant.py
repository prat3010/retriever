import openai
from fastapi import APIRouter, Depends, Security, status

from src.adapters.api.security import (
    verify_admin_key,
    verify_scopes,
    verify_tenant_isolation,
)
from src.config import settings
from src.container import (
    audit_logger,
    config_service,
    identity_provider,
    tenant_registry,
)
from src.domain.abstractions.config import TenantConfiguration
from src.schemas.admin import (
    ApiKeyCreatedResponse,
    CreateApiKeyRequest,
    ValidateKeyRequest,
    ValidateKeyResponse,
)
from src.schemas.tenant import CreateTenantRequest, TenantListItem

router = APIRouter(prefix="/v1", tags=["Tenants"])


@router.post(
    "/tenants",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantListItem,
    dependencies=[Depends(verify_admin_key)],
)
async def create_tenant(
    payload: CreateTenantRequest,
) -> TenantListItem:
    tenant = await tenant_registry.create_tenant(
        name=payload.name,
        tier=payload.tier,
        isolation_level=payload.isolation_level,
    )
    await audit_logger.write(tenant.tenant_id, "tenant.created", f"Tenant '{payload.name}' created")
    return TenantListItem(
        tenantId=tenant.tenant_id,
        name=tenant.name,
        status=tenant.status,
        tier=tenant.tier,
        createdAt=tenant.created_at,
    )


@router.post(
    "/config/validate-key",
    status_code=status.HTTP_200_OK,
    response_model=ValidateKeyResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def validate_api_key(
    payload: ValidateKeyRequest,
) -> ValidateKeyResponse:
    try:
        api_key = payload.api_key or settings.OPENAI_API_KEY
        if not api_key:
            return ValidateKeyResponse(valid=False, error="No API key provided and no server-wide key found.")
        kwargs = {"api_key": api_key}
        base_url = payload.base_url
        if not base_url and payload.provider == "gemini":
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        elif not base_url and payload.provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        if base_url:
            kwargs["base_url"] = base_url
        client = openai.AsyncOpenAI(**kwargs)
        await client.chat.completions.create(
            model=payload.model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=10
        )
        return ValidateKeyResponse(valid=True)
    except openai.AuthenticationError as ae:
        return ValidateKeyResponse(valid=False, error=f"Authentication Error: {ae.message}")
    except Exception as e:
        return ValidateKeyResponse(valid=False, error=str(e))


@router.put(
    "/config/global",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def update_global_config(
    payload: TenantConfiguration,
) -> dict[str, str]:
    await config_service.update_global_config(payload)
    await audit_logger.write("global", "config.updated", "Global configuration updated")
    return {"status": "updated", "scope": "global"}


@router.get(
    "/config/global",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_admin_key)],
)
async def get_global_config() -> TenantConfiguration:
    config = await config_service.get_global_config()
    return config.redact_secrets()


@router.put(
    "/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def update_tenant_config(
    tenantId: str,
    payload: TenantConfiguration,
) -> dict[str, str]:
    await config_service.update_tenant_config(tenantId, payload)
    return {"tenantId": tenantId, "status": "updated"}


@router.get(
    "/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_tenant_config(tenantId: str) -> TenantConfiguration:
    config = await config_service.get_tenant_config(tenantId)
    return config.redact_secrets()


@router.post(
    "/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatedResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def generate_api_key(
    tenantId: str,
    payload: CreateApiKeyRequest,
) -> ApiKeyCreatedResponse:
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
