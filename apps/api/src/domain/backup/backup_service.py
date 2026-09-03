import logging

from src.domain.abstractions.backup import (
    BackupAdapterInterface,
    BackupSnapshotMetadata,
    BackupStatus,
    BackupTriggerRequest,
    BackupTriggerResponse,
    RestoreAdapterInterface,
    RestoreRequest,
    RestoreResponse,
)

logger = logging.getLogger(__name__)


class BackupService:
    """Pure domain service orchestrating platform cloud snapshots and point-in-time recovery."""

    def __init__(
        self,
        backup_adapter: BackupAdapterInterface,
        restore_adapter: RestoreAdapterInterface,
    ) -> None:
        self._backup_adapter = backup_adapter
        self._restore_adapter = restore_adapter

    async def create_snapshot(self, request: BackupTriggerRequest) -> BackupTriggerResponse:
        """Trigger an encrypted logical snapshot of the platform database."""
        logger.info("Initiating platform database snapshot via backup service.")
        try:
            metadata = await self._backup_adapter.create_snapshot(request)
            return BackupTriggerResponse(
                snapshot_id=metadata.snapshot_id,
                status=metadata.status,
                message=f"Snapshot {metadata.snapshot_id} created successfully ({len(metadata.tables)} tables dumped, {metadata.compressed_bytes} bytes).",
                metadata=metadata,
            )
        except Exception as e:
            logger.exception("Failed to execute platform database snapshot.")
            return BackupTriggerResponse(
                snapshot_id="unknown",
                status=BackupStatus.FAILED,
                message=f"Snapshot generation failed: {e!s}",
                metadata=None,
            )

    async def list_snapshots(self) -> list[BackupSnapshotMetadata]:
        """List all verified snapshots stored in off-site cloud storage."""
        return await self._backup_adapter.list_snapshots()

    async def restore_snapshot(self, request: RestoreRequest) -> RestoreResponse:
        """Execute disaster recovery or dry-run validation against a target snapshot."""
        logger.info(
            "Executing snapshot restoration (id=%s, dry_run=%s).",
            request.snapshot_id,
            request.dry_run,
        )
        return await self._restore_adapter.restore_snapshot(request)
