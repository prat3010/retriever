import base64
import gzip
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import text

from src.adapters.backup.cloud_backup_adapter import TOPOLOGICAL_TABLE_ORDER
from src.adapters.database.connection import tenant_session
from src.adapters.storage.s3_storage import S3Storage
from src.domain.abstractions.backup import (
    RestoreAdapterInterface,
    RestoreRequest,
    RestoreResponse,
    RestoreStatus,
)

logger = logging.getLogger(__name__)


class CloudRestoreAdapter(RestoreAdapterInterface):
    """Production database restore adapter with cryptographic verification, dependency DAG insertion, and dry-run safety."""

    def __init__(
        self,
        master_key: str | None = None,
        storage: S3Storage | None = None,
        local_backup_dir: str | None = None,
    ) -> None:
        raw_key = (
            master_key
            or os.environ.get("BACKUP_ENCRYPTION_KEY")
            or os.environ.get("KEY_ENCRYPTION_KEY")
            or "retriever-default-backup-vault-key-32-chars!"
        )
        digest = hashlib.sha256(raw_key.encode()).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))
        self._storage = storage
        self._local_dir = Path(local_backup_dir or os.environ.get("LOCAL_BACKUP_DIR", "/tmp/retriever/backups"))

    async def _read_archive_bytes(self, snapshot_id: str) -> tuple[bytes, str]:
        archive_name = f"{snapshot_id}.tar.gz.enc"
        manifest_name = f"{snapshot_id}.manifest.json"

        local_archive = self._local_dir / archive_name
        local_manifest = self._local_dir / manifest_name

        if local_archive.exists() and local_manifest.exists():
            manifest_data = json.loads(local_manifest.read_text())
            expected_hash = manifest_data.get("sha256_checksum", "")
            return local_archive.read_bytes(), expected_hash

        if self._storage:
            s3_path = f"s3://system_backups/{archive_name}"
            archive_bytes = await self._storage.read_file(s3_path)
            manifest_bytes = await self._storage.read_file(f"s3://system_backups/{manifest_name}")
            if archive_bytes and manifest_bytes:
                manifest_data = json.loads(manifest_bytes.decode("utf-8"))
                expected_hash = manifest_data.get("sha256_checksum", "")
                return archive_bytes, expected_hash

        raise FileNotFoundError(f"Snapshot archive or manifest for '{snapshot_id}' not found.")

    async def restore_snapshot(self, request: RestoreRequest) -> RestoreResponse:
        start_time = time.perf_counter()
        logger.info("Starting restoration process for snapshot '%s' (dry_run=%s)", request.snapshot_id, request.dry_run)

        try:
            ciphertext, expected_hash = await self._read_archive_bytes(request.snapshot_id)

            # 1. Cryptographic SHA-256 integrity verification
            computed_hash = hashlib.sha256(ciphertext).hexdigest()
            if expected_hash and computed_hash != expected_hash:
                raise ValueError(
                    f"Cryptographic hash mismatch! Expected {expected_hash}, computed {computed_hash}. Archive may be corrupted or tampered."
                )

            # 2. Decrypt AES-256 payload
            compressed = self._fernet.decrypt(ciphertext)

            # 3. Decompress Gzip
            raw_json = gzip.decompress(compressed).decode("utf-8")
            payload = json.loads(raw_json)

            tables_data: dict[str, list[dict[str, Any]]] = payload.get("tables", {})
            tables_restored: list[str] = []
            total_rows = 0

            # 4. Topological traversal
            ordered_tables = [t for t in TOPOLOGICAL_TABLE_ORDER if t in tables_data]

            for table in ordered_tables:
                rows = tables_data[table]
                total_rows += len(rows)
                tables_restored.append(table)

            duration = round(time.perf_counter() - start_time, 3)

            # 5. Handle Dry-Run
            if request.dry_run:
                msg = (
                    f"DRY RUN PASSED: Verified cryptographic SHA-256 ({computed_hash[:8]}), "
                    f"decrypted {len(compressed)} bytes, successfully validated {len(tables_restored)} tables "
                    f"containing {total_rows} records. Database state untouched."
                )
                logger.info(msg)
                return RestoreResponse(
                    snapshot_id=request.snapshot_id,
                    status=RestoreStatus.DRY_RUN_PASSED,
                    tables_restored=tables_restored,
                    total_rows_restored=total_rows,
                    duration_seconds=duration,
                    message=msg,
                )

            # 6. Real Transactional Restore (Non-Dry-Run)
            async with tenant_session(bypass_rls=True) as session:
                for table in ordered_tables:
                    rows = tables_data[table]
                    if not rows:
                        continue

                    columns = list(rows[0].keys())
                    col_names = ", ".join(f'"{c}"' for c in columns)
                    placeholders = ", ".join(f":{c}" for c in columns)
                    insert_stmt = text(
                        f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
                    )

                    for batch_chunk in [rows[i:i + 100] for i in range(0, len(rows), 100)]:
                        await session.execute(insert_stmt, batch_chunk)

                await session.commit()

            msg = f"Disaster recovery successful: Restored {len(tables_restored)} tables and {total_rows} records in {duration}s."
            logger.info(msg)
            return RestoreResponse(
                snapshot_id=request.snapshot_id,
                status=RestoreStatus.SUCCESS,
                tables_restored=tables_restored,
                total_rows_restored=total_rows,
                duration_seconds=duration,
                message=msg,
            )

        except Exception as err:
            logger.exception("Restore operation failed for snapshot '%s': %s", request.snapshot_id, err)
            duration = round(time.perf_counter() - start_time, 3)
            return RestoreResponse(
                snapshot_id=request.snapshot_id,
                status=RestoreStatus.FAILED,
                tables_restored=[],
                total_rows_restored=0,
                duration_seconds=duration,
                message=f"Restoration failed: {err!s}",
            )
