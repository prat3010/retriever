from abc import ABC, abstractmethod
from typing import Literal

AlertSeverity = Literal["info", "warning", "critical"]


class NotificationProvider(ABC):

    @abstractmethod
    async def send_alert(
        self,
        tenant_id: str,
        message: str,
        severity: AlertSeverity = "warning",
    ) -> None:
        pass
