import asyncio

import boto3
from botocore.config import Config

from src.domain.abstractions.ingestion import DocumentStorage


class S3Storage(DocumentStorage):
    """S3-compatible object storage provider adapter (AWS S3, MinIO, Cloudflare R2)."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url

        session_opts = {}
        if aws_access_key_id:
            session_opts["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_opts["aws_secret_access_key"] = aws_secret_access_key
        if region_name:
            session_opts["region_name"] = region_name

        self.session = boto3.Session(**session_opts)

        client_opts = {}
        if endpoint_url:
            client_opts["endpoint_url"] = endpoint_url
            client_opts["config"] = Config(signature_version="s3v4", s3={"addressing_style": "path"})

        self.client = self.session.client("s3", **client_opts)

    async def save_file(self, tenant_id: str, filename: str, content: bytes) -> str:
        """Upload file content to S3, returning the s3:// URI."""
        s3_key = f"{tenant_id}/{filename}"

        def _upload() -> None:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
            )

        await asyncio.to_thread(_upload)
        return f"s3://{self.bucket_name}/{s3_key}"

    async def read_file(self, storage_path: str) -> bytes | None:
        if not storage_path.startswith("s3://"):
            return None
        path_parts = storage_path[5:].split("/", 1)
        if len(path_parts) != 2:
            return None
        bucket = path_parts[0]
        key = path_parts[1]

        def _read() -> bytes | None:
            try:
                obj = self.client.get_object(Bucket=bucket, Key=key)
                return obj["Body"].read()
            except Exception:
                return None

        return await asyncio.to_thread(_read)

    async def delete_file(self, storage_path: str) -> None:
        """Remove target file key from S3."""
        if not storage_path.startswith("s3://"):
            return

        path_parts = storage_path[5:].split("/", 1)
        if len(path_parts) != 2:
            return

        bucket = path_parts[0]
        key = path_parts[1]

        def _delete() -> None:
            self.client.delete_object(Bucket=bucket, Key=key)

        await asyncio.to_thread(_delete)

    async def generate_presigned_url(self, storage_path: str, expiry_seconds: int = 300) -> str:
        """Generate a pre-signed GET URL for document download."""
        if not storage_path.startswith("s3://"):
            raise ValueError("Storage path must be an S3 URI starting with s3://")

        path_parts = storage_path[5:].split("/", 1)
        if len(path_parts) != 2:
            raise ValueError("Invalid S3 URI path format")

        bucket = path_parts[0]
        key = path_parts[1]

        def _presign() -> str:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry_seconds,
            )

        return await asyncio.to_thread(_presign)
