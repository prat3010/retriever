"""Unit tests for Milestone 52: Commercial Payments & Deposit Billing."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.billing.payment_service import PaymentService
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: Signature Verification ──────────────────────────────────────

def test_verify_signature():
    """Verify HMAC signature validation for Stripe and Razorpay."""
    service = PaymentService()
    secret = "secret_key_123"
    payload = b'{"event":"payment.succeeded"}'

    # Dev fallback test
    assert service.verify_signature("stripe", payload, None, "dev_secret") is True

    # Valid Razorpay signature
    import hashlib
    import hmac
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert service.verify_signature("razorpay", payload, valid_sig, secret) is True

    # Invalid signature
    assert service.verify_signature("razorpay", payload, "invalid_sig", secret) is False


# ── 2. Unit Test: Webhook Processing & Tenant Quota Upgrade ───────────────────

@pytest.mark.asyncio
async def test_process_payment_webhook_upgrades_quota():
    """Verify processing a successful payment webhook logs to ledger and updates tenant quotas."""
    mock_repo = AsyncMock()
    mock_repo.save_transaction.return_value = {"transaction_id": "tx_123"}
    mock_registry = AsyncMock()
    mock_config = AsyncMock()
    mock_registry.get_config.return_value = mock_config

    service = PaymentService(payment_repository=mock_repo, tenant_registry=mock_registry)

    tenant_id = str(uuid.uuid4())
    payload = {
        "event": "payment.succeeded",
        "amount": 5999.0,
        "currency": "INR",
        "metadata": {"tenant_id": tenant_id, "plan_id": "pro_inr"},
    }

    res = await service.process_payment_webhook("razorpay", payload)

    assert res["status"] == "processed"
    mock_repo.save_transaction.assert_awaited_once()
    mock_registry.save_config.assert_awaited_once()
    assert mock_config.quota_settings.max_documents == 100


# ── 3. Unit Test: Checkout Session Generator ──────────────────────────────────

def test_create_checkout_session():
    """Verify checkout session generator returns valid checkout metadata."""
    service = PaymentService()
    tenant_id = str(uuid.uuid4())

    session_info = service.create_checkout_session(
        tenant_id=tenant_id,
        plan_id="pro_usd",
        currency="USD",
    )

    assert session_info["tenant_id"] == tenant_id
    assert session_info["plan_id"] == "pro_usd"
    assert "https://checkout.stripe.com/c/pay/" in session_info["checkout_url"]


# ── 4. Integration Test: Payments Router Endpoints ────────────────────────────

@patch("src.routers.payments.payment_repo.save_transaction", new_callable=AsyncMock)
@patch("src.routers.payments.payment_repo.list_transactions", new_callable=AsyncMock)
def test_payment_router_endpoints(mock_list_tx, mock_save_tx):
    """Verify checkout session API, webhook API, and admin ledger API."""
    mock_save_tx.return_value = {"transaction_id": "tx_test_123"}
    from src.adapters.api.security import verify_admin_key
    app.dependency_overrides[verify_admin_key] = lambda: True

    try:
        tenant_id = str(uuid.uuid4())

        # 1. Checkout Session Endpoint
        res_checkout = client.post(
            "/v1/payments/checkout-session",
            json={
                "tenant_id": tenant_id,
                "plan_id": "starter_inr",
                "currency": "INR",
            },
        )
        assert res_checkout.status_code == 200
        assert res_checkout.json()["tenant_id"] == tenant_id

        # 2. Webhook Endpoint Test (Dev mode)
        res_webhook = client.post(
            "/v1/payments/webhooks/razorpay",
            json={
                "event": "payment.succeeded",
                "amount": 1999.0,
                "metadata": {"tenant_id": tenant_id, "plan_id": "starter_inr"},
            },
        )
        assert res_webhook.status_code == 200
        assert res_webhook.json()["status"] == "processed"

        # 3. Admin Ledger Endpoint
        mock_list_tx.return_value = (
            [
                {
                    "transaction_id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "provider": "razorpay",
                    "event_type": "payment.succeeded",
                    "amount": 1999.0,
                    "currency": "INR",
                    "status": "completed",
                    "created_at": "2026-08-15T08:00:00Z",
                }
            ],
            1,
        )

        res_ledger = client.get(
            f"/v1/admin/tenants/{tenant_id}/payments/ledger",
            headers={"X-Admin-Master-Key": "test_key"},
        )
        assert res_ledger.status_code == 200
        body_ledger = res_ledger.json()
        assert body_ledger["total"] == 1
        assert len(body_ledger["items"]) == 1
    finally:
        app.dependency_overrides.clear()
