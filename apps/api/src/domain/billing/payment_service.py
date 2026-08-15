"""Domain service managing commercial payment processing, webhook verification, and tenant quota upgrades."""

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)

# SaaS Plan Quotas Mapping
PLAN_QUOTA_MAPPING = {
    "starter_inr": {"max_documents": 20, "tokens_per_minute": 50000, "requests_per_minute": 30},
    "starter_usd": {"max_documents": 20, "tokens_per_minute": 50000, "requests_per_minute": 30},
    "pro_inr": {"max_documents": 100, "tokens_per_minute": 150000, "requests_per_minute": 90},
    "pro_usd": {"max_documents": 100, "tokens_per_minute": 150000, "requests_per_minute": 90},
    "business_inr": {"max_documents": 500, "tokens_per_minute": 500000, "requests_per_minute": 300},
    "business_usd": {"max_documents": 500, "tokens_per_minute": 500000, "requests_per_minute": 300},
}


class PaymentService:
    """Processes commercial webhooks, verifies signatures, and provisions tenant quotas."""

    def __init__(self, payment_repository=None, tenant_registry=None) -> None:
        self.repo = payment_repository
        self.tenant_registry = tenant_registry

    def verify_signature(
        self, provider: str, payload_bytes: bytes, signature: str | None, secret: str
    ) -> bool:
        """Verify HMAC signature for incoming payment webhooks."""
        if not secret or secret == "dev_secret":
            # In dev mode without configured secret, allow testing
            return True

        if not signature:
            return False

        try:
            if provider == "stripe":
                # Stripe signature format: t=123,v1=abc
                parts = dict(pair.split("=") for pair in signature.split(",") if "=" in pair)
                timestamp = parts.get("t", "")
                expected_v1 = parts.get("v1", "")
                signed_payload = f"{timestamp}.{payload_bytes.decode('utf-8')}"
                computed = hmac.new(
                    secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(computed, expected_v1)

            elif provider in ("razorpay", "phonepe"):
                computed = hmac.new(
                    secret.encode("utf-8"), payload_bytes, hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(computed, signature)
        except Exception as err:
            logger.error(f"Signature verification error for provider '{provider}': {err}")
            return False

        return True

    async def process_payment_webhook(
        self, provider: str, payload: dict[str, Any], tenant_id_override: str | None = None
    ) -> dict[str, Any]:
        """Process validated payment payload, log to transaction ledger, and upgrade tenant quotas."""
        meta = payload.get("metadata", {})
        tenant_id = tenant_id_override or meta.get("tenant_id") or payload.get("tenant_id")

        if not tenant_id:
            logger.warning("Payment webhook missing tenant_id in payload metadata.")
            return {"status": "ignored", "reason": "missing_tenant_id"}

        event_type = payload.get("event") or payload.get("type") or "payment.succeeded"
        amount = float(payload.get("amount", 0.0))
        currency = payload.get("currency", "INR").upper()
        ext_ref = payload.get("id") or payload.get("payment_id") or payload.get("subscription_id")
        plan_id = meta.get("plan_id") or payload.get("plan_id")

        tx_record = {}
        if self.repo:
            tx_record = await self.repo.save_transaction(
                tenant_id=tenant_id,
                provider=provider,
                event_type=event_type,
                amount=amount,
                currency=currency,
                status="completed",
                external_reference=ext_ref,
                metadata=meta,
            )

        # Provision / upgrade tenant quotas if event indicates successful payment or subscription
        is_success = any(
            kw in event_type.lower()
            for kw in ("completed", "succeeded", "charged", "created", "active", "payment.succeeded")
        )
        if is_success and plan_id and plan_id in PLAN_QUOTA_MAPPING and self.tenant_registry:
            try:
                config = await self.tenant_registry.get_config(tenant_id)
                if config:
                    quota_updates = PLAN_QUOTA_MAPPING[plan_id]
                    config.quota_settings.max_documents = quota_updates["max_documents"]
                    config.rate_limits.tokens_per_minute = quota_updates["tokens_per_minute"]
                    config.rate_limits.requests_per_minute = quota_updates["requests_per_minute"]
                    await self.tenant_registry.save_config(tenant_id, config)
                    logger.info(f"Upgraded tenant '{tenant_id}' quotas for plan '{plan_id}'.")
            except Exception as err:
                logger.error(f"Failed to update tenant quotas for '{tenant_id}' ({err}).")

        return {
            "status": "processed",
            "tenant_id": tenant_id,
            "transaction": tx_record,
            "event_type": event_type,
        }

    def create_checkout_session(
        self,
        tenant_id: str,
        plan_id: str,
        currency: str = "INR",
        success_url: str = "https://prateeq.in/dashboard",
        cancel_url: str = "https://prateeq.in/rag",
    ) -> dict[str, Any]:
        """Generate hosted checkout session metadata."""
        plan_info = PLAN_QUOTA_MAPPING.get(plan_id, {"max_documents": 20})
        checkout_id = f"cs_test_{hashlib.md5(f'{tenant_id}:{plan_id}'.encode()).hexdigest()[:12]}"

        return {
            "checkout_session_id": checkout_id,
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "currency": currency,
            "quota_features": plan_info,
            "checkout_url": f"https://checkout.stripe.com/c/pay/{checkout_id}",
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
