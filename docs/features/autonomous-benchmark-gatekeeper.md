# Autonomous Continuous Benchmark & Regression Gatekeeper (Platform Battery #37)

## 1. Overview
The **Autonomous Continuous Benchmark & Regression Gatekeeper (Battery #37)** acts as the cognitive engine's automated quality guardrail. It prevents performance, accuracy, and groundedness regressions when new fine-tuned LoRA adapters (M120), vector sharding topologies (M117), prompt templates (M92), or embedding configurations are promoted into production.

Unlike conventional fixed-threshold CI assertions, the Gatekeeper leverages **Two-Sample Welch's t-test hypothesis testing** combined with **Information Retrieval (NDCG@K, MRR) and RAG Triad (Faithfulness, Relevance)** evaluations to differentiate statistically significant regressions ($p < \alpha$) from stochastic variance.

---

## 2. Mathematical Foundations

### 2.1. Normalized Discounted Cumulative Gain (NDCG@K)
For a query $q$ and rank cutoff $K$:
$$\text{DCG}@K = \sum_{i=1}^K \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}$$
Where $\text{rel}_i \in \{0, 1\}$ denotes binary ground-truth relevance of retrieved chunk $i$.

The ideal DCG ($\text{IDCG}@K$) places all ground truth chunks at the top ranks:
$$\text{IDCG}@K = \sum_{i=1}^{\min(|R|, K)} \frac{1}{\log_2(i + 1)}$$

Normalized score:
$$\text{NDCG}@K = \frac{\text{DCG}@K}{\text{IDCG}@K} \in [0.0, 1.0]$$

### 2.2. Mean Reciprocal Rank (MRR)
Measures the reciprocal rank of the first relevant document retrieved:
$$\text{MRR} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\text{rank}_q}$$
Where $\text{rank}_q$ is the 1-based index of the first relevant chunk ($0.0$ if no relevant chunk retrieved in top $K$).

### 2.3. RAG Triad Groundedness (Faithfulness)
Measures context attribution by evaluating the proportion of answer claims / substantive content tokens supported by the retrieved chunk contexts:
$$\text{Faithfulness} = \frac{|\text{Tokens}_{\text{Answer}} \cap \text{Tokens}_{\text{RetrievedContext}}|}{|\text{Tokens}_{\text{Answer}}|}$$

### 2.4. Two-Sample Welch's t-Test & p-Value
When comparing baseline distribution $X_1 \sim (N_1, \bar{X}_1, s_1^2)$ against candidate distribution $X_2 \sim (N_2, \bar{X}_2, s_2^2)$ under unequal variances:

$$t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\frac{s_1^2}{N_1} + \frac{s_2^2}{N_2}}}$$

Effective degrees of freedom $\nu$ is calculated via the **Welch–Satterthwaite equation**:
$$\nu = \frac{\left(\frac{s_1^2}{N_1} + \frac{s_2^2}{N_2}\right)^2}{\frac{(s_1^2 / N_1)^2}{N_1 - 1} + \frac{(s_2^2 / N_2)^2}{N_2 - 1}}$$

The two-tailed $p$-value represents the probability of observing a difference at least as extreme under the null hypothesis ($H_0: \mu_1 = \mu_2$):
$$p = 2 \cdot (1 - F(|t|; \nu))$$
If $p < \alpha$ (default $\alpha = 0.05$) and the delta indicates adverse performance, the regression is declared statistically significant.

---

## 3. Gatekeeper State Machine & Rollback

```
   ┌────────────────────────────────────────────────────────┐
   │            Benchmark Evaluation Triggered              │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │       Compute Empirical Metrics & Distributions        │
   │    (NDCG@K, MRR, Faithfulness, Latency P50/P95/P99)    │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │    Two-Sample Welch's t-Test vs Baseline Distribution  │
   │            (t-stat, Welch-Satterthwaite ν, p)          │
   └───────────────────────────┬────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
  [All Metrics Passed]    [Minor Delta /        [Significant Drop
   Δ within bounds         p ≥ α (Stochastic)]    p < α & Δ > threshold]
        │                      │                      │
        ▼                      ▼                      ▼
   PASSED_CLEAN         WARNING_DEGRADED       REJECTED_REGRESSION
 (Deploy Approved)     (Review Flagged)                │
                                                       ▼
                                            [Automated Rollback Signal]
                                            (Revert LoRA adapter / prompt)
```

---

## 4. API Endpoints

- `GET /v1/benchmarks/health`: Health status and registered mathematical engines.
- `GET /v1/tenants/{tenantId}/benchmarks/suites`: List all benchmark suites.
- `POST /v1/tenants/{tenantId}/benchmarks/suites`: Create a benchmark suite with customized SLA regression gates.
- `GET /v1/tenants/{tenantId}/benchmarks/runs`: Historical benchmark run ledger.
- `POST /v1/tenants/{tenantId}/benchmarks/runs`: Ingest or trigger an automated benchmark run.
- `POST /v1/tenants/{tenantId}/benchmarks/evaluate-gate`: Execute Welch's t-test and GatePolicy regression evaluation.
- `POST /v1/benchmarks/math/simulate`: Real-time mathematical simulation endpoint for statistical regression analysis.
