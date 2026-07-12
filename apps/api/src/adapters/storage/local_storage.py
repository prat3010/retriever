import os
import asyncio
from src.domain.abstractions.ingestion import DocumentStorage


class LocalStorage(DocumentStorage):
    def __init__(self, storage_dir: str = "./storage") -> None:
        self.storage_dir = storage_dir
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

    async def delete_file(self, storage_path: str) -> None:
        """Asynchronously delete target file from disk."""
        def _delete() -> None:
            if os.path.exists(storage_path):
                os.remove(storage_path)

        await asyncio.to_thread(_delete)
