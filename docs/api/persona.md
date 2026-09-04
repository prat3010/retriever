# REST API Reference: Visitor Persona & Lead Propensity Intelligence

**Base Path:** `/v1/ml`  
**Authentication:** Public / Tenant Session / Master Admin Key  
**Milestone:** 85 (Phase K)  
**Version:** `v0.70.0`  

---

## Overview

The Persona Intelligence API applies unsupervised machine learning (Scikit-Learn K-Means) and supervised propensity regression to classify anonymous visitor session telemetry into real-world buyer personas and score prospective B2B commercial leads for automated outreach prioritization.

---

## Endpoints

### 1. Classify Anonymous Visitor Session Telemetry

Clusters anonymous session dwell time, pageview distribution, and interaction density into standardized persona archetypes.

- **Method:** `POST`
- **Path:** `/v1/ml/classify-visitor`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "commercial_intent_ratio": 0.65,
    "credibility_intent_ratio": 0.15,
    "product_intent_ratio": 0.15,
    "content_intent_ratio": 0.05,
    "dwell_time_seconds": 185.0,
    "interaction_depth_score": 12.0
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "persona_category": "commercial_buyer",
    "confidence_score": 0.92,
    "intent_affinity": {
      "commercial": 0.65,
      "credibility": 0.15,
      "product": 0.15,
      "content": 0.05
    },
    "recommended_action": "Surface instant project scoping quote and calendar booking modal.",
    "cluster_id": 0
  }
  ```

#### Supported Persona Categories:
| Category | Primary Behavior | Recommended Conversion Action |
| :--- | :--- | :--- |
| `commercial_buyer` | High dwell on pricing, scoping, checkout | Highlight instant SOW generation & escrow deposit |
| `technical_evaluator` | High dwell on architecture, terminal, docs | Showcase 3D vector visualizer, Python REPL & GitHub code |
| `talent_recruiter` | High dwell on resume, certifications, case studies | Surface PDF resume export and LinkedIn/email links |
| `community_peer` | High dwell on blog posts, research writeups | Prompt newsletter signup or open-source repo stars |

---

### 2. Score Commercial Lead Propensity

Predicts conversion probability and priority tier for prospective B2B clients or autonomous outreach candidates based on company size, vertical, seniority, and budget.

- **Method:** `POST`
- **Path:** `/v1/ml/score-lead`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "company_size_tier": 3,
    "domain_vertical": "enterprise_saas",
    "role_seniority": "engineering_leadership",
    "tech_stack_affinity": 0.85,
    "budget_tier_usd": 75000.0,
    "is_remote": true
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "conversion_probability": 0.884,
    "priority_tier": "A+ High Value",
    "recommended_engagement_strategy": "Lead with enterprise multi-tenant RAG architecture and 7-day trial sandbox demo.",
    "key_scoring_drivers": [
      "Engineering leadership seniority with direct technical decision authority (+0.25)",
      "High tech stack affinity with Python/PostgreSQL/Vector architecture (+0.20)",
      "Enterprise budget tier exceeding $50k annual threshold (+0.18)"
    ]
  }
  ```

#### Priority Tier Bands:
- `A+ High Value`: Conversion probability $\ge 0.75$. Instant autonomous outreach dispatch and priority SDR alert.
- `B Qualified`: Conversion probability $\in [0.45, 0.75)$. Standard automated drip campaign with case studies.
- `C Low Priority`: Conversion probability $< 0.45$. Low-touch asynchronous nurture queue.
