"""Slack Web API Data Connector for Channels, Conversations, and Threads."""
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


class SlackConnector(BaseConnector):
    """Production-grade Slack connector interfacing with Slack Web API.

    Supports:
    - Ingesting messages and threaded discussions from specified channels.
    - Thread synthesis into unified markdown conversation documents.
    - Incremental sync using Slack message timestamp cursors (`ts`).
    """

    SLACK_API_BASE = "https://slack.com/api"

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="slack",
            name="Slack Workspace & Threads",
            description="Ingests channel discussions, messages, and thread replies with incremental timestamp tracking.",
            icon="slack",
            supports_incremental=True,
            required_parameters=["bot_token", "channels"],
            optional_parameters={
                "include_replies": True,
                "batch_limit": 100,
            },
        )

    def _get_headers(self, config: ConnectorConfig) -> dict[str, str]:
        cfg = config.configuration
        token = cfg.get("bot_token") or cfg.get("access_token", "")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        """Validate Slack bot token using auth.test."""
        cfg = config.configuration
        if cfg.get("offline_sandbox", False):
            return True

        token = cfg.get("bot_token") or cfg.get("access_token")
        if not token:
            return False

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    f"{self.SLACK_API_BASE}/auth.test",
                    headers=self._get_headers(config),
                )
                data = res.json()
                return bool(data.get("ok", False))
        except Exception as exc:
            logger.warning("Slack credential validation error: %s", exc)
            return False

    def _format_thread_to_document(
        self,
        channel_id: str,
        message: dict[str, Any],
        replies: list[dict[str, Any]],
    ) -> DiscoveredDocument:
        """Format Slack conversation thread into structured markdown document."""
        ts = message.get("ts", "0")
        user = message.get("user", "unknown_user")
        text = message.get("text", "")

        try:
            readable_time = datetime.fromtimestamp(float(ts), tz=UTC).isoformat()
        except Exception:
            readable_time = ts

        lines = [
            f"# Slack Conversation — Channel `{channel_id}`",
            f"- **Timestamp**: `{readable_time}` (`{ts}`)",
            f"- **Author**: `@{user}`",
            "",
            "## Message",
            "",
            text,
        ]

        if replies:
            lines.extend([
                "",
                "## Thread Replies",
                "",
            ])
            for reply in replies:
                r_user = reply.get("user", "user")
                r_text = reply.get("text", "")
                r_ts = reply.get("ts", "")
                try:
                    r_time = datetime.fromtimestamp(float(r_ts), tz=UTC).strftime("%H:%M:%S UTC")
                except Exception:
                    r_time = r_ts
                lines.append(f"- **@{r_user}** ({r_time}): {r_text}")

        content = "\n".join(lines)
        clean_ts = ts.replace(".", "_")
        filename = f"slack_{channel_id}_{clean_ts}.md"

        return DiscoveredDocument(
            filename=filename,
            content=content,
            mime_type="text/markdown",
            source_url=f"slack://channel/{channel_id}?ts={ts}",
            metadata={
                "source": "slack",
                "channel_id": channel_id,
                "ts": ts,
                "author": user,
                "reply_count": len(replies),
                "timestamp": readable_time,
            },
        )

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        """Fetch all documents without prior cursor."""
        docs, _ = await self.fetch_incremental(config, ConnectorSyncState())
        return docs

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        """Fetch messages sent after watermark timestamp cursor."""
        cfg = config.configuration
        channels = cfg.get("channels", [])
        if isinstance(channels, str):
            channels = [c.strip() for c in channels.split(",") if c.strip()]

        include_replies = bool(cfg.get("include_replies", True))
        watermark = state.watermark or "0"
        highest_watermark = watermark
        discovered_docs: list[DiscoveredDocument] = []
        now_iso = datetime.now(UTC).isoformat()

        # Offline sandbox / mock support
        if cfg.get("offline_sandbox", False) or cfg.get("mock_messages"):
            mock_msgs = cfg.get("mock_messages", {})
            for ch in channels:
                msgs = mock_msgs.get(ch, [])
                for m in msgs:
                    m_ts = str(m.get("ts", "0"))
                    if float(m_ts) > float(watermark):
                        replies = m.get("replies", []) if include_replies else []
                        doc = self._format_thread_to_document(ch, m, replies)
                        discovered_docs.append(doc)
                        if float(m_ts) > float(highest_watermark):
                            highest_watermark = m_ts

            new_state = ConnectorSyncState(
                cursor=f"slack_ts_{highest_watermark}",
                watermark=highest_watermark,
                last_sync_at=now_iso,
                metadata={"channels": channels, "messages_synced": len(discovered_docs)},
            )
            return discovered_docs, new_state

        # Live Slack Web API query
        headers = self._get_headers(config)
        async with httpx.AsyncClient(timeout=15.0) as client:
            for ch in channels:
                res = await client.get(
                    f"{self.SLACK_API_BASE}/conversations.history",
                    headers=headers,
                    params={"channel": ch, "oldest": watermark, "limit": 100},
                )
                if res.status_code != 200:
                    continue
                data = res.json()
                if not data.get("ok"):
                    continue

                for msg in data.get("messages", []):
                    m_ts = str(msg.get("ts", "0"))
                    replies = []
                    if include_replies and msg.get("reply_count", 0) > 0:
                        rep_res = await client.get(
                            f"{self.SLACK_API_BASE}/conversations.replies",
                            headers=headers,
                            params={"channel": ch, "ts": m_ts},
                        )
                        if rep_res.status_code == 200:
                            rep_data = rep_res.json()
                            if rep_data.get("ok"):
                                replies = rep_data.get("messages", [])[1:]  # Skip parent

                    doc = self._format_thread_to_document(ch, msg, replies)
                    discovered_docs.append(doc)
                    if float(m_ts) > float(highest_watermark):
                        highest_watermark = m_ts

        new_state = ConnectorSyncState(
            cursor=f"slack_ts_{highest_watermark}",
            watermark=highest_watermark,
            last_sync_at=now_iso,
            metadata={"channels": channels, "messages_synced": len(discovered_docs)},
        )
        return discovered_docs, new_state
