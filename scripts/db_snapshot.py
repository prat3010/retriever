#!/usr/bin/env python3
"""Retriever Cloud Database Snapshot CLI.

Executes pooler-safe logical table dumps, gzip compression, AES-256 GCM encryption,
SHA-256 checksum generation, and off-site cloud archival.

Usage:
    python3 scripts/db_snapshot.py [--local-dir /path/to/backups]
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
from src.domain.abstractions.backup import BackupTriggerRequest  # noqa: E402
from src.domain.backup.backup_service import BackupService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_snapshot")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger an encrypted cloud database snapshot.")
    parser.add_argument(
        "--local-dir",
        type=str,
        default="/tmp/retriever/backups",
        help="Local directory to store encrypted archives and manifests.",
    )
    args = parser.parse_args()

    adapter = CloudBackupAdapter(local_backup_dir=args.local_dir)
    restore_adapter = CloudRestoreAdapter(local_backup_dir=args.local_dir)
    service = BackupService(backup_adapter=adapter, restore_adapter=restore_adapter)

    logger.info("Triggering encrypted database snapshot...")
    response = await service.create_snapshot(BackupTriggerRequest())

    if response.metadata:
        m = response.metadata
        print("\n" + "=" * 60)
        print("✅ DATABASE SNAPSHOT COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Snapshot ID     : {m.snapshot_id}")
        print(f"Timestamp       : {m.timestamp}")
        print(f"Tables Dumped   : {len(m.tables)}")
        print(f"Original Size   : {m.uncompressed_bytes:,} bytes")
        print(f"Encrypted Size  : {m.compressed_bytes:,} bytes")
        print(f"Algorithm       : {m.encryption_algorithm}")
        print(f"SHA-256 Digest  : {m.sha256_checksum}")
        print(f"Storage URI     : {m.storage_uri}")
        print(f"Duration        : {m.duration_seconds}s")
        print("=" * 60 + "\n")
        sys.exit(0)
    else:
        print(f"\n❌ Snapshot failed: {response.message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
