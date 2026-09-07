from typing import ClassVar

from src.domain.abstractions.connector import BaseConnector
from src.domain.connectors.google_drive import GoogleDriveConnector
from src.domain.connectors.local_folder import LocalFolderConnector
from src.domain.connectors.notion import NotionConnector
from src.domain.connectors.web_crawler import WebCrawlerConnector


class ConnectorRegistry:
    """Registry to resolve connector strategy implementations by connector_type."""

    _connectors: ClassVar[dict[str, BaseConnector]] = {
        "web_crawler": WebCrawlerConnector(),
        "google_drive": GoogleDriveConnector(),
        "notion": NotionConnector(),
        "local_folder": LocalFolderConnector(),
        "cloud_drive": LocalFolderConnector(),
    }

    @classmethod
    def get_connector(cls, connector_type: str) -> BaseConnector:
        if connector_type not in cls._connectors:
            raise NotImplementedError(
                f"Connector type '{connector_type}' is not implemented. "
                f"Supported connectors: {list(cls._connectors.keys())}"
            )
        return cls._connectors[connector_type]
