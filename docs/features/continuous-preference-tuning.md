# Continuous DPO / ORPO Model Fine-Tuning Pipeline

> **Platform Battery:** #35 (`continuous_preference_tuning`)  
> **Category:** `ML_INTELLIGENCE`  
> **Milestone:** M120 (`v1.9.0-alpha2`)  
> **Health Check Endpoint:** `GET /v1/tuning/health`  

---

## 1. Architectural Overview

The **Continuous Preference Tuning Engine** establishes an autonomous closed-loop optimization system that harvests user feedback and continuously fine-tunes specialized domain models via Direct Preference Optimization (DPO) and Odds Ratio Preference Optimization (ORPO):

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   PREFERENCE HARVESTING BUFFER (👍 / 👎)               │
│                                                                        │
│   User Interaction ──► (x, y_w, y_l) ──► /v1/tenants/{tenant}/tuning/   │
│   Ratings & Edits      (Deduplication)   Buffer Auto-Trigger (e.g. 20) │
├────────────────────────────────────────────────────────────────────────┤
│                 CONTINUOUS DPO / ORPO OPTIMIZATION ENGINES             │
│                                                                        │
│   Objective Selection:                                                 │
│   1. DPO:  L_DPO  = -log σ( β · [ log(π_θ/π_ref)_w - log(π_θ/π_ref)_l ] )│
│   2. ORPO: L_ORPO = L_SFT + λ · L_odds                                 │
│   Output: Parameter-Efficient LoRA Adapter (r=16, α=32)                │
├────────────────────────────────────────────────────────────────────────┤
│               AUTOMATED VALIDATION GATE & ATOMIC ROLLBACK             │
│                                                                        │
│   Held-Out Validation Split (20%):                                     │
│   1. Val Accuracy >= 0.75  ──► Checkpoint Promoted to Active Serving   │
│   2. Val Accuracy < 0.75   ──► State: FAILED (Prevents Model Collapse) │
│   3. 1-Click Rollback      ──► Atomic Reversion to Prior Stable LoRA   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts & Mathematical Formulation

### 1. Direct Preference Optimization (DPO)
Under the Bradley-Terry implicit reward formulation:
$$r(x, y) = \beta \log \frac{\pi_\theta(y | x)}{\pi_{ref}(y | x)}$$

The reward margin between winning response $y_w$ and losing response $y_l$ is:
$$\Delta r = \beta \left[ \log \frac{\pi_\theta(y_w | x)}{\pi_{ref}(y_w | x)} - \log \frac{\pi_\theta(y_l | x)}{\pi_{ref}(y_l | x)} \right]$$

The loss is minimized via maximum likelihood:
$$\mathcal{L}_{DPO} = -\log \sigma(\Delta r) = \log(1 + e^{-\Delta r})$$

### 2. Odds Ratio Preference Optimization (ORPO)
ORPO removes the memory overhead of maintaining a frozen reference model in GPU VRAM:
$$\text{Odds}_\theta(y | x) = \frac{\pi_\theta(y | x)}{1 - \pi_\theta(y | x)}$$

$$\mathcal{L}_{ORPO} = \mathcal{L}_{SFT}(\theta) - \lambda_{ORPO} \cdot \log \sigma \left( \log \frac{\text{Odds}_\theta(y_w | x)}{\text{Odds}_\theta(y_l | x)} \right)$$

### 3. Automated Validation Gate & Rollback
- Automatically splits harvested dataset into 80% train / 20% validation splits.
- Rejects models that fail to achieve $\ge 75\%$ preference accuracy on the held-out split.
- Maintains historical checkpoints and supports 1-click zero-downtime hot swapping and rollbacks.

---

## 3. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/tuning/health` | Battery status, GPU acceleration, and supported objectives |
| `GET` | `/v1/tenants/{tenant_id}/tuning/config` | Retrieve tenant hyperparameters and active adapter ID |
| `PUT` | `/v1/tenants/{tenant_id}/tuning/config` | Update tuning config, learning rate, beta, and auto-trigger threshold |
| `GET` | `/v1/tenants/{tenant_id}/tuning/pairs` | Paginated preference buffer list |
| `POST` | `/v1/tenants/{tenant_id}/tuning/pairs` | Ingest preference pair (auto-triggers job if threshold reached) |
| `DELETE` | `/v1/tenants/{tenant_id}/tuning/pairs/{pair_id}` | Delete preference pair |
| `POST` | `/v1/tenants/{tenant_id}/tuning/jobs` | Trigger manual DPO or ORPO fine-tuning job |
| `GET` | `/v1/tenants/{tenant_id}/tuning/jobs` | List historical and active fine-tuning jobs |
| `GET` | `/v1/tenants/{tenant_id}/tuning/jobs/{job_id}` | Inspect job loss history and validation results |
| `POST` | `/v1/tenants/{tenant_id}/tuning/jobs/{job_id}/promote` | Hot-promote verified LoRA adapter checkpoint to active serving |
| `POST` | `/v1/tenants/{tenant_id}/tuning/rollback` | Atomic rollback to prior stable adapter checkpoint |
| `POST` | `/v1/tuning/math/simulate` | Interactive mathematical simulator for DPO/ORPO losses |
