"""Domain service for dispatching outbound n8n webhook notifications for workflow automation events."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class N8nWebhookDispatcher:
    """Dispatches event triggers to external n8n automation webhooks."""

    async def dispatch_event(
        self, webhook_url: str, event_type: str, tenant_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Post event notification to external n8n webhook endpoint."""
        if not webhook_url:
            return {"success": False, "reason": "empty_webhook_url"}

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
