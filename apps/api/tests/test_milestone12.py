from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from processing_core import ConfigEncrypter

from src.adapters.storage.s3_storage import S3Storage
from src.main import app


# 1. Test Encryption / Decryption Primitives
def test_config_encrypter_basic():
    enc = ConfigEncrypter(key_encryption_key="super-secret-test-key-encryption-key-must-be-32-bytes")
    plaintext = "sk-proj-someopenaiapikeytest"

    # Encrypt
    ciphertext = enc.encrypt(plaintext)
    assert ciphertext != plaintext
    assert isinstance(ciphertext, str)

    # Decrypt
    decrypted = enc.decrypt(ciphertext)
    assert decrypted == plaintext


def test_config_encrypter_graceful_migration_plaintext():
    enc = ConfigEncrypter(key_encryption_key="super-secret-test-key-encryption-key-must-be-32-bytes")
    plaintext = "unencrypted_legacy_key"

    # Decrypting plaintext shouldn't throw, should return original plaintext
    decrypted = enc.decrypt(plaintext)
    assert decrypted == plaintext


def test_config_encrypter_redacted_preserved():
    enc = ConfigEncrypter(key_encryption_key="super-secret-test-key-encryption-key-must-be-32-bytes")
    redacted = "********"

    assert enc.encrypt(redacted) == redacted
    assert enc.decrypt(redacted) == redacted


# 2. Test S3Storage Adapter Implementation
@patch("boto3.Session")
@pytest.mark.asyncio
async def test_s3_storage_operations(mock_session_cls):
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_session_cls.return_value = mock_session

    storage = S3Storage(
        bucket_name="test-bucket",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        region_name="us-west-2",
        endpoint_url="http://localhost:9000",
    )

    # Test Save
    mock_client.put_object.return_value = {}
    path = await storage.save_file(
        tenant_id="tenant-123",
        filename="report.pdf",
        content=b"pdf_content_here",
    )
    assert path == "s3://test-bucket/tenant-123/report.pdf"
    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="tenant-123/report.pdf",
        Body=b"pdf_content_here",
    )

    # Test Delete
    mock_client.delete_object.return_value = {}
    await storage.delete_file(path)
    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="tenant-123/report.pdf",
    )

    # Test Presigned URL
    mock_client.generate_presigned_url.return_value = "http://presigned-link.com/download"
    url = await storage.generate_presigned_url(path, expiry_seconds=300)
    assert url == "http://presigned-link.com/download"
    mock_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "test-bucket", "Key": "tenant-123/report.pdf"},
        ExpiresIn=300,
    )


# 3. Test Config Database Integration (Encrypt on save, decrypt on load)
@pytest.mark.asyncio
@patch("src.adapters.database.config_repository.tenant_session")
async def test_sql_config_registry_encryption(mock_session_ctx):
    from src.adapters.database.config_repository import SqlConfigRegistry
    from src.adapters.database.models import ConfigurationDb

    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_session

    db_config_row = ConfigurationDb(
        tenant_id=None,
        key="config_payload",
        value={
            "ai_provider": {"provider_name": "openai", "api_key": "raw-key-to-encrypt"},
            "embedding_provider": {"provider_name": "openai", "api_key": "raw-embed-key"},
        },
        version=1,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = db_config_row
    mock_session.execute.return_value = mock_result

    registry = SqlConfigRegistry(key_encryption_key="test-kek-must-be-32-bytes-long-for-fernet=")

    # Test retrieve decrypts automatically
    loaded_config = await registry.get_raw_config(tenant_id=None)
    assert loaded_config["ai_provider"]["api_key"] == "raw-key-to-encrypt"
    assert loaded_config["embedding_provider"]["api_key"] == "raw-embed-key"

    # Test save encrypts before inserting
    # Clear mocks
    mock_session.execute.reset_mock()
    mock_result.scalar_one_or_none.return_value = None  # Force INSERT

    save_payload = {
        "ai_provider": {"provider_name": "openai", "api_key": "super-secret-raw-key"},
        "embedding_provider": {"provider_name": "openai", "api_key": "embed-secret-raw"},
    }

    await registry.save_raw_config(tenant_id=None, config_data=save_payload)

    # Inspect what was saved
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, ConfigurationDb)
    # The saved value should NOT contain raw plaintext key
    assert added_obj.value["ai_provider"]["api_key"] != "super-secret-raw-key"
    assert added_obj.value["embedding_provider"]["api_key"] != "embed-secret-raw"

    # Decrypting it back should reveal the plaintext
    decrypted_key = registry.encrypter.decrypt(added_obj.value["ai_provider"]["api_key"])
    assert decrypted_key == "super-secret-raw-key"


# 4. Test Health Readiness with S3 Probe
@patch("src.routers.health.redis_client.ping", new_callable=AsyncMock)
@patch("src.routers.health.engine", autospec=True)
def test_readiness_probe_with_s3(mock_engine, mock_redis_ping):
    mock_db_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_db_conn
    mock_redis_ping.return_value = "PONG"

    client = TestClient(app)

    # When S3 is not active
    with patch("src.routers.health.settings.STORAGE_PROVIDER", "local"):
        response = client.get("/health/readiness")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ready"

    # When S3 is active
    with patch("src.routers.health.settings.STORAGE_PROVIDER", "s3"):
        mock_s3_storage = MagicMock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.client = MagicMock()
        mock_s3_storage.client.head_bucket.return_value = {}

        with patch("src.routers.health.local_storage", mock_s3_storage):
            response = client.get("/health/readiness")
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "ready"
            mock_s3_storage.client.head_bucket.assert_called_once_with(Bucket="test-bucket")
