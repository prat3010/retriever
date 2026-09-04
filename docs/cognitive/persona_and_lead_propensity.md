# Cognitive Architecture Deep-Dive: Universal Visitor Persona Clustering & Lead Propensity

**Module:** Machine Learning & Behavioral Intelligence  
**Milestone:** 85 (Phase K)  
**Version:** `v0.70.0`  

---

## 1. Problem Definition & Strategic Objectives

Traditional web analytics tools (e.g. Google Analytics, Plausible) track pageviews and bounce rates in isolation, failing to provide actionable cognitive classification of **who** the visitor is and **what conversion leverage** should be applied in real time.

Retriever's Persona Intelligence engine solves this by:
1. Transforming raw, privacy-preserving session telemetry into a normalized feature vector.
2. Employing **Unsupervised K-Means Clustering** to categorize anonymous visitors into 4 core commercial archetypes.
3. Using a **Supervised Logistic Regression Propensity Scorer** to rank prospective commercial leads into actionable outreach priority bands ($A+, B, C$).

---

## 2. Mathematical Formulation: Visitor Telemetry Vector

Let an anonymous visitor session $S$ be represented by the 6-dimensional feature vector $\mathbf{x} \in \mathbb{R}^6$:

$$\mathbf{x} = \begin{bmatrix} r_{\text{comm}} \\ r_{\text{cred}} \\ r_{\text{prod}} \\ r_{\text{cont}} \\ \tilde{t}_{\text{dwell}} \\ \tilde{d}_{\text{inter}} \end{bmatrix}$$

Where:
- $r_{\text{comm}} \in [0, 1]$: Commercial intent ratio (dwell time on `/scoping`, `/pricing`, `/dashboard/checkout`).
- $r_{\text{cred}} \in [0, 1]$: Credibility intent ratio (dwell time on `/resume`, `/certificates`, case studies).
- $r_{\text{prod}} \in [0, 1]$: Product intent ratio (dwell time on `/rag`, `/rag/app`, `/terminal`).
- $r_{\text{cont}} \in [0, 1]$: Content intent ratio (dwell time on `/blog`, research articles).
- $\tilde{t}_{\text{dwell}} = \min(1.0, \frac{t_{\text{dwell}}}{600})$: Normalized dwell time (capped at 10 minutes).
- $\tilde{d}_{\text{inter}} = \min(1.0, \frac{N_{\text{interactions}}}{25})$: Normalized interaction depth (terminal commands, feature card toggles, sliders).

### Persona Clustering via K-Means
Given $K=4$ cluster centroids $\boldsymbol{\mu}_k \in \mathbb{R}^6$ calibrated across historical session distributions:

$$k^* = \arg\min_{k \in \{0, 1, 2, 3\}} \|\mathbf{x} - \boldsymbol{\mu}_k\|_2$$

The cluster assignment $k^*$ maps directly to canonical personas:
- $\boldsymbol{\mu}_0$: **Commercial Buyer** (dominated by $r_{\text{comm}} \ge 0.50$).
- $\boldsymbol{\mu}_1$: **Technical Evaluator** (dominated by $r_{\text{prod}} \ge 0.40$).
- $\boldsymbol{\mu}_2$: **Talent Recruiter** (dominated by $r_{\text{cred}} \ge 0.45$).
- $\boldsymbol{\mu}_3$: **Community Peer** (dominated by $r_{\text{cont}} \ge 0.40$).

The confidence score is computed from the normalized Euclidean distance to the winning centroid:
$$\text{Confidence}(\mathbf{x}) = \frac{1}{1 + \|\mathbf{x} - \boldsymbol{\mu}_{k^*}\|_2}$$

---

## 3. Lead Conversion Propensity Scorer

For structured B2B outbound prospects (from LinkedIn, GitHub, or inbound RFP inquiries), the lead feature vector $\mathbf{z} \in \mathbb{R}^d$ includes:
- Company size tier $s \in \{1, \dots, 5\}$
- Seniority weight $w_{\text{role}} \in [0.1, 1.0]$ (`founder_cxo` = 1.0, `eng_lead` = 0.85, etc.)
- Tech stack affinity $\alpha_{\text{tech}} \in [0, 1]$ (overlap with Python/PostgreSQL/Vector stack)
- Budget tier log-ratio: $\tilde{b} = \log_{10}(\max(1000, B_{\text{USD}})) / 6.0$

The conversion probability $P(\text{Convert} \mid \mathbf{z})$ is calculated via logistic sigmoid:

$$P(\text{Convert} \mid \mathbf{z}) = \sigma(\mathbf{w}^T \mathbf{z} + b) = \frac{1}{1 + e^{-(\mathbf{w}^T \mathbf{z} + b)}}$$

### Priority Tier Classification:
$$\text{Tier}(\mathbf{z}) = \begin{cases} \text{"A+ High Value"} & \text{if } P \ge 0.75 \\ \text{"B Qualified"} & \text{if } 0.45 \le P < 0.75 \\ \text{"C Low Priority"} & \text{if } P < 0.45 \end{cases}$$

---

## 4. Architectural Isolation

Under Retriever's Hexagonal Boundary rules:
- Pure abstractions reside in `src/domain/abstractions/persona_classifier.py` (`0` framework dependencies).
- Concrete Scikit-Learn training, inference, and fallback heuristics reside in `src/adapters/ml/scikit_persona_classifier.py`.
- Cold-start resilience: If Scikit-Learn is missing or models are uninitialized, the adapter automatically executes deterministic mathematical vector distance heuristics with zero downtime.
