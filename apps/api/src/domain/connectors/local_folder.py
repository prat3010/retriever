"""Local Directory / File System Connector for Document Ingestion."""

import os
from pathlib import Path

from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    DiscoveredDocument,
)


class LocalFolderConnector(BaseConnector):
    """Local filesystem directory connector that ingests real documents from a path."""

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        folder_path = config.configuration.get("folder_path") or config.configuration.get("folder_id")
        if not folder_path:
            return False
        return os.path.isdir(str(folder_path))

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        folder_path = config.configuration.get("folder_path") or config.configuration.get("folder_id")
        if not folder_path or not os.path.isdir(str(folder_path)):
            return []

        discovered: list[DiscoveredDocument] = []
        path = Path(str(folder_path))
        supported_extensions = {".txt", ".md", ".json", ".csv"}

        for root, _, files in os.walk(path):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in supported_extensions and file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        discovered.append(
                            DiscoveredDocument(
                                filename=file_path.name,
                                content=content,
                                mime_type="text/plain",
                                source_url=file_path.as_uri(),
                                metadata={
                                    "connector_id": config.id,
                                    "source": "local_folder",
                                    "file_path": str(file_path),
                                },
                            )
                        )
                    except Exception:
                        continue
        return discovered
