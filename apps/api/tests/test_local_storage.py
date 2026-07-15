"""Tests for LocalStorage adapter (M12: Production Storage)."""

import os
import tempfile

import pytest

from src.adapters.storage.local_storage import LocalStorage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalStorage(storage_dir=tmpdir)


@pytest.mark.asyncio
async def test_save_file_creates_file(storage):
    path = await storage.save_file("tnt_001", "test.pdf", b"hello")
    assert os.path.exists(path)
    assert path.endswith("tnt_001/test.pdf")


@pytest.mark.asyncio
async def test_save_file_writes_content(storage):
    path = await storage.save_file("tnt_001", "test.pdf", b"hello world")
    with open(path, "rb") as f:
        assert f.read() == b"hello world"


@pytest.mark.asyncio
async def test_save_file_returns_absolute_path(storage):
    path = await storage.save_file("tnt_001", "doc.txt", b"data")
    assert os.path.isabs(path)
    assert storage.storage_dir in path


@pytest.mark.asyncio
async def test_delete_file_removes_file(storage):
    path = await storage.save_file("tnt_001", "delete_me.txt", b"bye")
    assert os.path.exists(path)
    await storage.delete_file(path)
    assert not os.path.exists(path)


@pytest.mark.asyncio
async def test_delete_file_missing_does_not_raise(storage):
    await storage.delete_file("/tmp/nonexistent_file_xyz.txt")


@pytest.mark.asyncio
async def test_generate_presigned_url_contains_params(storage):
    path = await storage.save_file("tnt_001", "report.pdf", b"content")
    url = await storage.generate_presigned_url(path, expiry_seconds=300)

    assert url.startswith("/v1/local-downloads/")
    assert "expires=" in url
    assert "signature=" in url
    assert "tnt_001/report.pdf" in url


@pytest.mark.asyncio
async def test_generate_presigned_url_signature_verifies(storage):
    import hmac
    import time
    from hashlib import sha256

    path = await storage.save_file("tnt_001", "doc.pdf", b"data")
    url = await storage.generate_presigned_url(path, expiry_seconds=300)

    # Parse URL components
    qs = url.split("?")[1]
    params = dict(p.split("=") for p in qs.split("&"))
    expires = int(params["expires"])
    sig = params["signature"]

    # Recompute expected signature
    relative = "tnt_001/doc.pdf"
    msg = f"{relative}:{expires}".encode()
    expected = hmac.new(b"local-storage-presign-key", msg=msg, digestmod=sha256).hexdigest()

    assert sig == expected
    assert expires > int(time.time())
