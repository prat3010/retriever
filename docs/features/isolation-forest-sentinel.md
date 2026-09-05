# Isolation Forest Telemetry Sentinel & Automated API Key Quarantine

**Milestone:** M83 (v0.68.0)  
**System Layer:** Unsupervised Anomaly Detection & Threat Defense (Platform Battery #8)  
**Architecture:** Scikit-Learn Isolation Forest + Multi-Dimensional Feature Extractor + Shannon Entropy Scorer + Dynamic Token Quarantine Trigger  

---

## 1. Executive Summary

Milestone 83 delivers **Platform Battery #8: `isolation_forest_sentinel`**, establishing autonomous, unsupervised threat detection across API traffic in Retriever.

Static threshold rate limiters (e.g. "max 100 requests per minute") fail to stop sophisticated automated attacks:
- Distributed scraping botnets that keep per-IP request rates below rate-limiting thresholds.
- Token exhaustion attacks that cycle through disparate IP addresses while querying resource-heavy endpoints.
- Credential stuffing and compromised tenant API keys exhibiting abrupt behavioral divergence.

Platform Battery #8 deploys an unsupervised Scikit-Learn Isolation Forest model operating continuously over real-time traffic feature vectors. Rather than modeling "normal" behavior, it isolates anomalous observations based on tree traversal depths. When a tenant's traffic pattern exhibits multi-dimensional anomalies (such as high query entropy combined with token burn spikes), the sentinel automatically quarantines the compromised API key and emits operational alerts.

---

## 2. Mathematical Foundation & Feature Space

The Sentinel extracts a 5-dimensional telemetry vector $x_i$ for every sliding time window:

$$x_i = \Big[ \text{velocity}, \text{token\_burn\_rate}, H(\text{query\_tokens}), \text{endpoint\_entropy}, \text{error\_ratio} \Big]$$

### 1. Shannon Token Entropy
Measures whether queries are natural human questions or automated algorithmic scans:

$$H(X) = - \sum_{j=1}^{K} p(w_j) \log_2 p(w_j)$$

- High entropy ($H > 0.82$) combined with uniform token distributions indicates randomized dictionary attacks or systematic corpus scraping.

### 2. Isolation Score Formulation
The anomaly score $s(x, n)$ for an instance $x$ in a dataset of $n$ instances is:

$$s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}}$$

Where:
- $h(x)$ is the path length (number of splits) required to isolate point $x$ in an Isolation Tree.
- $\mathbb{E}(h(x))$ is the average path length across all $n_{\text{estimators}} = 100$ trees.
- $c(n) = 2 \ln(n - 1) + 0.5772156649 - \frac{2(n-1)}{n}$ is the average path length of unsuccessful searches in a binary search tree.

```text
       Normal Points (Dense)                Anomalous Outlier
         (Requires Many Splits)            (Isolated in 1-2 Splits)
              ┌───┬───┐                             *
              │ • │ • │                            / \
              ├───┼───┤                           /   \
              │ • │ • │
```

When $s \to 1.0$ (short path length), the traffic pattern is flagged as an acute anomaly.

---

## 3. Quarantine Workflow & Automated Response

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SENTINEL ANOMALY RESPONSE PIPELINE                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Real-Time Request Stream ] ──► Window Aggregator (60s)                             │
│                                           │                                            │
│                                           ▼                                            │
│                               ┌───────────────────────┐                                │
│                               │ Feature Vector (5D)   │                                │
│                               └───────────┬───────────┘                                │
│                                           │                                            │
│                                           ▼                                            │
│                               ┌───────────────────────┐                                │
│                               │ Isolation Forest Model│                                │
│                               │ - 100 Isolation Trees │                                │
│                               │ - Contamination: 0.05 │                                │
│                               └───────────┬───────────┘                                │
│                                           │                                            │
│                    ┌──────────────────────┴──────────────────────┐                     │
│                    ▼ (Score < 0.65: Normal)                      ▼ (Score >= 0.65)     │
│             [ Allow Traffic ]                           ┌─────────────────┐            │
│                                                         │ Anomaly Trigger │            │
│                                                         └────────┬────────┘            │
│                                                                  │                     │
│                   ┌──────────────────────────────────────────────┴──────────────┐      │
│                   ▼                                                             ▼      │
│     ┌───────────────────────────┐                                 ┌──────────────────┐ │
│     │ Revoke / Quarantine Key   │                                 │ Emit Alert Event │ │
│     │ (403 KeyQuarantinedError) │                                 │ (SRE Webhook)    │ │
│     └───────────────────────────┘                                 └──────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/cognitive/anomaly_detector_adapter.py`
- **Repository:** `apps/api/src/adapters/database/anomaly_repository.py`
- **Model Parameters:**
  - `n_estimators`: 100
  - `contamination`: 0.05
  - `entropy_threshold`: 0.82
- **Latency Profile:** $\sim 4\text{ms}$ inference evaluation.
- **Health Check Endpoint:** `GET /v1/telemetry/sentinel/status`

---

## 5. Non-Negotiable Invariants

1. **Self-Healing Grace Period:** Quarantined keys carry a 15-minute administrative review window before permanent revocation.
2. **Deterministic Baseline:** Models are fitted on authenticated tenant training sets without cross-contaminating tenant profiles.
3. **Fail-Open Policy:** If the anomaly scoring pipeline encounters a database timeout, requests default to passing with an audit log rather than blocking legitimate tenant traffic.
