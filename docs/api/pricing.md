---
id: Retriever_API_v1_pricing
title: "API Specification: Dynamic Pricing & Catalog Engine (/v1/pricing)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/pricing
  - commerce/catalog
  - platform/retriever
blast_radius: MEDIUM
security_auth: PUBLIC
invariants:
  - "Pricing figures MUST match single source of truth across INR and USD tiers."
---

# API Specification: Dynamic Pricing & Catalog Engine (`/v1/pricing`)

#api #pricing #catalog #plans #retriever

> **Authoritative specification for public SaaS tier pricing catalogs, currency resolution (INR/USD), and admin price overrides.**

---

## 1. Pricing Catalog Tiers

Retriever provides 3 standard multi-tenant subscription tiers:

| Tier ID | Plan Name | Monthly INR | Monthly USD | Document Quota | Token Quota / mo | Features Included |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `tier_starter` | **Starter** | ₹999 | $19 | 50 docs | 500,000 | Hybrid Search, BM25, Standard SSE |
| `tier_pro` | **Pro** | ₹2,999 | $49 | 500 docs | 5,000,000 | Hybrid Search, Reranking, GraphRAG, Citations |
| `tier_enterprise`| **Enterprise**| ₹9,999 | $149 | Unlimited | Unlimited | RLM REPL, Consensus Debate, Custom VPC |

---

## 2. API Endpoints

### 2.1 Get Public Pricing Plans

- **HTTP Method:** `GET`
- **Path:** `/v1/pricing`
- **Authentication:** Public
- **Query Parameters:** `currency` (`INR` or `USD`)
- **Response Schema (`200 OK`):**
```json
{
  "currency": "USD",
  "plans": [
    {
      "planId": "tier_starter",
      "name": "Starter",
      "price": 19,
      "billingPeriod": "monthly",
      "features": [
        "50 Documents",
        "500k Tokens / month",
        "Hybrid Search & Citations"
      ]
    },
    {
      "planId": "tier_pro",
      "name": "Pro",
      "price": 49,
      "billingPeriod": "monthly",
      "features": [
        "500 Documents",
        "5M Tokens / month",
        "GraphRAG & Neural Reranker"
      ]
    }
  ]
}
```

---

## 🔗 Related Architecture & Cross-References
- [Payments & Billing Specification](payments.md)
- [Commercial Billing Integration](../integrations/commercial_billing_integration.md)
