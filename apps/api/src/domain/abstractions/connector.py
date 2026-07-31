from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field


class DiscoveredDocument(BaseModel):
    filename: str
    content: str
    mime_type: str = "text/plain"
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorConfig(BaseModel):
    id: str
    name: str
    connector_type: Literal["web_crawler", "cloud_drive", "google_drive", "notion", "slack", "s3"] = "web_crawler"
    status: Literal["idle", "syncing", "failed", "disabled"] = "idle"
    sync_interval_minutes: int = 1440
    configuration: dict[str, Any] = Field(default_factory=dict)
    last_sync_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


class BaseConnector(ABC):
    """Abstract base class for all SaaS Data Connectors."""

    @abstractmethod
    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate credentials or parameters provided in connector configuration."""
        pass

    @abstractmethod
    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Fetch/discover documents from external cloud data source."""
        pass
