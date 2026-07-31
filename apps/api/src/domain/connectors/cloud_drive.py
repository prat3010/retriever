from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    DiscoveredDocument,
)


class MockCloudDriveConnector(BaseConnector):
    """Simulated cloud drive connector for Google Drive / Notion / S3 folder syncing."""

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        folder_id = config.configuration.get("folder_id") or config.configuration.get("bucket_name")
        return bool(folder_id)

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        folder_id = config.configuration.get("folder_id", "root_folder")
        connector_type = config.connector_type

        # Generate sample discovered cloud documents
        return [
            DiscoveredDocument(
                filename=f"{connector_type}_quarterly_report.txt",
                content=f"Quarterly Business Overview & Financial Highlights for {folder_id}.",
                mime_type="text/plain",
                source_url=f"cloud://{connector_type}/{folder_id}/quarterly_report.txt",
                metadata={
                    "connector_id": config.id,
                    "source": connector_type,
                    "folder_id": folder_id,
                },
            ),
            DiscoveredDocument(
                filename=f"{connector_type}_architecture_spec.txt",
                content=f"System Architecture & SaaS Security Standard Specification for {folder_id}.",
                mime_type="text/plain",
                source_url=f"cloud://{connector_type}/{folder_id}/architecture_spec.txt",
                metadata={
                    "connector_id": config.id,
                    "source": connector_type,
                    "folder_id": folder_id,
                },
            ),
        ]
