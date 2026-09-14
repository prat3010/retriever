"""Cloud Object Storage Data Connector for AWS S3, Cloudflare R2, and MinIO."""
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    ConnectorManifest,
    ConnectorSyncState,
    DiscoveredDocument,
)

logger = logging.getLogger(__name__)


class S3StorageConnector(BaseConnector):
    """Cloud Object Storage connector for S3, Cloudflare R2, MinIO, and Google Cloud Storage.

    Features:
    - Lists and filters bucket objects by folder prefix and allowed extensions.
    - Incremental sync via ETag and LastModified checksum verification.
    - Preserves object metadata (ETag, storage class, key, byte size).
    """

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {".txt", ".md", ".pdf", ".json", ".csv", ".html", ".docx"}

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="s3",
            name="Cloud Object Storage (S3 / R2 / MinIO / GCS)",
            description="Automated object storage watcher synchronizing documents from S3-compatible buckets.",
            icon="cloud",
            supports_incremental=True,
            required_parameters=["bucket_name"],
            optional_parameters={
                "endpoint_url": None,
                "prefix": "",
                "aws_access_key_id": "",
                "aws_secret_access_key": "",
                "region_name": "us-east-1",
                "allowed_extensions": list(self.SUPPORTED_EXTENSIONS),
            },
        )

    def _get_boto_client(self, config: ConnectorConfig) -> Any:
        import boto3
        cfg = config.configuration
        kwargs: dict[str, Any] = {
            "region_name": cfg.get("region_name", "us-east-1"),
        }
        if cfg.get("endpoint_url"):
            kwargs["endpoint_url"] = cfg["endpoint_url"]
        if cfg.get("aws_access_key_id"):
            kwargs["aws_access_key_id"] = cfg["aws_access_key_id"]
        if cfg.get("aws_secret_access_key"):
            kwargs["aws_secret_access_key"] = cfg["aws_secret_access_key"]

        return boto3.client("s3", **kwargs)

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate bucket connectivity and read permissions."""
        cfg = config.configuration
        if cfg.get("offline_sandbox", False):
            return True

        bucket = cfg.get("bucket_name")
        if not bucket:
            return False

        try:
            client = self._get_boto_client(config)
            # head_bucket or list with max-keys 1 verifies connectivity
            client.list_objects_v2(Bucket=bucket, MaxKeys=1)
            return True
        except Exception as exc:
            logger.warning("S3 credential validation error for bucket %s: %s", bucket, exc)
            return False

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Fetch all documents from target bucket without prior cursor."""
        docs, _ = await self.fetch_incremental(config, ConnectorSyncState())
        return docs

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        """Fetch new or modified objects comparing against known ETags."""
        cfg = config.configuration
        bucket = cfg.get("bucket_name", "")
        prefix = cfg.get("prefix", "")
        allowed_exts = set(cfg.get("allowed_extensions", self.SUPPORTED_EXTENSIONS))

        seen_etags: dict[str, str] = dict(state.metadata.get("seen_etags", {}))
        discovered_docs: list[DiscoveredDocument] = []
        now_iso = datetime.now(UTC).isoformat()

        # Offline sandbox / mock support
        if cfg.get("offline_sandbox", False) or cfg.get("mock_objects"):
            mock_objects = cfg.get("mock_objects", [])
            for obj in mock_objects:
                key = obj.get("key", "")
                ext = Path(key).suffix.lower()
                if allowed_exts and ext not in allowed_exts:
                    continue
                etag = obj.get("etag", "default-etag")
                if seen_etags.get(key) == etag:
                    continue  # Unmodified

                doc = DiscoveredDocument(
                    filename=Path(key).name,
                    content=obj.get("content", ""),
                    mime_type=obj.get("mime_type", "text/plain"),
                    source_url=f"s3://{bucket}/{key}",
                    metadata={
                        "source": "s3",
                        "bucket": bucket,
                        "s3_key": key,
                        "etag": etag,
                        "size": len(obj.get("content", "")),
                        "last_modified": obj.get("last_modified", now_iso),
                    },
                )
                discovered_docs.append(doc)
                seen_etags[key] = etag

            new_state = ConnectorSyncState(
                cursor=f"s3_cursor_{len(seen_etags)}",
                watermark=now_iso,
                last_sync_at=now_iso,
                metadata={"seen_etags": seen_etags, "synced_count": len(discovered_docs)},
            )
            return discovered_docs, new_state

        # Live boto3 S3 bucket discovery
        client = self._get_boto_client(config)
        paginator = client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in page_iterator:
            for item in page.get("Contents", []):
                key = item["Key"]
                ext = Path(key).suffix.lower()
                if allowed_exts and ext not in allowed_exts:
                    continue

                etag = item.get("ETag", "").strip('"')
                if seen_etags.get(key) == etag:
                    continue  # File unchanged since last sync

                # Download object bytes
                try:
                    obj_res = client.get_object(Bucket=bucket, Key=key)
                    raw_bytes = obj_res["Body"].read()
                    try:
                        content_str = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        content_str = f"[Binary Document: {key} ({len(raw_bytes)} bytes)]"

                    mime_type = obj_res.get("ContentType", "text/plain")
                    if ext == ".md":
                        mime_type = "text/markdown"
                    elif ext == ".json":
                        mime_type = "application/json"
                    elif ext == ".pdf":
                        mime_type = "application/pdf"

                    doc = DiscoveredDocument(
                        filename=Path(key).name,
                        content=content_str,
                        mime_type=mime_type,
                        source_url=f"s3://{bucket}/{key}",
                        metadata={
                            "source": "s3",
                            "bucket": bucket,
                            "s3_key": key,
                            "etag": etag,
                            "size": item.get("Size", len(raw_bytes)),
                            "last_modified": item.get("LastModified", datetime.now(UTC)).isoformat(),
                        },
                    )
                    discovered_docs.append(doc)
                    seen_etags[key] = etag
                except Exception as dl_err:
                    logger.warning("Failed to fetch S3 object s3://%s/%s: %s", bucket, key, dl_err)

        new_state = ConnectorSyncState(
            cursor=f"s3_cursor_{len(seen_etags)}",
            watermark=now_iso,
            last_sync_at=now_iso,
            metadata={"seen_etags": seen_etags, "synced_count": len(discovered_docs)},
        )
        return discovered_docs, new_state
