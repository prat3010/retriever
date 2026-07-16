import logging

from src.domain.abstractions.notifications import AlertSeverity, NotificationProvider

logger = logging.getLogger(__name__)


class LoggingNotificationAdapter(NotificationProvider):

    async def send_alert(
        self,
        tenant_id: str,
        message: str,
        severity: AlertSeverity = "warning",
    ) -> None:
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.ERROR,
        }.get(severity, logging.WARNING)
        logger.log(log_level, "[budget alert] tenant=%s severity=%s %s", tenant_id, severity, message)
