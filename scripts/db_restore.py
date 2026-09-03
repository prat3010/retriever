#!/usr/bin/env python3
"""Retriever Database Disaster Recovery & PITR CLI.

Performs cryptographic verification, decryption, and dependency DAG restoration
for a specified database snapshot.

Usage:
    # Dry-run validation (safe, checks checksums & decrypts):
    python3 scripts/db_restore.py --snapshot snap_20260904_120000 --dry-run

    # Live transactional restoration:
    python3 scripts/db_restore.py --snapshot snap_20260904_120000 --execute
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "apps" / "api"))

from src.adapters.backup.cloud_backup_adapter import CloudBackupAdapter  # noqa: E402
from src.adapters.backup.cloud_restore_adapter import CloudRestoreAdapter  # noqa: E402
from src.domain.abstractions.backup import RestoreRequest, RestoreStatus  # noqa: E402
from src.domain.backup.backup_service import BackupService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_restore")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Restore an encrypted cloud database snapshot.")
    parser.add_argument(
        "--snapshot",
        type=str,
        required=True,
        help="Snapshot ID to restore, e.g. snap_20260904_120000",
    )
    parser.add_argument(
        "--local-dir",
        type=str,
        default="/tmp/retriever/backups",
        help="Local directory containing backups and manifests.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Execute real live database restoration (default is dry-run mode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run simulation mode (validates checksums, schema, and decrypts without modifying data).",
    )
    args = parser.parse_args()

    is_dry_run = not args.execute

    adapter = CloudBackupAdapter(local_backup_dir=args.local_dir)
    restore_adapter = CloudRestoreAdapter(local_backup_dir=args.local_dir)
    service = BackupService(backup_adapter=adapter, restore_adapter=restore_adapter)

    req = RestoreRequest(
        snapshot_id=args.snapshot,
        dry_run=is_dry_run,
    )

    logger.info("Initiating restore process (dry_run=%s)...", is_dry_run)
    res = await service.restore_snapshot(req)

    print("\n" + "=" * 60)
    if res.status in (RestoreStatus.SUCCESS, RestoreStatus.DRY_RUN_PASSED):
        print(f"✅ RESTORE STATUS: {res.status.upper()}")
        print("=" * 60)
        print(f"Snapshot ID     : {res.snapshot_id}")
        print(f"Tables Restored : {len(res.tables_restored)} ({', '.join(res.tables_restored)})")
        print(f"Total Records   : {res.total_rows_restored:,}")
        print(f"Duration        : {res.duration_seconds}s")
        print(f"Details         : {res.message}")
        print("=" * 60 + "\n")
        sys.exit(0)
    else:
        print(f"❌ RESTORE FAILED: {res.status.upper()}")
        print("=" * 60)
        print(f"Error Message   : {res.message}")
        print("=" * 60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
