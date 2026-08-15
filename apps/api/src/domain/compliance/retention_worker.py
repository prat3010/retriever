"""Domain worker for scanning document age against tenant retention SLAs and auto-purging expired data."""

import logging
from datetime import UTC, datetime, timedelta

from src.domain.compliance.purge_service import HardPurgeService

logger = logging.getLogger(__name__)


class RetentionWorker:
    """Scans and purges documents exceeding tenant SLA data retention limits."""

    def __init__(self, purge_service: HardPurgeService, compliance_repo=None) -> None:
        self.purge_service = purge_service
        self.repo = compliance_repo

    async def scan_and_purge_expired_documents(
        self, tenant_id: str, retention_days: int
    ) -> dict[str, int]:
        """Find all documents older than retention_days and execute hard purge."""
        if retention_days <= 0 or not self.repo:
            return {"scanned": 0, "purged": 0}

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
        expired_doc_ids = await self.repo.get_expired_document_ids(tenant_id, cutoff_date)

        purged_count = 0
        for doc_id in expired_doc_ids:
            try:
                await self.purge_service.hard_purge_document(tenant_id, doc_id)
                purged_count += 1
            except Exception as err:
                logger.error(f"Failed to auto-purge expired document '{doc_id}' ({err}).")

        if purged_count > 0:
            logger.info(
                f"Data Retention Worker auto-purged {purged_count} document(s) older than {retention_days} days for tenant '{tenant_id}'."
            )

        return {"scanned": len(expired_doc_ids), "purged": purged_count}
