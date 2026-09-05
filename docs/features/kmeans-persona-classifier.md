# Zero-Cookie KMeans Persona Classifier & B2B Deal Propensity Scorer

**Milestone:** M85 (v0.70.0)  
**System Layer:** Machine Learning & Visitor Commercial Classification (Platform Battery #10)  
**Architecture:** Scikit-Learn KMeans Clustering + Balanced Logistic Regression + Client-Side Behavioral Telemetry Vectorizer  

---

## 1. Executive Summary

Milestone 85 establishes **Platform Battery #10: `kmeans_persona_classifier`**, delivering zero-cookie visitor intelligence and commercial intent scoring across Retriever and the portfolio.

Traditional marketing analytics rely on privacy-invasive third-party tracking cookies (Meta Pixel, Google Tag Manager, Clearbit). These approaches suffer from:
- Immediate breakage under modern privacy browsers (Safari ITP, Firefox Enhanced Tracking Protection, Brave).
- Severe GDPR/ePrivacy compliance liabilities.
- Zero mathematical connection between browsing behavior and actual B2B enterprise deal propensity.

Platform Battery #10 classifies visitors based entirely on client-side behavioral interactions (scroll depth, terminal commands executed, pricing engine modifications, case study inspection velocity, session duration) without collecting Personally Identifiable Information (PII). It clusters visitors into 4 commercial archetypes and predicts a normalized deal closure propensity score $P(\text{Deal}) \in [0.0, 1.0]$.

---

## 2. Mathematical Foundation & Dual-Stage ML Architecture

The classification pipeline operates in two stages:

### Stage 1: KMeans Unsupervised Cluster Discovery
Maps normalized telemetry vectors $X \in \mathbb{R}^7$ into 4 distinct commercial archetypes by minimizing within-cluster sum-of-squares (inertia):

$$\arg\min_{S} \sum_{i=1}^{k} \sum_{x \in S_i} \|x - \mu_i\|^2 \quad (k=4)$$

The 4 discovered archetypes are:
1. **Commercial Enterprise Buyer:** Heavy focus on `/scoping`, PDF pricing downloads, client dashboard tours, and SLA guarantees.
2. **Technical Recruiter / Headhunter:** Rapid visits to `/resume`, LinkedIn outbound clicks, certificate verification queries.
3. **Peer Engineer / Open-Source Evaluator:** High engagement with `/terminal` commands, architecture nodes, GitHub commits, and API schemas.
4. **Casual Browser / General Evaluator:** High bounce rate, short dwell time, surface-level hero scrolling.

### Stage 2: Balanced Logistic Regression (Deal Propensity)
Predicts the probability of the session generating a high-value commercial engagement ($y=1$):

$$P(y=1|x) = \sigma(w^\top x + b) = \frac{1}{1 + e^{-(w^\top x + b)}}$$

Trained with `class_weight='balanced'` to offset the natural class imbalance of commercial inquiries ($<2\%$ of total traffic).

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ZERO-COOKIE PERSONA CLASSIFICATION FLOW                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Client Session Telemetry (Zero PII) ]                                              │
│   - scroll_velocity, scoping_clicks, dwell_time_sec, terminal_queries, pdf_exports     │
│                            │                                                           │
│                            ▼                                                           │
│              ┌───────────────────────────┐                                             │
│              │ StandardScaler Transform  │ ──► [ -0.4, 2.1, 1.8, 0.0, 3.4 ... ]        │
│              └─────────────┬─────────────┘                                             │
│                            │                                                           │
│            ┌───────────────┴───────────────┐                                           │
│            ▼                               ▼                                           │
│   ┌───────────────────┐           ┌─────────────────────────────┐                      │
│   │ KMeans Model(k=4) │           │ Balanced Logistic Regressor │                      │
│   └────────┬──────────┘           └──────────────┬──────────────┘                      │
│            │                                     │                                     │
│            ▼                                     ▼                                     │
│   [ Archetype: BUYER ]             [ Deal Propensity: 0.89 ]                           │
│            │                                     │                                     │
│            └───────────────────┬─────────────────┘                                     │
│                                ▼                                                       │
│             ┌─────────────────────────────────────┐                                    │
│             │ Adaptive UX / Lead Priority Dispatch│                                    │
│             │ (Highlight Escrow SOW / Pre-Deposit)│                                    │
│             └─────────────────────────────────────┘                                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Details

- **Adapter:** `apps/api/src/adapters/ml/scikit_persona_classifier.py`
- **Domain Service:** `apps/api/src/domain/clustering/persona_service.py`
- **FastAPI Router:** `apps/api/src/routers/persona.py`
- **Active Parameters:**
  - `n_clusters`: 4
  - `random_state`: 42
  - `class_weight`: `"balanced"`
- **Latency Profile:** $\sim 3\text{ms}$ execution latency.
- **Health Check Endpoint:** `GET /v1/ml/classify-visitor`

---

## 4. Non-Negotiable Invariants & Privacy Guarantees

1. **Zero Raw IP / PII Retention:** Raw IP addresses are immediately hashed via daily rotating salt (`SHA256(ip + salt)`) before telemetry aggregation; no personal data is passed to the ML pipeline.
2. **Deterministic Archetype Labels:** Centroid indices are mapped deterministically to semantic archetypes to prevent label-switching across re-trainings.
3. **GDPR Exemption:** Because telemetry operates strictly on non-identifiable browser events without client cookies, it is exempt from cookie banner consent requirements.
