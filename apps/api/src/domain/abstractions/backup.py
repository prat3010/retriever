from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BackupStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RestoreStatus(StrEnum):
    SUCCESS = "success"
    DRY_RUN_PASSED = "dry_run_passed"
    FAILED = "failed"


class BackupSnapshotMetadata(BaseModel):
    snapshot_id: str = Field(..., description="Unique snapshot identifier, e.g. 'snap_20260904_030000'")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tables: list[str] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    uncompressed_bytes: int = 0
    compressed_bytes: int = 0
    sha256_checksum: str = Field(..., description="Cryptographic SHA-256 digest of encrypted archive")
    encryption_algorithm: str = "AES-256-GCM"
    storage_uri: str = Field(..., description="Destination S3/R2 or local archive URI")
    status: BackupStatus = BackupStatus.COMPLETED
    duration_seconds: float = 0.0


class BackupTriggerRequest(BaseModel):
    include_tables: list[str] | None = None
    exclude_tables: list[str] | None = None


class BackupTriggerResponse(BaseModel):
    snapshot_id: str
    status: BackupStatus
    message: str
    metadata: BackupSnapshotMetadata | None = None


class RestoreRequest(BaseModel):
    snapshot_id: str
    target_db_url: str | None = None
    point_in_time: datetime | None = None
    dry_run: bool = True


class RestoreResponse(BaseModel):
    snapshot_id: str
    status: RestoreStatus
    tables_restored: list[str]
    total_rows_restored: int
    duration_seconds: float
    message: str


class BackupAdapterInterface(ABC):
    @abstractmethod
    async def create_snapshot(self, request: BackupTriggerRequest) -> BackupSnapshotMetadata:
        pass

    @abstractmethod
    async def list_snapshots(self) -> list[BackupSnapshotMetadata]:
        pass


class RestoreAdapterInterface(ABC):
    @abstractmethod
    async def restore_snapshot(self, request: RestoreRequest) -> RestoreResponse:
        pass
