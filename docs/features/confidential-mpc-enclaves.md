# Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves

> **Platform Battery:** #36 (`confidential_mpc_enclave`)  
> **Category:** `SAFETY_DEFENSE`  
> **Milestone:** M121 (`v2.0.0-alpha3`)  
> **Health Check Endpoint:** `GET /v1/mpc/health`  

---

## 1. Architectural Overview

The **Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves** engine enables collaborative cross-organization semantic search and vector similarity retrieval across sovereign enterprise consortiums **without disclosing raw vector embeddings, underlying text chunks, or query terms**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│             SOVEREIGN MULTI-PARTY CONSORTIUM ENCLAVE                   │
│                                                                        │
│   Hospital A (Party 1)         Research Lab B (Party 2)                │
│   [Query Vector q]             [Candidate Vectors d]                   │
│         │                               │                              │
│         ▼                               ▼                              │
│   Additive Share Gen           Additive Share Gen                      │
│   [q]_1 + [q]_2                [d]_1 + [d]_2                           │
├────────────────────────────────────────────────────────────────────────┤
│           BEAVER MULTIPLICATION TRIPLE PROTOCOL (PPIP)                 │
│                                                                        │
│   Correlated Random Triples: (a, b, c = a · b)                         │
│   Locally Mask: [Δx]_p = [x]_p - [a]_p,  [Δy]_p = [y]_p - [b]_p       │
│   Reconstruct Masked Offsets Δx, Δy across parties                     │
│   Compute Product Share:                                               │
│   [z]_p = [c]_p + Δx·[b]_p + Δy·[a]_p + (Δx·Δy if p==1 else 0)        │
│   Reconstruct Inner Product: ⟨q, d⟩ = Σ [z]_p                          │
├────────────────────────────────────────────────────────────────────────┤
│             THRESHOLD TOP-K FILTERING & PRIVACY BUDGET                 │
│                                                                        │
│   Cosine Similarity: cos(θ) = ⟨q, d⟩ / (||q|| · ||d||)                 │
│   Privacy Gate: If cos(θ) ≥ τ_privacy ──► Reveal in Top-K              │
│                 If cos(θ) < τ_privacy ──► Zero-Knowledge Suppression   │
│   Differential Privacy Budget Account: ε_consumed += ε_query           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Cryptographic & Mathematical Foundation

### 2.1 Additive Secret Sharing
Any continuous embedding vector $v \in \mathbb{R}^D$ is quantized into fixed-point integer space $\tilde{v} = \lfloor v \cdot 2^S \rceil$ where $S=16$ ($Q_{16.16}$).
For $N \ge 2$ sovereign parties, $N-1$ random shares $[v]_1, \dots, [v]_{N-1}$ are sampled uniformly from $[-\text{bound}, \text{bound}]$. The $N$-th share is:
$$[v]_N = \tilde{v} - \sum_{k=1}^{N-1} [v]_k$$
**Information-Theoretic Security**: Any coalition of up to $N-1$ curious or compromised parties learns zero information about $v$, as the marginal distribution of $N-1$ shares is statistically indistinguishable from uniform random noise.

### 2.2 Beaver Multiplication Triples for Secure Dot Product
To compute the scalar product of secret-shared coordinates $x \cdot y$ without disclosing $x$ or $y$:
1. Correlated triples $(a, b, c = a \cdot b)$ are pre-shared: $[a]_k, [b]_k, [c]_k$.
2. Parties compute $[\Delta x]_k = [x]_k - [a]_k$ and $[\Delta y]_k = [y]_k - [b]_k$.
3. Masked values $\Delta x = \sum_k [\Delta x]_k$ and $\Delta y = \sum_k [\Delta y]_k$ are published.
4. Each party calculates:
   $$[x \cdot y]_k = [c]_k + \Delta x \cdot [b]_k + \Delta y \cdot [a]_k + (\Delta x \cdot \Delta y \text{ if } k = 1 \text{ else } 0)$$
5. The sum of shares recovers the exact product:
   $$\sum_k [x \cdot y]_k = c + \Delta x \cdot b + \Delta y \cdot a + \Delta x \cdot \Delta y = (a + \Delta x)(b + \Delta y) = x \cdot y$$

### 2.3 Threshold Top-$K$ Filtering
To eliminate vector reconstruction attacks via repeated querying, candidate matches whose confidential cosine similarity falls below privacy threshold $\tau_{privacy}$ are suppressed without leaking their rank or score.

---

## 3. REST API Reference

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/v1/mpc/health` | Public | Battery #36 operational probe |
| `POST` | `/v1/tenants/{id}/mpc/sessions` | API Key | Create collaborative MPC enclave session |
| `GET` | `/v1/tenants/{id}/mpc/sessions` | API Key | List active/historical consortium sessions |
| `GET` | `/v1/tenants/{id}/mpc/sessions/{sid}` | API Key | Get session status and participating parties |
| `POST` | `/v1/tenants/{id}/mpc/sessions/{sid}/join` | API Key | Join session with public key as sovereign party |
| `POST` | `/v1/tenants/{id}/mpc/sessions/{sid}/shares` | API Key | Ingest additive vector shares |
| `POST` | `/v1/tenants/{id}/mpc/sessions/{sid}/compute` | API Key | Execute confidential Beaver inner product |
| `GET` | `/v1/tenants/{id}/mpc/sessions/{sid}/results` | API Key | Retrieve threshold Top-K matching items |
| `POST` | `/v1/tenants/{id}/mpc/sessions/{sid}/abort` | API Key | Terminate active MPC session |
| `POST` | `/v1/mpc/math/simulate` | Public | Interactive Beaver Triples & PPIP math evaluation |

---

## 4. Verification & Quality Invariants

- **Zero-Toy Invariant**: Real fixed-point quantization ($Q_{16.16}$), authentic Beaver multiplication algebraic expansion, and genuine Shannon entropy verification.
- **Hexagonal Isolation**: `src/domain/abstractions/mpc_enclave.py` has 0 framework imports.
- **Precision Error**: Numerical deviation from floating-point baseline $|\Delta| < 0.001$.
