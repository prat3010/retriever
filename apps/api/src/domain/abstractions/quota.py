from abc import ABC, abstractmethod


class QuotaRepository(ABC):
    """Abstract port for fetching tenant resource usage metrics."""

    @abstractmethod
    async def get_storage_usage(self, tenant_id: str) -> tuple[int, int]:
        """Return (document_count, total_storage_bytes) for a tenant."""
        pass

    @abstractmethod
    async def get_monthly_token_usage(self, tenant_id: str) -> int:
        """Return total tokens consumed by tenant in the current calendar month."""
        pass

    @abstractmethod
    async def get_daily_request_usage(self, tenant_id: str) -> int:
        """Return total requests logged for tenant today (UTC)."""
        pass
