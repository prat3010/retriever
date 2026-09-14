"""GitHub REST API Data Connector for Repositories, Documentation, and Issues."""
import logging
from datetime import UTC, datetime
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


class GitHubConnector(BaseConnector):
    """Production-grade GitHub connector interfacing with GitHub REST API v3.

    Supports:
    - Synchronizing repository Markdown documentation.
    - Ingesting GitHub Issues and Pull Requests with author, labels, and state.
    - Incremental sync via the `since` timestamp parameter.
    """

    GITHUB_API_BASE = "https://api.github.com"

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="github",
            name="GitHub Repository & Issues",
            description="Ingests repository markdown documentation, issues, and pull requests with incremental change tracking.",
            icon="github",
            supports_incremental=True,
            required_parameters=["repo"],
            optional_parameters={
                "access_token": "",
                "sync_targets": ["docs", "issues"],
                "branch": "main",
            },
        )

    def _get_headers(self, config: ConnectorConfig) -> dict[str, str]:
        cfg = config.configuration
        token = cfg.get("access_token") or cfg.get("api_key", "")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Retriever-Connector/1.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate GitHub repository access."""
        cfg = config.configuration
        if cfg.get("offline_sandbox", False):
            return True

        repo = cfg.get("repo")
        if not repo or "/" not in repo:
            return False

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"{self.GITHUB_API_BASE}/repos/{repo}",
                    headers=self._get_headers(config),
                )
                return res.status_code == 200
        except Exception as exc:
            logger.warning("GitHub credential validation error for %s: %s", repo, exc)
            return False

    def _format_issue_to_document(self, repo: str, issue: dict[str, Any]) -> DiscoveredDocument:
        """Format GitHub issue or pull request into structured markdown."""
        number = issue.get("number", 0)
        title = issue.get("title", "")
        body = issue.get("body") or "(No description provided)"
        state = issue.get("state", "open")
        author = issue.get("user", {}).get("login", "unknown")
        labels = [lbl.get("name", "") for lbl in issue.get("labels", []) if isinstance(lbl, dict)]
        is_pr = "pull_request" in issue
        item_type = "Pull Request" if is_pr else "Issue"
        created_at = issue.get("created_at", "")
        updated_at = issue.get("updated_at", "")
        html_url = issue.get("html_url", f"https://github.com/{repo}/issues/{number}")

        lines = [
            f"# GitHub {item_type} #{number}: {title}",
            f"- **Repository**: `{repo}`",
            f"- **Status**: `{state.upper()}`",
            f"- **Author**: `@{author}`",
            f"- **Labels**: `{', '.join(labels) if labels else 'None'}`",
            f"- **Created**: `{created_at}`",
            f"- **Updated**: `{updated_at}`",
            f"- **URL**: {html_url}",
            "",
            "## Description",
            "",
            body,
        ]

        content = "\n".join(lines)
        filename = f"github_{repo.replace('/', '_')}_{'pr' if is_pr else 'issue'}_{number}.md"

        return DiscoveredDocument(
            filename=filename,
            content=content,
            mime_type="text/markdown",
            source_url=html_url,
            metadata={
                "source": "github",
                "repo": repo,
                "item_type": item_type.lower(),
                "number": number,
                "state": state,
                "author": author,
                "labels": labels,
                "updated_at": updated_at,
            },
        )

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Fetch all documents from target repo without prior cursor."""
        docs, _ = await self.fetch_incremental(config, ConnectorSyncState())
        return docs

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        """Fetch repository docs and issues updated since watermark."""
        cfg = config.configuration
        repo = cfg.get("repo", "")
        sync_targets = cfg.get("sync_targets", ["docs", "issues"])
        watermark = state.watermark or "1970-01-01T00:00:00Z"
        highest_watermark = watermark
        discovered_docs: list[DiscoveredDocument] = []
        now_iso = datetime.now(UTC).isoformat()

        # Offline sandbox / mock data
        if cfg.get("offline_sandbox", False) or cfg.get("mock_data"):
            mock_data = cfg.get("mock_data", {})
            for issue in mock_data.get("issues", []):
                i_updated = str(issue.get("updated_at", "1970-01-01T00:00:00Z"))
                if i_updated > watermark:
                    doc = self._format_issue_to_document(repo, issue)
                    discovered_docs.append(doc)
                    if i_updated > highest_watermark:
                        highest_watermark = i_updated

            new_state = ConnectorSyncState(
                cursor=f"gh_{highest_watermark}",
                watermark=highest_watermark,
                last_sync_at=now_iso,
                metadata={"repo": repo, "synced_count": len(discovered_docs)},
            )
            return discovered_docs, new_state

        # Live GitHub REST API extraction
        headers = self._get_headers(config)
        async with httpx.AsyncClient(timeout=15.0) as client:
            if "issues" in sync_targets:
                params = {
                    "state": "all",
                    "since": watermark,
                    "per_page": 100,
                    "sort": "updated",
                    "direction": "asc",
                }
                res = await client.get(
                    f"{self.GITHUB_API_BASE}/repos/{repo}/issues",
                    headers=headers,
                    params=params,
                )
                if res.status_code == 200:
                    for issue in res.json():
                        i_updated = str(issue.get("updated_at", ""))
                        doc = self._format_issue_to_document(repo, issue)
                        discovered_docs.append(doc)
                        if i_updated > highest_watermark:
                            highest_watermark = i_updated

        new_state = ConnectorSyncState(
            cursor=f"gh_{highest_watermark}",
            watermark=highest_watermark,
            last_sync_at=now_iso,
            metadata={"repo": repo, "synced_count": len(discovered_docs)},
        )
        return discovered_docs, new_state
