from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateConnectorRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the data connector.")
    connector_type: Literal["web_crawler", "cloud_drive", "google_drive", "notion", "slack", "s3"] = Field(
        ..., description="Data connector source type."
    )
    sync_interval_minutes: int = Field(default=1440, ge=15, le=43200, description="Sync frequency in minutes.")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Connector credentials/parameters.")


class UpdateConnectorRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sync_interval_minutes: int | None = Field(None, ge=15, le=43200)
    configuration: dict[str, Any] | None = None
    status: Literal["idle", "syncing", "failed", "disabled"] | None = None


class ConnectorSyncResponse(BaseModel):
    connectorId: str
    status: str
    documentsDiscovered: int
    documentsIngested: int
    durationMs: float
    message: str
