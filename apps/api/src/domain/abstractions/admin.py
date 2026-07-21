from abc import ABC, abstractmethod
from typing import Any


class AdminRepository(ABC):
    """Port for admin-only platform operations."""

    @abstractmethod
    async def get_platform_stats(self) -> dict[str, Any]:
        """Aggregate counts across all tenant data tables."""
        pass

    @abstractmethod
    async def reset_platform(
        self, include_system_tenant: bool = False
    ) -> int:
        """Delete all tenant data. Returns count of tenants deleted."""
        pass
