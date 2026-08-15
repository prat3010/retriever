"""Commercial Payments, Webhooks, and Billing Router."""

import logging
from typing import Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import BaseModel

from src.adapters.api.security import verify_admin_key
from src.config import settings
from src.container import payment_repo, payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Payments"])


class CheckoutSessionRequest(BaseModel):
    tenant_id: str
    plan_id: str
    currency: Literal["INR", "USD"] = "INR"
    success_url: str = "https://prateeq.in/dashboard"
    cancel_url: str = "https://prateeq.in/rag"


@router.post(
    "/payments/checkout-session",
    status_code=status.HTTP_200_OK,
)
async def create_checkout_session(payload: CheckoutSessionRequest) -> Any:
    """Generate a hosted payment checkout session for client deposit or subscription upgrade."""
    return payment_service.create_checkout_session(
        tenant_id=payload.tenant_id,
        plan_id=payload.plan_id,
        currency=payload.currency,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )


@router.post(
    "/payments/webhooks/{provider}",
    status_code=status.HTTP_200_OK,
)
async def handle_payment_webhook(
    provider: str,
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    x_razorpay_signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    x_verify: str | None = Header(None, alias="X-VERIFY"),
) -> Any:
    """Receive and verify cryptographically signed webhooks from Stripe, Razorpay, or PhonePe."""
    payload_bytes = await request.body()
    signature = stripe_signature or x_razorpay_signature or x_verify

    # Retrieve secret configuration for provider
    secret = getattr(settings, f"{provider.upper()}_WEBHOOK_SECRET", "dev_secret")

    # Verify signature
    is_valid = payment_service.verify_signature(
        provider=provider,
        payload_bytes=payload_bytes,
        signature=signature,
        secret=secret,
    )
    if not is_valid:
        logger.warning(f"Invalid webhook signature for provider '{provider}'.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        payload_json = await request.json()
    except Exception:
        payload_json = {}

    result = await payment_service.process_payment_webhook(
        provider=provider,
        payload=payload_json,
    )
    return result


@router.get(
    "/admin/tenants/{tenantId}/payments/ledger",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def get_tenant_payment_ledger(
    tenantId: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Any:
    """Retrieve audit-proof transaction ledger for a tenant (Admin only)."""
    items, total = await payment_repo.list_transactions(tenantId, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}
