---
id: Guide_Commercial_Billing_Integration
title: "Client Integration Guide: Multi-Gateway Commercial Billing (Stripe, Razorpay, PhonePe)"
tier: 4_api_gateway
platform: retriever
tags:
  - integrations/billing
  - payments/razorpay
  - payments/stripe
  - payments/phonepe
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Every payment webhook MUST verify cryptographic HMAC signatures before updating subscription state."
---

# Client Integration Guide: Multi-Gateway Commercial Billing (Stripe, Razorpay, PhonePe)

#integrations #billing #stripe #razorpay #phonepe #subscriptions #webhooks #retriever

> **End-to-end integration manual for multi-gateway SaaS checkout, subscription state synchronization, and HMAC webhook processing.**

---

## 1. Multi-Gateway Payment Flow

```mermaid
flowchart TD
    User([User in Pricing Section]) --> Geo{Geo-IP Currency Detection}
    Geo -->|India (INR)| RazorpayOrPhonePe[Razorpay / PhonePe Gateway]
    Geo -->|International (USD)| StripeGateway[Stripe Checkout Session]
    
    RazorpayOrPhonePe & StripeGateway --> CustomerPays[User Authorizes Transaction]
    CustomerPays --> Webhook[POST /v1/payments/webhook/{gateway}]
    
    Webhook --> VerifyHMAC{Verify Cryptographic HMAC}
    VerifyHMAC -->|Valid| Ledger[Record in Invoices Ledger & Upgrade Quota]
    VerifyHMAC -->|Invalid| Reject[400 Invalid Signature (Reject)]
```

---

## 2. Webhook Signature Verification Reference

### Razorpay HMAC Verification (Python)
```python
import hmac
import hashlib

def verify_razorpay_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    generated_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature_header)
```

---

## 🔗 Related Architecture & Cross-References
- [Payments API Specification](../api/payments.md)
- [Pricing Catalog Specification](../api/pricing.md)
- [Database Schema & Invoices](../infrastructure/database_and_schemas.md)
