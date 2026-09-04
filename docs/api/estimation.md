# REST API Reference: Project Effort & Sprint Delivery Estimation

**Base Path:** `/v1/scoping`  
**Authentication:** Public / Authenticated  
**Milestone:** 84 (Phase K)  
**Version:** `v0.69.0`  

---

## Overview

The Estimation API applies a Scikit-Learn regression model (`ScikitEffortRegressor`) trained on historical software engineering deliverables to calculate statistical engineering effort (P50/P90 hours), calendar delivery turnaround bounds, architectural complexity indices, and top risk contributors for a project scope.

---

## Endpoints

### 1. Estimate Scoping Timeline & Complexity

Takes selected architecture engines, feature modules, and design tiers, vectorizes their topological dependencies, and predicts empirical delivery bounds.

- **Method:** `POST`
- **Path:** `/v1/scoping/estimate-timeline`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "engine_id": "saas",
    "feature_ids": [
      "feat_auth_google",
      "feat_rag_vector_search",
      "feat_rag_stream_chat",
      "feat_razorpay_subscriptions",
      "feat_admin_rbac_deck"
    ],
    "brand_asset_id": "brand_design_system_2",
    "maintenance_plan_id": "care_enterprise_sla",
    "custom_notes": "Requires real-time streaming, vector RAG, and Razorpay subscription billing."
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "hours_p50": 38.5,
    "hours_p90": 52.0,
    "calendar_days_min": 7,
    "calendar_days_max": 14,
    "complexity_index": 3.85,
    "recommended_sprint_weeks": "1 to 2 Weeks Sprint",
    "confidence_score": 0.94,
    "top_effort_drivers": [
      {
        "feature_name": "feat_rag_vector_search",
        "category": "AI/RAG",
        "added_hours_estimate": 14.0,
        "risk_level": "medium"
      },
      {
        "feature_name": "feat_razorpay_subscriptions",
        "category": "Payments & Billing",
        "added_hours_estimate": 10.5,
        "risk_level": "medium"
      },
      {
        "feature_name": "feat_admin_rbac_deck",
        "category": "Admin & RBAC",
        "added_hours_estimate": 8.0,
        "risk_level": "low"
      }
    ],
    "risk_factors": [
      "Multi-tenant vector search requires pgvector HNSW index warmup and RLS enforcement.",
      "Webhook signature validation requires idempotent retry handlers to prevent duplicate billing."
    ]
  }
  ```

---

## Metric Definitions

| Field | Meaning | Mathematical Basis |
| :--- | :--- | :--- |
| `hours_p50` | Expected median engineering hours | Mean prediction $\mu$ from Scikit Gradient Boosting regressor |
| `hours_p90` | Risk-buffered conservative effort | $\mu + 1.28 \times \sigma$ (90th percentile of prediction interval) |
| `calendar_days_min` | Best-case turnaround | Derived from $H_{\text{P50}} / 6.0\text{h daily capacity}$, min 3 days |
| `calendar_days_max` | 95% SLA upper bound | Derived from $H_{\text{P90}} / 4.0\text{h daily effective throughput}$ |
| `complexity_index` | Architectural depth score (1.0–5.0) | Normalized DAG depth and subsystem entropy score |
