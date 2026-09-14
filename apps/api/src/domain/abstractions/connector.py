from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field


class DiscoveredDocument(BaseModel):
    filename: str
    content: str
    mime_type: str = "text/plain"
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_deleted: bool = False


class ConnectorSyncState(BaseModel):
    cursor: str | None = None
    watermark: str | None = None
    last_sync_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorManifest(BaseModel):
    connector_type: str
    name: str
    description: str
    icon: str = "database"
    supports_incremental: bool = False
    required_parameters: list[str] = Field(default_factory=list)
    optional_parameters: dict[str, Any] = Field(default_factory=dict)


class ConnectorConfig(BaseModel):
    id: str
    name: str
    connector_type: Literal[
        "web_crawler",
        "cloud_drive",
        "google_drive",
        "notion",
        "slack",
        "s3",
        "gcs",
        "local_folder",
        "postgres_cdc",
        "mysql_cdc",
        "database_cdc",
        "github",
    ] = "web_crawler"
    status: Literal["idle", "syncing", "failed", "disabled"] = "idle"
    sync_interval_minutes: int = 1440
    configuration: dict[str, Any] = Field(default_factory=dict)
    last_sync_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


class BaseDocumentParser(ABC):
    """Abstract base class for custom community-authored document parsers."""

    @abstractmethod
    def can_parse(self, filename: str, mime_type: str) -> bool:
        """Return True if this parser can handle the provided file type."""
        pass

    @abstractmethod
    def parse(
        self,
        content_bytes: bytes,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DiscoveredDocument]:
        """Parse raw binary data into structured DiscoveredDocument objects."""
        pass


class BaseConnector(ABC):
    """Abstract base class for all SaaS and Enterprise Data Connectors."""

    @abstractmethod
    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate credentials or parameters provided in connector configuration."""
        pass

    @abstractmethod
    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Fetch/discover documents from external cloud data source."""
        pass

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        """Fetch documents incrementally using watermark or cursor state."""
        docs = await self.fetch_documents(config)
        return docs, state

    def get_manifest(self) -> ConnectorManifest:
        """Return connector descriptor manifest and parameter requirements."""
        return ConnectorManifest(
            connector_type="generic",
            name="Generic Connector",
            description="Abstract connector implementation.",
            icon="plug",
            supports_incremental=False,
        )
