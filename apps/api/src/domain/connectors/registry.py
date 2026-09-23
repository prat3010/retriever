from collections.abc import Callable
from typing import ClassVar, TypeVar

from src.domain.abstractions.connector import BaseConnector, ConnectorManifest
from src.domain.connectors.cloud_storage import S3StorageConnector
from src.domain.connectors.confluence_jira import ConfluenceConnector, JiraConnector
from src.domain.connectors.database_cdc import DatabaseCdcConnector
from src.domain.connectors.github import GitHubConnector
from src.domain.connectors.google_drive import GoogleDriveConnector
from src.domain.connectors.local_folder import LocalFolderConnector
from src.domain.connectors.microsoft365 import Microsoft365Connector
from src.domain.connectors.notion import NotionConnector
from src.domain.connectors.slack import SlackConnector
from src.domain.connectors.web_crawler import WebCrawlerConnector

T = TypeVar("T", bound=type[BaseConnector])


class ConnectorRegistry:
    """Registry to resolve connector strategy implementations by connector_type."""

    _db_cdc = DatabaseCdcConnector()
    _s3_storage = S3StorageConnector()
    _m365 = Microsoft365Connector()

    _connectors: ClassVar[dict[str, BaseConnector]] = {
        "web_crawler": WebCrawlerConnector(),
        "google_drive": GoogleDriveConnector(),
        "notion": NotionConnector(),
        "local_folder": LocalFolderConnector(),
        "cloud_drive": LocalFolderConnector(),
        "postgres_cdc": _db_cdc,
        "mysql_cdc": _db_cdc,
        "database_cdc": _db_cdc,
        "s3": _s3_storage,
        "gcs": _s3_storage,
        "github": GitHubConnector(),
        "slack": SlackConnector(),
        "confluence": ConfluenceConnector(),
        "jira": JiraConnector(),
        "microsoft365": _m365,
        "sharepoint": _m365,
    }

    @classmethod
    def register(cls, connector_type: str, connector: BaseConnector) -> None:
        """Register a custom connector instance."""
        cls._connectors[connector_type] = connector

    @classmethod
    def get_connector(cls, connector_type: str) -> BaseConnector:
        if connector_type not in cls._connectors:
            raise NotImplementedError(
                f"Connector type '{connector_type}' is not implemented. "
                f"Supported connectors: {list(cls._connectors.keys())}"
            )
        return cls._connectors[connector_type]

    @classmethod
    def list_manifests(cls) -> list[ConnectorManifest]:
        """Return catalog of unique connector manifests."""
        seen_types: set[str] = set()
        manifests: list[ConnectorManifest] = []
        for _c_type, connector in cls._connectors.items():
            manifest = connector.get_manifest()
            manifest_type = manifest.connector_type
            if manifest_type not in seen_types:
                seen_types.add(manifest_type)
                manifests.append(manifest)
        return manifests


def register_connector(connector_type: str) -> Callable[[T], T]:
    """Decorator to register community-authored or custom connector classes."""

    def decorator(cls_target: T) -> T:
        instance = cls_target()
        ConnectorRegistry.register(connector_type, instance)
        return cls_target

    return decorator
