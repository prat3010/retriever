from typing import ClassVar

from src.domain.abstractions.connector import BaseConnector
from src.domain.connectors.cloud_drive import MockCloudDriveConnector
from src.domain.connectors.web_crawler import WebCrawlerConnector


class ConnectorRegistry:
    """Registry to resolve connector strategy implementations by connector_type."""

    _connectors: ClassVar[dict[str, BaseConnector]] = {
        "web_crawler": WebCrawlerConnector(),
        "cloud_drive": MockCloudDriveConnector(),
        "google_drive": MockCloudDriveConnector(),
        "notion": MockCloudDriveConnector(),
        "slack": MockCloudDriveConnector(),
        "s3": MockCloudDriveConnector(),
    }

    @classmethod
    def get_connector(cls, connector_type: str) -> BaseConnector:
        return cls._connectors.get(connector_type, WebCrawlerConnector())
