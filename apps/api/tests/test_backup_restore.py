import base64
import gzip
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from src.adapters.backup.cloud_backup_adapter import CloudBackupAdapter
from src.adapters.backup.cloud_restore_adapter import CloudRestoreAdapter
from src.domain.abstractions.backup import (
    BackupStatus,
    BackupTriggerRequest,
    RestoreRequest,
    RestoreStatus,
)
from src.domain.backup.backup_service import BackupService
from src.main import app


@pytest.fixture
def temp_backup_env():
    """Create a temporary directory for backups and clean it up afterwards."""
    temp_dir = tempfile.mkdtemp(prefix="retriever_backup_test_")
    test_key = "test-master-backup-encryption-key-32-chars!"
    digest = hashlib.sha256(test_key.encode()).digest()
    fernet = Fernet(base64.urlsafe_b64encode(digest))

    yield {
        "dir": temp_dir,
        "key": test_key,
        "fernet": fernet,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_backup_and_restore_roundtrip(temp_backup_env):
    """Test full cycle: snapshot creation, encryption, checksum validation, and dry-run restore."""
    temp_dir = temp_backup_env["dir"]
    master_key = temp_backup_env["key"]

    backup_adapter = CloudBackupAdapter(
        master_key=master_key,
        local_backup_dir=temp_dir,
    )
    restore_adapter = CloudRestoreAdapter(
        master_key=master_key,
        local_backup_dir=temp_dir,
    )
    service = BackupService(
        backup_adapter=backup_adapter,
        restore_adapter=restore_adapter,
    )

    # 1. Trigger snapshot
    response = await service.create_snapshot(BackupTriggerRequest(include_tables=["tenants", "users"]))
    assert response.status == BackupStatus.COMPLETED
    assert response.metadata is not None
    m = response.metadata
    assert m.snapshot_id.startswith("snap_")
    assert len(m.sha256_checksum) == 64
    assert m.encryption_algorithm == "AES-256-GCM"

    # 2. Verify files written to disk
    archive_file = Path(temp_dir) / f"{m.snapshot_id}.tar.gz.enc"
    manifest_file = Path(temp_dir) / f"{m.snapshot_id}.manifest.json"
    assert archive_file.exists()
    assert manifest_file.exists()

    # 3. Verify ciphertext cannot be read as plain JSON (must be encrypted)
    raw_ciphertext = archive_file.read_bytes()
    with pytest.raises(Exception):
        json.loads(raw_ciphertext.decode("utf-8"))

    # 4. Verify manual decryption and decompress recovers JSON
    decrypted = temp_backup_env["fernet"].decrypt(raw_ciphertext)
    decompressed = gzip.decompress(decrypted).decode("utf-8")
    payload = json.loads(decompressed)
    assert payload["snapshot_id"] == m.snapshot_id
    assert "tenants" in payload["tables"]

    # 5. Execute dry-run restore
    restore_res = await service.restore_snapshot(RestoreRequest(snapshot_id=m.snapshot_id, dry_run=True))
    assert restore_res.status == RestoreStatus.DRY_RUN_PASSED
    assert m.snapshot_id == restore_res.snapshot_id
    assert "tenants" in restore_res.tables_restored

    # 6. List snapshots
    snapshots = await service.list_snapshots()
    assert len(snapshots) >= 1
    assert any(s.snapshot_id == m.snapshot_id for s in snapshots)


@pytest.mark.asyncio
async def test_tampered_archive_detection(temp_backup_env):
    """Test that tampering with archive bytes triggers SHA-256 cryptographic rejection."""
    temp_dir = temp_backup_env["dir"]
    master_key = temp_backup_env["key"]

    backup_adapter = CloudBackupAdapter(master_key=master_key, local_backup_dir=temp_dir)
    restore_adapter = CloudRestoreAdapter(master_key=master_key, local_backup_dir=temp_dir)
    service = BackupService(backup_adapter=backup_adapter, restore_adapter=restore_adapter)

    response = await service.create_snapshot(BackupTriggerRequest(include_tables=["tenants"]))
    snapshot_id = response.metadata.snapshot_id

    # Tamper with archive file
    archive_file = Path(temp_dir) / f"{snapshot_id}.tar.gz.enc"
    corrupted_bytes = b"TAMPERED_HEADER_" + archive_file.read_bytes()[16:]
    archive_file.write_bytes(corrupted_bytes)

    # Attempt restore
    res = await service.restore_snapshot(RestoreRequest(snapshot_id=snapshot_id, dry_run=True))
    assert res.status == RestoreStatus.FAILED
    assert "Cryptographic hash mismatch" in res.message or "mismatch" in res.message


def test_backup_admin_api_endpoints():
    """Test REST API endpoints: GET /v1/admin/platform/backups and POST /v1/admin/platform/backups/trigger."""
    client = TestClient(app)

    with patch("src.config.settings.ADMIN_MASTER_KEY", "test_admin_secret"):
        headers = {"X-Admin-Master-Key": "test_admin_secret"}

        # 1. Trigger snapshot via API
        post_res = client.post(
            "/v1/admin/platform/backups/trigger",
            headers=headers,
            json={"include_tables": ["tenants"]},
        )
        assert post_res.status_code == 200
        data = post_res.json()
        assert "snapshot_id" in data
        assert data["status"] == "completed"

        snapshot_id = data["snapshot_id"]

        # 2. List snapshots via API
        list_res = client.get("/v1/admin/platform/backups", headers=headers)
        assert list_res.status_code == 200
        snapshots = list_res.json()
        assert isinstance(snapshots, list)
        assert any(s["snapshot_id"] == snapshot_id for s in snapshots)

        # 3. Dry-run restore via API
        restore_res = client.post(
            "/v1/admin/platform/backups/restore",
            headers=headers,
            json={"snapshot_id": snapshot_id, "dry_run": True},
        )
        assert restore_res.status_code == 200
        restore_data = restore_res.json()
        assert restore_data["status"] == "dry_run_passed"


def test_hexagonal_architecture_boundaries():
    """Ensure pure domain abstractions and services never import infrastructure or framework adapters."""
    domain_files = [
        Path("apps/api/src/domain/abstractions/backup.py"),
        Path("apps/api/src/domain/backup/backup_service.py"),
    ]

    forbidden_imports = [
        "src.adapters",
        "src.routers",
        "sqlalchemy",
        "fastapi",
        "boto3",
        "psycopg2",
    ]

    for file_path in domain_files:
        content = file_path.read_text()
        for forbidden in forbidden_imports:
            assert forbidden not in content, (
                f"Hexagonal boundary violation in {file_path}: found '{forbidden}'"
            )
