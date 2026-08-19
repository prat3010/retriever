import ipaddress
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def is_safe_webhook_url(url: str) -> bool:
    """Validate webhook URL to prevent SSRF against internal/private networks."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname = hostname.lower()
        if hostname in ("localhost", "loopback"):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


class N8nWebhookDispatcher:
    """Dispatches event triggers to external n8n automation webhooks."""

    async def dispatch_event(
        self, webhook_url: str, event_type: str, tenant_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Post event notification to external n8n webhook endpoint."""
        if not webhook_url or not is_safe_webhook_url(webhook_url):
            logger.warning(
                f"Blocked potential SSRF or invalid webhook URL '{webhook_url}' for tenant '{tenant_id}'."
            )
            return {"success": False, "reason": "invalid_or_unsafe_webhook_url"}

        event_payload = {
            "event": event_type,
            "tenant_id": tenant_id,
            "data": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook_url, json=event_payload)
                resp.raise_for_status()
                logger.info(
                    f"Successfully dispatched n8n event '{event_type}' for tenant '{tenant_id}'."
                )
                return {"success": True, "status_code": resp.status_code}
        except Exception as err:
            logger.error(
                f"Failed to dispatch n8n webhook for tenant '{tenant_id}' ({err})."
            )
            return {"success": False, "error": str(err)}
