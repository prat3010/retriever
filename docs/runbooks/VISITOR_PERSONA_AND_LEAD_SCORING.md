# Operational Runbook: Visitor Persona Clustering & Lead Conversion Propensity Engine

**Document Status:** Production-Ready  
**Milestone:** 85 (v0.70.0)  
**Target Audience:** Commercial Operations, Sales Engineers, Growth Teams & Platform Administrators  

---

## 1. Commercial Objective: Autonomous Lead Qualification

In developer portfolios and B2B SaaS platforms, raw traffic numbers are vanity metrics. Out of 10,000 monthly visitors, 90% may be students or casual readers, while 20 visitors represent enterprise engineering leaders with substantial software budgets.

The **Retriever Persona Intelligence Engine (`apps/api/src/domain/intelligence/`)** bridges technical telemetry with sales execution by:
1. **Clustering Anonymous Visitors into 4 Commercial Archetypes** via unsupervised Machine Learning (`KMeans`).
2. **Predicting Lead Conversion Propensity ($0.0 - 1.0$)** via supervised scoring based on high-intent conversion signals.
3. **Dispatching High-Intent Leads** to the Autonomous Outreach Queue and local Streamlit Synchronizer cockpit.

---

## 2. Unsupervised KMeans Persona Clustering

The clustering engine maps session interactions into a normalized 8-dimensional feature vector:

$$\mathbf{x} = \big[\text{scroll\_depth},\; \text{terminal\_usage},\; \text{pricing\_views},\; \text{scoping\_interactions},\; \text{docs\_reads},\; \text{duration},\; \text{rfp\_uploads},\; \text{partner\_clicks}\big]$$

```text
                                [Visitor Telemetry]
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     StandardScaler Feature Vector     │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │          Scikit-Learn KMeans          │
                     │             (k=4 Clusters)            │
                     └───────────────────┬───────────────────┘
                                         │
         ┌───────────────────┬───────────┴───────────┬───────────────────┐
         │                   │                       │                   │
         ▼                   ▼                       ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Developer /   │ │   Enterprise    │ │    Agency /     │ │    Student /    │
│     Builder     │ │      Buyer      │ │    Partner      │ │ Casual Explorer │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### The 4 Commercial Archetypes:

| Archetype | Primary Behavioral Signals | Commercial Value | Recommended Next Step |
| :--- | :--- | :--- | :--- |
| **`Enterprise Buyer`** | Scoping wizard completions, pricing customization, SLA & compliance page visits, RFP uploads. | **Highest (\$5k - \$50k+ SOWs)** | Immediate direct meeting outreach; provision 7-day dedicated trial tenant. |
| **`Developer / Builder`** | `/terminal` CLI usage, GitHub repository link clicks, API docs reading, sandbox prompt tests. | High (Product advocacy & bottoms-up adoption) | Offer Developer Console API keys; invite to Open Source GitHub repository. |
| **`Agency / Partner`** | Middleman commission calculator visits, Sales Partner Agreement PDF downloads. | High (Recurring commission pipeline) | Dispatch automated Middleman Partnership Agreement packet. |
| **`Student / Explorer`** | Blog reading, snake game playing in terminal, high bounce rate, short dwell time. | Low commercial intent | Passive engagement; newsletter signup. |

---

## 3. Supervised Lead Conversion Propensity Scorer

For any visitor who interacts with the Scoping Lab or contact form, the Propensity Scorer calculates a continuous probability $P(\text{conversion}) \in [0.0, 1.0]$:

### Key Weighted Conversion Signals:
- **`uploaded_rfp_pdf`:** $+0.35$ (Explicit project requirements ready).
- **`customized_scoping_architecture`:** $+0.25$ (Interactive architecture drawer configuration).
- **`checked_pricing_calculator`:** $+0.15$ (Commercial budget consciousness).
- **`requested_proposal_pdf`:** $+0.15$ (Formal executive approval packet generated).
- **`authenticated_via_google_oauth`:** $+0.20$ (Verified corporate identity).

### Action Tiers:
```text
Score >= 0.75  ──> 🔴 HOT LEAD: Immediate alert pushed to Streamlit Synchronizer; auto-provision trial tenant.
0.40 - 0.74    ──> 🟡 WARM LEAD: Queued for Autonomous AI personalized email follow-up.
Score < 0.40   ──> ⚪ COLD / CASUAL: Standard analytics logging; no outbound dispatch.
```

---

## 4. Programmatic REST APIs

### 1. Classify Visitor Persona
```bash
curl -X POST "https://rag.prateeq.in/v1/admin/intelligence/persona/classify" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "scroll_depth": 0.85,
    "terminal_events": 12,
    "pricing_views": 3,
    "scoping_events": 18,
    "docs_reads": 4,
    "session_duration_s": 380,
    "rfp_uploaded": true,
    "partner_views": 0
  }'
```
**Sample Response:**
```json
{
  "archetype": "Enterprise Buyer",
  "confidence": 0.92,
  "cluster_id": 1,
  "actionable_insight": "Visitor exhibits deep scoping intent with technical validation. High probability enterprise prospect."
}
```

### 2. Score Lead Conversion Propensity
```bash
curl -X POST "https://rag.prateeq.in/v1/admin/intelligence/leads/score" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "rfp_uploaded": true,
      "quote_amount_usd": 12500,
      "email_domain_is_corporate": true,
      "visited_compliance": true
    }
  }'
```
**Sample Response:**
```json
{
  "propensity_score": 0.88,
  "tier": "HOT",
  "top_drivers": [
    {"signal": "rfp_uploaded", "impact": "+0.35"},
    {"signal": "corporate_email_domain", "impact": "+0.20"},
    {"signal": "compliance_inspection", "impact": "+0.15"}
  ]
}
```

---

## 5. Operations & Synchronization

Lead scores and persona classifications are continuously updated in Supabase table `outreach_leads` and viewable in:
1. **Local Streamlit Synchronizer:** Tab **Leads & Pipeline** (`sync_tabs/leads.py`).
2. **Master Admin Portal:** Route `/admin` on `prateeq.in`.
3. **Autonomous Outreach Queue:** Dispatches personalized outbound drafts for review before sending via Resend.
