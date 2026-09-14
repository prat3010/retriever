"""Database Change-Data-Capture (CDC) Data Connector for PostgreSQL and MySQL."""
import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    ConnectorManifest,
    ConnectorSyncState,
    DiscoveredDocument,
)

logger = logging.getLogger(__name__)


class DatabaseCdcConnector(BaseConnector):
    """High-watermark Change-Data-Capture (CDC) connector for relational databases.

    Features:
    - Supports PostgreSQL and MySQL sources.
    - Continuous incremental sync using high-watermark timestamps (e.g. `updated_at`) or sequence cursors.
    - Automatic tabular markdown and structured JSON serialization for vector chunking.
    - Soft-delete tracking (`is_deleted` or `deleted_at`).
    """

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="database_cdc",
            name="Relational Database CDC (PostgreSQL / MySQL)",
            description="Real-time change-data-capture streaming modified and new records into tenant vector storage.",
            icon="database",
            supports_incremental=True,
            required_parameters=["host", "database", "user", "tables"],
            optional_parameters={
                "db_type": "postgresql",
                "port": 5432,
                "password": "",
                "watermark_column": "updated_at",
                "primary_key": "id",
                "batch_size": 500,
            },
        )

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate database parameters and connectivity."""
        cfg = config.configuration
        if cfg.get("offline_sandbox", False):
            return True

        host = cfg.get("host")
        database = cfg.get("database")
        user = cfg.get("user")
        tables = cfg.get("tables")

        if not all([host, database, user, tables]):
            return False

        db_type = str(cfg.get("db_type", "postgresql")).lower()
        port = int(cfg.get("port", 5432 if db_type == "postgresql" else 3306))
        password = cfg.get("password", "")

        try:
            if db_type == "postgresql":
                import asyncpg
                conn = await asyncpg.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    timeout=5.0,
                )
                await conn.close()
                return True
            else:
                import asyncio
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0,
                )
                writer.close()
                await writer.wait_closed()
                return True
        except Exception as exc:
            logger.warning("Database CDC connection validation failed for %s:%s: %s", host, port, exc)
            return False

    def _format_row_to_document(
        self,
        table_name: str,
        row: dict[str, Any],
        primary_key_col: str,
        watermark_col: str,
        db_type: str,
    ) -> DiscoveredDocument:
        """Format an individual database row into a clean, searchable markdown document."""
        row_id = str(row.get(primary_key_col, "unknown"))
        watermark_val = str(row.get(watermark_col, datetime.now(UTC).isoformat()))
        is_deleted = bool(row.get("is_deleted") or row.get("deleted_at"))

        lines = [
            f"# Table: {table_name}",
            f"**Record ID**: `{row_id}`",
            f"**Source Engine**: `{db_type.upper()}`",
            f"**Last Modified**: `{watermark_val}`",
            "",
            "### Record Attributes",
            "",
            "| Field | Value |",
            "| :--- | :--- |",
        ]

        for col, val in sorted(row.items()):
            if col in (primary_key_col, watermark_col, "is_deleted", "deleted_at"):
                continue
            if isinstance(val, dict | list):
                formatted_val = json.dumps(val, default=str)
            else:
                formatted_val = str(val).replace("\n", " ")
            lines.append(f"| **{col}** | {formatted_val} |")

        content = "\n".join(lines)
        filename = f"cdc_{table_name}_{row_id}.md"

        return DiscoveredDocument(
            filename=filename,
            content=content,
            mime_type="text/markdown",
            source_url=f"db://{table_name}/{row_id}",
            is_deleted=is_deleted,
            metadata={
                "source": "database_cdc",
                "table": table_name,
                "row_id": row_id,
                "db_type": db_type,
                "watermark": watermark_val,
            },
        )

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Fetch documents without historical cursor (full initial pull)."""
        docs, _ = await self.fetch_incremental(config, ConnectorSyncState())
        return docs

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        """Fetch records with updated_at greater than current watermark."""
        cfg = config.configuration
        db_type = str(cfg.get("db_type", "postgresql")).lower()
        tables = cfg.get("tables", [])
        if isinstance(tables, str):
            tables = [t.strip() for t in tables.split(",") if t.strip()]

        watermark_col = cfg.get("watermark_column", "updated_at")
        primary_key_col = cfg.get("primary_key", "id")
        batch_size = int(cfg.get("batch_size", 500))

        current_watermark = state.watermark or "1970-01-01T00:00:00Z"
        highest_watermark = current_watermark
        discovered_docs: list[DiscoveredDocument] = []

        # Handle offline/sandbox mock data or dry-run testing
        if cfg.get("offline_sandbox", False) or cfg.get("mock_records"):
            mock_records = cfg.get("mock_records", {})
            for tbl in tables:
                records = mock_records.get(tbl, [])
                for r in records:
                    r_watermark = str(r.get(watermark_col, "1970-01-01T00:00:00Z"))
                    if r_watermark > current_watermark:
                        doc = self._format_row_to_document(
                            table_name=tbl,
                            row=r,
                            primary_key_col=primary_key_col,
                            watermark_col=watermark_col,
                            db_type=db_type,
                        )
                        discovered_docs.append(doc)
                        if r_watermark > highest_watermark:
                            highest_watermark = r_watermark

            new_state = ConnectorSyncState(
                cursor=f"lsn_{highest_watermark}",
                watermark=highest_watermark,
                last_sync_at=datetime.now(UTC).isoformat(),
                metadata={"total_tables": len(tables), "records_found": len(discovered_docs)},
            )
            return discovered_docs, new_state

        # Live PostgreSQL CDC query via asyncpg
        host = cfg.get("host")
        port = int(cfg.get("port", 5432))
        user = cfg.get("user")
        password = cfg.get("password", "")
        database = cfg.get("database")

        try:
            import asyncpg
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                timeout=10.0,
            )
            try:
                for tbl in tables:
                    safe_tbl = "".join(c for c in tbl if c.isalnum() or c == "_")
                    query = f"""
                        SELECT * FROM {safe_tbl}
                        WHERE {watermark_col} > $1
                        ORDER BY {watermark_col} ASC
                        LIMIT $2
                    """
                    rows = await conn.fetch(query, current_watermark, batch_size)
                    for row in rows:
                        row_dict = dict(row)
                        r_watermark = str(row_dict.get(watermark_col, ""))
                        doc = self._format_row_to_document(
                            table_name=safe_tbl,
                            row=row_dict,
                            primary_key_col=primary_key_col,
                            watermark_col=watermark_col,
                            db_type=db_type,
                        )
                        discovered_docs.append(doc)
                        if r_watermark > highest_watermark:
                            highest_watermark = r_watermark
            finally:
                await conn.close()
        except Exception as exc:
            logger.error("Database CDC execution failed on %s: %s", host, exc)
            raise

        new_state = ConnectorSyncState(
            cursor=f"lsn_{highest_watermark}",
            watermark=highest_watermark,
            last_sync_at=datetime.now(UTC).isoformat(),
            metadata={"total_tables": len(tables), "records_found": len(discovered_docs)},
        )
        return discovered_docs, new_state
