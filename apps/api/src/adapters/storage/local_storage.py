import asyncio
import os

import httpx

from src.domain.abstractions.ingestion import DocumentStorage


class LocalStorage(DocumentStorage):
    def __init__(self, storage_dir: str = "./storage", fallback_url: str = "", internal_key: str = "", hmac_key: str = "local-storage-presign-key") -> None:
        self.storage_dir = storage_dir
        self.fallback_url = fallback_url.rstrip("/")
        self.internal_key = internal_key
        self.hmac_key = hmac_key.encode() if isinstance(hmac_key, str) else hmac_key
        os.makedirs(self.storage_dir, exist_ok=True)

    async def save_file(self, tenant_id: str, filename: str, content: bytes) -> str:
        """Persist file to tenant-specific storage folder asynchronously."""
        tenant_dir = os.path.join(self.storage_dir, tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)

        file_path = os.path.join(tenant_dir, filename)

        def _write() -> None:
            with open(file_path, "wb") as f:
                f.write(content)

        await asyncio.to_thread(_write)
        return file_path

    async def read_file(self, storage_path: str) -> bytes | None:
        def _read() -> bytes | None:
            if not os.path.exists(storage_path):
                return None
            with open(storage_path, "rb") as f:
                return f.read()
        content = await asyncio.to_thread(_read)
        if content is not None:
            return content
        if not self.fallback_url or not self.internal_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.fallback_url}/v1/admin/storage/internal/{storage_path.lstrip('/')}",
                    headers={"X-Internal-Key": self.internal_key},
                )
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None

    async def delete_file(self, storage_path: str) -> None:
        """Asynchronously delete target file from disk."""
        def _delete() -> None:
            if os.path.exists(storage_path):
                os.remove(storage_path)

        await asyncio.to_thread(_delete)

    async def generate_presigned_url(self, storage_path: str, expiry_seconds: int = 300) -> str:
        """Generate a local temporary signed URL with HMAC verification."""
        import hmac
        import time
        from hashlib import sha256

        # Extract relative path to reconstruct target download file
        relative_path = os.path.relpath(storage_path, self.storage_dir)
        expires = int(time.time()) + expiry_seconds

        # Cryptographic HMAC-SHA256 signature
        msg = f"{relative_path}:{expires}".encode()
        sig = hmac.new(self.hmac_key, msg=msg, digestmod=sha256).hexdigest()

        return f"/v1/local-downloads/{relative_path}?expires={expires}&signature={sig}"
