"""Native Slack Workspace Integration & Block Kit Service."""
import hashlib
import hmac
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SlackService:
    """Pure domain service managing Slack signature verification and Block Kit generation."""

    @staticmethod
    def verify_slack_signature(
        signing_secret: str,
        timestamp: str | None,
        signature: str | None,
        raw_body: bytes,
    ) -> bool:
        """Verify the cryptographic signature on an incoming Slack webhook.

        Format:
        basestring = 'v0:' + timestamp + ':' + raw_body
        expected = 'v0=' + HMAC-SHA256(secret, basestring)
        """
        if not signing_secret or not timestamp or not signature:
            return False

        # Protect against replay attacks (ignore if older than 5 minutes)
        try:
            req_time = int(timestamp)
            if abs(time.time() - req_time) > 300:
                logger.warning("Slack webhook rejected: timestamp too old (%s)", timestamp)
                return False
        except (ValueError, TypeError):
            return False

        sig_basestring = f"v0:{timestamp}:{raw_body.decode('utf-8', errors='replace')}".encode()
        computed_hash = hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring,
            hashlib.sha256,
        ).hexdigest()
        expected_sig = f"v0={computed_hash}"

        return hmac.compare_digest(expected_sig, signature)

    @staticmethod
    def build_slack_block_response(
        query: str,
        answer: str,
        citations: list[dict[str, Any]] | None = None,
        tenant_id: str = "default",
        duration_ms: float = 0.0,
    ) -> dict[str, Any]:
        """Construct an enterprise-grade Slack Block Kit interactive message."""
        citations = citations or []

        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔍 *Query:* _{query}_\n\n{answer}",
                },
            },
        ]

        # Add citation sources if present
        if citations:
            source_links: list[str] = []
            for i, c in enumerate(citations[:5], 1):
                title = c.get("title") or c.get("filename") or f"Document #{i}"
                url = c.get("source_url") or c.get("url") or "https://prateeq.in/rag/app"
                source_links.append(f"<{url}|*{title}*>")

            citation_text = " • ".join(source_links)
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📚 *Sources Consulted:*\n{citation_text}",
                    },
                }
            )

        # Context block with duration and tenant metadata
        duration_str = f"{duration_ms:.0f}ms" if duration_ms > 0 else "<50ms"
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⚡ Grounded by *Retriever AI* in {duration_str} • Tenant: `{tenant_id}`",
                    }
                ],
            }
        )

        # Interactive action buttons
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "👍 Helpful"},
                        "value": "feedback_positive",
                        "action_id": "btn_feedback_pos",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "👎 Inaccurate"},
                        "value": "feedback_negative",
                        "action_id": "btn_feedback_neg",
                        "style": "danger",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 Open in Studio"},
                        "url": f"https://prateeq.in/rag/app?tenant={tenant_id}",
                        "action_id": "btn_open_studio",
                    },
                ],
            }
        )

        return {
            "response_type": "in_channel",
            "blocks": blocks,
            "text": answer,  # Fallback notification text
        }
