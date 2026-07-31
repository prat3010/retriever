"""Quota Management Service.

Calculates real-time tenant resource usage (documents, storage size,
monthly tokens, daily requests) against tenant quota settings, and raises
QuotaExceededError (HTTP 402/429) or returns soft limit warnings.
"""

from src.domain.abstractions.config import TenantConfiguration, TenantQuotaSettings
from src.domain.abstractions.exceptions import QuotaExceededError
from src.domain.abstractions.quota import QuotaRepository


class QuotaService:
    """Calculates usage metrics and enforces quota boundaries."""

    def __init__(self, repository: QuotaRepository | None = None) -> None:
        self.repository = repository

    async def get_storage_usage(self, tenant_id: str) -> tuple[int, int]:
        """Return (document_count, total_storage_bytes) for a tenant."""
        if not self.repository:
            return 0, 0
        return await self.repository.get_storage_usage(tenant_id)

    async def get_monthly_token_usage(self, tenant_id: str) -> int:
        """Return total tokens consumed by tenant in the current calendar month."""
        if not self.repository:
            return 0
        return await self.repository.get_monthly_token_usage(tenant_id)

    async def get_daily_request_usage(self, tenant_id: str) -> int:
        """Return total requests logged for tenant today (UTC)."""
        if not self.repository:
            return 0
        return await self.repository.get_daily_request_usage(tenant_id)

    async def check_storage_quota(
        self, tenant_id: str, new_file_size: int, config: TenantConfiguration
    ) -> str | None:
        """Check document count and storage size quotas.

        Raises QuotaExceededError (status_code=402) if hard limit is breached.
        Returns soft limit warning string if usage exceeds soft_limit_percentage.
        """
        quotas: TenantQuotaSettings = config.quota_settings
        doc_count, total_bytes = await self.get_storage_usage(tenant_id)

        # Check hard limits
        if quotas.max_documents is not None and doc_count + 1 > quotas.max_documents:
            raise QuotaExceededError(
                resource_type="documents",
                usage=doc_count + 1,
                limit=quotas.max_documents,
                status_code=402,
            )

        if quotas.max_storage_bytes is not None and total_bytes + new_file_size > quotas.max_storage_bytes:
            raise QuotaExceededError(
                resource_type="storage_bytes",
                usage=total_bytes + new_file_size,
                limit=quotas.max_storage_bytes,
                status_code=402,
            )

        # Check soft limits
        warning = None
        if quotas.max_storage_bytes and quotas.max_storage_bytes > 0:
            usage_pct = ((total_bytes + new_file_size) / quotas.max_storage_bytes) * 100
            if usage_pct >= quotas.soft_limit_percentage:
                warning = f"Storage usage at {usage_pct:.1f}% of quota ({total_bytes + new_file_size}/{quotas.max_storage_bytes} bytes)"

        if not warning and quotas.max_documents and quotas.max_documents > 0:
            doc_pct = ((doc_count + 1) / quotas.max_documents) * 100
            if doc_pct >= quotas.soft_limit_percentage:
                warning = f"Document count at {doc_pct:.1f}% of quota ({doc_count + 1}/{quotas.max_documents} docs)"

        return warning

    async def check_inference_quota(
        self, tenant_id: str, estimated_tokens: int, config: TenantConfiguration
    ) -> str | None:
        """Check token consumption and daily request volume quotas.

        Raises QuotaExceededError (status_code=429) if hard limit is breached.
        Returns soft limit warning string if usage exceeds soft_limit_percentage.
        """
        quotas: TenantQuotaSettings = config.quota_settings

        if quotas.max_daily_requests is not None:
            daily_reqs = await self.get_daily_request_usage(tenant_id)
            if daily_reqs + 1 > quotas.max_daily_requests:
                raise QuotaExceededError(
                    resource_type="daily_requests",
                    usage=daily_reqs + 1,
                    limit=quotas.max_daily_requests,
                    status_code=429,
                )

        if quotas.max_monthly_tokens is not None:
            monthly_tokens = await self.get_monthly_token_usage(tenant_id)
            if monthly_tokens + estimated_tokens > quotas.max_monthly_tokens:
                raise QuotaExceededError(
                    resource_type="monthly_tokens",
                    usage=monthly_tokens + estimated_tokens,
                    limit=quotas.max_monthly_tokens,
                    status_code=429,
                )

        return None
