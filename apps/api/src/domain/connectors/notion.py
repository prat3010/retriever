"""Authentic Notion REST API v1 Data Connector."""
import logging
from typing import Any

import httpx

from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    ConnectorManifest,
    ConnectorSyncState,
    DiscoveredDocument,
)

logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    """Production-grade Notion connector interfacing with Notion REST API v1.

    Supports:
    - Internal Integration Token (`Bearer secret_...`).
    - Querying pages from target Database ID (`/v1/databases/{database_id}/query`).
    - Recursive block tree extraction (`/v1/blocks/{page_id}/children`).
    - Full table block parsing (`table` and `table_row`) into standard Markdown tables.
    - Markdown conversion for paragraphs, headings, lists, quotes, callouts, and code blocks.
    - Incremental differential change tracking via `last_edited_time` cursor filter.
    - Document-level ACL extraction and group inheritance.
    """

    NOTION_API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="notion",
            name="Notion Knowledge Base",
            description="Extracts databases, pages, tables, and recursive block hierarchies with ACL mapping.",
            icon="notion",
            supports_incremental=True,
            required_parameters=["api_key", "database_id"],
            optional_parameters={"page_size": 100, "crawl_child_pages": True, "default_groups": []},
        )

    def _get_headers(self, config: ConnectorConfig) -> dict[str, str]:
        token = config.configuration.get("api_key") or config.configuration.get("access_token", "")
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate credentials by querying current bot identity or database."""
        token = config.configuration.get("api_key") or config.configuration.get("access_token")
        database_id = config.configuration.get("database_id")

        if not token:
            return bool(config.configuration.get("offline_sandbox", False) and database_id)

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"{self.NOTION_API_BASE}/users/me",
                    headers=self._get_headers(config),
                )
                return res.status_code == 200
        except Exception as exc:
            logger.warning("Notion credential validation error: %s", exc)
            return False

    @staticmethod
    def _extract_rich_text(rich_text_list: list[dict[str, Any]]) -> str:
        """Extract plain text string from Notion rich_text object array."""
        return "".join([t.get("plain_text", "") for t in rich_text_list if isinstance(t, dict)])

    def _parse_block_to_markdown(self, block: dict[str, Any]) -> str:
        """Convert a single Notion block object into standard Markdown."""
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})
        rich_text = block_data.get("rich_text", [])
        text = self._extract_rich_text(rich_text)

        if block_type == "paragraph":
            return f"{text}\n\n" if text else ""
        elif block_type == "heading_1":
            return f"# {text}\n\n"
        elif block_type == "heading_2":
            return f"## {text}\n\n"
        elif block_type == "heading_3":
            return f"### {text}\n\n"
        elif block_type == "bulleted_list_item":
            return f"- {text}\n"
        elif block_type == "numbered_list_item":
            return f"1. {text}\n"
        elif block_type == "quote":
            return f"> {text}\n\n"
        elif block_type == "callout":
            return f"> [!NOTE]\n> {text}\n\n"
        elif block_type == "code":
            lang = block_data.get("language", "")
            return f"```{lang}\n{text}\n```\n\n"
        elif block_type == "divider":
            return "---\n\n"
        elif block_type == "child_page":
            title = block_data.get("title", "Subpage")
            return f"\n### Subpage: {title}\n\n"

        return f"{text}\n" if text else ""

    async def _fetch_table_markdown(
        self, client: httpx.AsyncClient, table_block_id: str, headers: dict[str, str], table_data: dict[str, Any]
    ) -> str:
        """Fetch child rows for a table block and format into a standard Markdown table."""
        url = f"{self.NOTION_API_BASE}/blocks/{table_block_id}/children?page_size=100"
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            return ""

        row_blocks = res.json().get("results", [])
        if not row_blocks:
            return ""

        table_width = table_data.get("table_width", 0)
        has_column_header = table_data.get("has_column_header", True)

        rows_cells: list[list[str]] = []
        for row_block in row_blocks:
            if row_block.get("type") != "table_row":
                continue
            cells = row_block.get("table_row", {}).get("cells", [])
            row_text_cells = [self._extract_rich_text(cell_rich_text).replace("|", "\\|").strip() for cell_rich_text in cells]
            if table_width and len(row_text_cells) < table_width:
                row_text_cells.extend([""] * (table_width - len(row_text_cells)))
            rows_cells.append(row_text_cells)

        if not rows_cells:
            return ""

        col_count = len(rows_cells[0])
        lines: list[str] = []

        if has_column_header:
            header_row = rows_cells[0]
            lines.append("| " + " | ".join(header_row) + " |")
            lines.append("| " + " | ".join(["---"] * col_count) + " |")
            body_rows = rows_cells[1:]
        else:
            default_header = [f"Col {i+1}" for i in range(col_count)]
            lines.append("| " + " | ".join(default_header) + " |")
            lines.append("| " + " | ".join(["---"] * col_count) + " |")
            body_rows = rows_cells

        for row in body_rows:
            lines.append("| " + " | ".join(row) + " |")

        return "\n" + "\n".join(lines) + "\n\n"

    async def _fetch_page_content(
        self,
        client: httpx.AsyncClient,
        page_id: str,
        headers: dict[str, str],
        crawl_child_pages: bool = False,
        depth: int = 0,
        max_depth: int = 3,
    ) -> str:
        """Recursively fetch block children and compile page markdown, including tables and child pages."""
        if depth > max_depth:
            return ""

        url = f"{self.NOTION_API_BASE}/blocks/{page_id}/children?page_size=100"
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            return ""

        blocks_data = res.json()
        blocks = blocks_data.get("results", [])

        markdown_chunks: list[str] = []
        for b in blocks:
            b_type = b.get("type", "")
            if b_type == "table":
                table_md = await self._fetch_table_markdown(client, b.get("id", ""), headers, b.get("table", {}))
                markdown_chunks.append(table_md)
            elif b_type == "child_page" and crawl_child_pages:
                sub_id = b.get("id", "")
                sub_title = b.get("child_page", {}).get("title", "Subpage")
                markdown_chunks.append(f"\n## Subpage: {sub_title}\n\n")
                sub_content = await self._fetch_page_content(
                    client=client,
                    page_id=sub_id,
                    headers=headers,
                    crawl_child_pages=crawl_child_pages,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                markdown_chunks.append(sub_content)
            else:
                markdown_chunks.append(self._parse_block_to_markdown(b))

        return "".join(markdown_chunks).strip()

    def _get_sandbox_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        database_id = config.configuration.get("database_id", "notion_sandbox_db")
        return [
            DiscoveredDocument(
                filename="engineering_onboarding_guide.md",
                content=(
                    "# Engineering Onboarding Guide\n\n"
                    "Welcome to the technical engineering team. Below is our standard infrastructure matrix:\n\n"
                    "| Component | Technology | Cluster Tier |\n"
                    "| --- | --- | --- |\n"
                    "| Vector Engine | PostgreSQL + pgvector | Production High-Avail |\n"
                    "| Sparse Inverted Index | SPLADE + BM25 | Production Memory |\n"
                    "| LLM Reasoning Router | Local Ollama / vLLM | Self-Hosted GPU Cluster |\n\n"
                    "All engineers must complete onboarding checklist within 7 days."
                ),
                mime_type="text/markdown",
                source_url=f"https://notion.so/{database_id}_onboarding",
                allowed_users=[],
                allowed_groups=["engineering", "product"],
                is_public=False,
                metadata={
                    "connector_id": config.id,
                    "source": "notion",
                    "database_id": database_id,
                    "sync_mode": "sandbox",
                },
            ),
            DiscoveredDocument(
                filename="general_company_faq.md",
                content=(
                    "# General Company FAQ\n\n"
                    "Frequently asked questions regarding company policies, office hours, and public announcements.\n"
                    "This document is accessible to all verified organization members."
                ),
                mime_type="text/markdown",
                source_url=f"https://notion.so/{database_id}_faq",
                allowed_users=[],
                allowed_groups=[],
                is_public=True,
                metadata={
                    "connector_id": config.id,
                    "source": "notion",
                    "database_id": database_id,
                    "sync_mode": "sandbox",
                },
            ),
        ]

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Discover and download pages from the configured Notion database or page."""
        database_id = config.configuration.get("database_id")
        if not database_id:
            logger.warning("Notion connector '%s' missing database_id", config.id)
            return []

        token = config.configuration.get("api_key") or config.configuration.get("access_token")

        if not token and config.configuration.get("offline_sandbox", False):
            return self._get_sandbox_documents(config)

        if not token:
            logger.error("Notion connector '%s' missing API token", config.id)
            return []

        discovered: list[DiscoveredDocument] = []
        headers = self._get_headers(config)
        crawl_child_pages = bool(config.configuration.get("crawl_child_pages", True))
        default_groups = config.configuration.get("default_groups", [])

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                query_url = f"{self.NOTION_API_BASE}/databases/{database_id}/query"
                res = await client.post(query_url, headers=headers, json={"page_size": 100})

                if res.status_code != 200:
                    logger.error(
                        "Notion API query returned HTTP %d: %s",
                        res.status_code,
                        res.text[:200],
                    )
                    return []

                pages = res.json().get("results", [])

                for page in pages:
                    page_id = page.get("id", "")
                    last_edited = page.get("last_edited_time", "")
                    page_url = page.get("url", f"https://notion.so/{page_id.replace('-', '')}")
                    created_by = page.get("created_by", {}).get("id", "")

                    title = f"notion_page_{page_id[:8]}"
                    properties = page.get("properties", {})
                    for _, prop_val in properties.items():
                        if prop_val.get("type") == "title":
                            extracted = self._extract_rich_text(prop_val.get("title", []))
                            if extracted:
                                title = extracted
                                break

                    filename = f"{title.replace(' ', '_').lower()}.md"
                    content_md = await self._fetch_page_content(
                        client=client,
                        page_id=page_id,
                        headers=headers,
                        crawl_child_pages=crawl_child_pages,
                    )

                    if not content_md:
                        content_md = f"# {title}\n\n*Page synced from Notion database.*"

                    # ACL resolution: created_by user ID, default_groups, or public
                    allowed_users = [created_by] if created_by else []
                    allowed_groups = list(default_groups)
                    is_public = len(allowed_users) == 0 and len(allowed_groups) == 0

                    discovered.append(
                        DiscoveredDocument(
                            filename=filename,
                            content=content_md,
                            mime_type="text/markdown",
                            source_url=page_url,
                            allowed_users=allowed_users,
                            allowed_groups=allowed_groups,
                            is_public=is_public,
                            metadata={
                                "connector_id": config.id,
                                "source": "notion",
                                "notion_page_id": page_id,
                                "last_edited_time": last_edited,
                                "created_by": created_by,
                            },
                        )
                    )

        except Exception as exc:
            logger.error("Failed to fetch documents from Notion: %s", exc)

        return discovered

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        """Incremental differential fetch using Notion database last_edited_time filter."""
        database_id = config.configuration.get("database_id")
        if not database_id:
            return [], state

        token = config.configuration.get("api_key") or config.configuration.get("access_token")
        if not token and config.configuration.get("offline_sandbox", False):
            docs = self._get_sandbox_documents(config)
            state.cursor = "2026-09-23T00:00:00Z"
            return docs, state

        if not token:
            return [], state

        headers = self._get_headers(config)
        crawl_child_pages = bool(config.configuration.get("crawl_child_pages", True))
        default_groups = config.configuration.get("default_groups", [])

        query_payload: dict[str, Any] = {"page_size": 100}
        if state.cursor:
            query_payload["filter"] = {
                "timestamp": "last_edited_time",
                "last_edited_time": {"after": state.cursor},
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                query_url = f"{self.NOTION_API_BASE}/databases/{database_id}/query"
                res = await client.post(query_url, headers=headers, json=query_payload)
                if res.status_code != 200:
                    logger.error("Incremental Notion API query returned HTTP %d: %s", res.status_code, res.text[:200])
                    return [], state

                pages = res.json().get("results", [])
                discovered: list[DiscoveredDocument] = []
                latest_edited = state.cursor or ""

                for page in pages:
                    page_id = page.get("id", "")
                    last_edited = page.get("last_edited_time", "")
                    if last_edited and last_edited > latest_edited:
                        latest_edited = last_edited

                    page_url = page.get("url", f"https://notion.so/{page_id.replace('-', '')}")
                    created_by = page.get("created_by", {}).get("id", "")

                    title = f"notion_page_{page_id[:8]}"
                    for _, prop_val in page.get("properties", {}).items():
                        if prop_val.get("type") == "title":
                            extracted = self._extract_rich_text(prop_val.get("title", []))
                            if extracted:
                                title = extracted
                                break

                    filename = f"{title.replace(' ', '_').lower()}.md"
                    content_md = await self._fetch_page_content(
                        client=client,
                        page_id=page_id,
                        headers=headers,
                        crawl_child_pages=crawl_child_pages,
                    )

                    allowed_users = [created_by] if created_by else []
                    allowed_groups = list(default_groups)
                    is_public = len(allowed_users) == 0 and len(allowed_groups) == 0

                    discovered.append(
                        DiscoveredDocument(
                            filename=filename,
                            content=content_md or f"# {title}\n\n*Page synced from Notion database.*",
                            mime_type="text/markdown",
                            source_url=page_url,
                            allowed_users=allowed_users,
                            allowed_groups=allowed_groups,
                            is_public=is_public,
                            metadata={
                                "connector_id": config.id,
                                "source": "notion",
                                "notion_page_id": page_id,
                                "last_edited_time": last_edited,
                            },
                        )
                    )

                if latest_edited:
                    state.cursor = latest_edited
                return discovered, state
        except Exception as exc:
            logger.error("Incremental Notion sync failed: %s", exc)
            return [], state
