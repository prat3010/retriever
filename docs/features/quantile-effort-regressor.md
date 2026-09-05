# Quantile Gradient Boosting Effort & Timeline Regressor

**Milestone:** M84 (v0.69.0)  
**System Layer:** Machine Learning & Project Estimation (Platform Battery #9)  
**Architecture:** Scikit-Learn Gradient Boosting Regressor + Pinball Loss (Quantiles 0.1, 0.5, 0.9) + DAG Complexity Feature Extraction  

---

## 1. Executive Summary

Milestone 84 delivers **Platform Battery #9: `quantile_effort_regressor`**, bringing empirical, statistical certainty to software engineering effort and project timeline estimation.

Traditional CPQ (Configure, Price, Quote) engines rely on static heuristic tables or optimistic single-point estimates (e.g. "Feature X takes 4 days"). This creates commercial and delivery failure modes:
- Software engineering delivery distribution is intrinsically non-Gaussian (skewed right with long tails).
- Unforeseen integration dependencies and cascading technical scope create severe timeline blowouts.
- Clients receive arbitrary quotes with no probabilistic confidence intervals.

Platform Battery #9 trains three parallel Gradient Boosting Regressors using the asymmetric **Pinball Loss** function at $\alpha \in \{0.10, 0.50, 0.90\}$. Given an architectural scope DAG, it outputs a calibrated delivery band:
- **P10 (Optimistic):** Best-case timeline with zero architectural blockers.
- **P50 (Median):** Expected timeline for standard commercial execution.
- **P90 (High-Risk):** 90th-percentile conservative delivery ceiling accounting for upstream integration delays.

---

## 2. Mathematical Foundation & Pinball Loss Function

Standard Ordinary Least Squares (OLS) regression estimates the conditional mean $\mathbb{E}[Y|X]$ by minimizing squared errors. In contrast, Quantile Regression models the conditional quantile $Q_Y(\alpha|X)$ by minimizing the asymmetric **Pinball (Tilted) Loss** function $\mathcal{L}_\alpha$:

$$\mathcal{L}_\alpha(y, \hat{y}) = \begin{cases} 
\alpha (y - \hat{y}) & \text{if } y \ge \hat{y} \\ 
(1 - \alpha)(\hat{y} - y) & \text{if } y < \hat{y} 
\end{cases}$$

```text
       Loss L_α
          │          /  Slope = α (Underestimation penalty)
          │         /
          │        /
          │       /
   ───────┼──────/─────── Error (y - ŷ)
         /│
        / │
       /  │  Slope = (1 - α) (Overestimation penalty)
```

- For $\alpha = 0.50$: Penalties for over- and under-estimation are symmetric (median regression).
- For $\alpha = 0.90$: Underestimating project hours is penalized 9 times more heavily than overestimating, forcing the model to predict a robust upper bound.

---

## 3. DAG Feature Extraction Pipeline

The regressor ingests an architectural scope graph (nodes represent services/features; edges represent `dependsOn` relationships):

$$X = \Big[ |V|, |E|, \text{depth}_{\max}, \text{cyclomatic\_complexity}, \text{auth\_tier}, \text{third\_party\_integrations}, \text{custom\_ui\_flags} \Big]$$

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        QUANTILE EFFORT INFERENCE FLOW                                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Scope Configuration / Selected Features ]                                          │
│                        │                                                               │
│                        ▼                                                               │
│          ┌───────────────────────────┐                                                 │
│          │ DAG Feature Extractor     │ ──► [ Nodes=12, Edges=18, MaxDepth=4, Ext=3 ]   │
│          └─────────────┬─────────────┘                                                 │
│                        │                                                               │
│           ┌────────────┼────────────┐                                                  │
│           ▼ (α = 0.10) ▼ (α = 0.50) ▼ (α = 0.90)                                       │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐                                             │
│     │ GBR(0.1) │ │ GBR(0.5) │ │ GBR(0.9) │                                             │
│     └────┬─────┘ └────┬─────┘ └────┬─────┘                                             │
│          │            │            │                                                   │
│          ▼            ▼            ▼                                                   │
│     [ P10: 14d ] [ P50: 21d ] [ P90: 32d ]                                             │
│          │            │            │                                                   │
│          └────────────┼────────────┘                                                   │
│                       ▼                                                                │
│        ┌─────────────────────────────┐                                                 │
│        │ Calibrated Delivery Horizon │                                                 │
│        │ (21 days, [14d - 32d] 80% CI│                                                 │
│        └─────────────────────────────┘                                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/ml/scikit_effort_regressor.py`
- **Domain Service:** `apps/api/src/domain/estimation/effort_estimation_service.py`
- **Model Parameters:**
  - `quantiles`: `[0.1, 0.5, 0.9]`
  - `n_estimators`: 120
  - `max_depth`: 4
  - `loss`: `"quantile"`
- **Latency Profile:** $\sim 6\text{ms}$ inference latency.
- **Health Check Endpoint:** `GET /v1/ml/estimate-effort`

---

## 5. Non-Negotiable Invariants

1. **Monotonic Quantile Order:** The system asserts $P_{10} \le P_{50} \le P_{90}$. If quantile crossing occurs due to gradient step variance, monotonic sorting isotonic adjustments are applied.
2. **Zero Negative Estimates:** All estimated effort values are bounded from below by 1.0 engineering day.
3. **Reproducibility:** Random states for tree bootstrapping are pinned across production inference runs.
