"""Unit tests for Milestone 26: SaaS Tenant Resource Quotas."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.config import TenantConfiguration, TenantQuotaSettings
from src.domain.abstractions.exceptions import QuotaExceededError
from src.domain.abstractions.identity import UserContext
from src.domain.quota.quota_service import QuotaService
from src.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_quota_service_storage_hard_limit_documents() -> None:
    quota_service = QuotaService()
    config = TenantConfiguration(
        quota_settings=TenantQuotaSettings(
            max_documents=5,
            max_storage_bytes=1000000,
        )
    )

    with patch.object(quota_service, "get_storage_usage", new_callable=AsyncMock) as mock_usage:
        # Current usage: 5 docs, 5000 bytes
        mock_usage.return_value = (5, 5000)

        with pytest.raises(QuotaExceededError) as exc_info:
            await quota_service.check_storage_quota("tenant_123", new_file_size=100, config=config)

        assert exc_info.value.resource_type == "documents"
        assert exc_info.value.status_code == 402
        assert exc_info.value.usage == 6
        assert exc_info.value.limit == 5


@pytest.mark.asyncio
async def test_quota_service_storage_hard_limit_bytes() -> None:
    quota_service = QuotaService()
    config = TenantConfiguration(
        quota_settings=TenantQuotaSettings(
            max_documents=10,
            max_storage_bytes=5000,
        )
    )

    with patch.object(quota_service, "get_storage_usage", new_callable=AsyncMock) as mock_usage:
        # Current usage: 2 docs, 4500 bytes
        mock_usage.return_value = (2, 4500)

        with pytest.raises(QuotaExceededError) as exc_info:
            await quota_service.check_storage_quota("tenant_123", new_file_size=1000, config=config)

        assert exc_info.value.resource_type == "storage_bytes"
        assert exc_info.value.status_code == 402
        assert exc_info.value.usage == 5500
        assert exc_info.value.limit == 5000


@pytest.mark.asyncio
async def test_quota_service_storage_soft_limit_warning() -> None:
    quota_service = QuotaService()
    config = TenantConfiguration(
        quota_settings=TenantQuotaSettings(
            max_documents=10,
            max_storage_bytes=10000,
            soft_limit_percentage=80.0,
        )
    )

    with patch.object(quota_service, "get_storage_usage", new_callable=AsyncMock) as mock_usage:
        # Current usage: 2 docs, 7500 bytes + 1000 bytes new = 8500 (85% of quota)
        mock_usage.return_value = (2, 7500)

        warning = await quota_service.check_storage_quota("tenant_123", new_file_size=1000, config=config)
        assert warning is not None
        assert "85.0%" in warning


@pytest.mark.asyncio
async def test_quota_service_inference_monthly_tokens_exceeded() -> None:
    quota_service = QuotaService()
    config = TenantConfiguration(
        quota_settings=TenantQuotaSettings(
            max_monthly_tokens=10000,
        )
    )

    with patch.object(quota_service, "get_monthly_token_usage", new_callable=AsyncMock) as mock_usage:
        mock_usage.return_value = 9950

        with pytest.raises(QuotaExceededError) as exc_info:
            await quota_service.check_inference_quota("tenant_123", estimated_tokens=100, config=config)

        assert exc_info.value.resource_type == "monthly_tokens"
        assert exc_info.value.status_code == 429
        assert exc_info.value.usage == 10050
        assert exc_info.value.limit == 10000


@pytest.mark.asyncio
async def test_quota_service_inference_daily_requests_exceeded() -> None:
    quota_service = QuotaService()
    config = TenantConfiguration(
        quota_settings=TenantQuotaSettings(
            max_daily_requests=50,
        )
    )

    with patch.object(quota_service, "get_daily_request_usage", new_callable=AsyncMock) as mock_usage:
        mock_usage.return_value = 50

        with pytest.raises(QuotaExceededError) as exc_info:
            await quota_service.check_inference_quota("tenant_123", estimated_tokens=10, config=config)

        assert exc_info.value.resource_type == "daily_requests"
        assert exc_info.value.status_code == 429
        assert exc_info.value.usage == 51
        assert exc_info.value.limit == 50


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.routers.document.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.routers.document.quota_service.check_storage_quota", new_callable=AsyncMock)
def test_document_upload_quota_exceeded_402(mock_check_quota, mock_get_config, mock_validate) -> None:
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id="tenant_123",
        roles=["client"],
        scopes=["document:write"],
    )
    mock_get_config.return_value = TenantConfiguration()
    mock_check_quota.side_effect = QuotaExceededError(
        resource_type="documents",
        usage=11,
        limit=10,
        status_code=402,
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    files = {"file": ("test.pdf", b"sample file content", "application/pdf")}

    response = client.post("/v1/tenants/tenant_123/documents", headers=headers, files=files)

    assert response.status_code == 402
    assert response.headers["Quota-Exceeded-Resource"] == "documents"
    assert response.headers["Quota-Limit"] == "10"
    assert response.headers["Quota-Usage"] == "11"
    assert "Tenant quota exceeded for documents" in response.json()["detail"]


from src.domain.abstractions.inference import ChatSessionInfo


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.routers.chat.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.routers.chat.quota_service.check_inference_quota", new_callable=AsyncMock)
@patch("src.routers.chat.inference_orchestrator.get_session", new_callable=AsyncMock)
def test_chat_message_token_quota_exceeded_429(
    mock_get_session, mock_check_quota, mock_get_config, mock_validate
) -> None:
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id="tenant_123",
        roles=["client"],
        scopes=["document:write"],
    )
    user_id = str(uuid.uuid4())
    mock_get_session.return_value = ChatSessionInfo(
        session_id="sess_123",
        tenant_id="tenant_123",
        user_id=user_id,
        created_at="2026-07-31T00:00:00Z",
    )
    mock_get_config.return_value = TenantConfiguration()
    mock_check_quota.side_effect = QuotaExceededError(
        resource_type="monthly_tokens",
        usage=500000,
        limit=500000,
        status_code=429,
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": user_id}
    payload = {"query": "Hello AI"}

    response = client.post(
        "/v1/tenants/tenant_123/chat/sessions/sess_123/messages",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 429
    assert response.headers["Quota-Exceeded-Resource"] == "monthly_tokens"
    assert response.headers["Quota-Limit"] == "500000"
    assert response.headers["Quota-Usage"] == "500000"
    assert "Tenant quota exceeded for monthly_tokens" in response.json()["detail"]
