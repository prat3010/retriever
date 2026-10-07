# Architectural Dependency Rules & DAG Prerequisite Specifications

Governance Body: Prateeq Studio Architecture Review
Algorithmic Enforcement: Directed Acyclic Graph (DAG) Transitive Closure
Validation Scope: Client Scoping Lab, SOW Compiler, Automated Provisioning

---

## 1. Architectural Prerequisite Matrix

In modern cloud applications, high-level business capabilities cannot function in isolation. Attempting to deploy commerce without authentication or appointment booking without payment processing results in broken system states.

Prateeq Studio enforces architectural integrity via deterministic dependency rules:

| High-Level Module | Direct Dependencies (`dependsOn`) | Transitive Closure ($C(S)$) | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **`booking`** (Appointments) | `payments`, `auth` | `booking`, `payments`, `auth` | Client bookings require upfront deposit checkout (`payments`) and appointment management dashboard (`auth`). |
| **`commerce`** (E-Commerce Store)| `payments`, `auth` | `commerce`, `payments`, `auth` | Product purchases require gateway processing (`payments`) and order tracking / customer ledger (`auth`). |
| **`lms`** (Course Academy) | `payments`, `auth` | `lms`, `payments`, `auth` | Gated student courses require fee checkout (`payments`) and student lesson progression storage (`auth`). |
| **`crm`** (Lead Management) | `auth` | `crm`, `auth` | Private internal deal pipelines require user authentication and staff permission boundaries (`auth`). |
| **`migration`** (Legacy ETL) | None (Auto-included on legacy) | `migration` | Extracting legacy databases requires schema mapping directly to target PostgreSQL tables. |

---

## 2. Mathematical Formulation & Topological Traversal

The complete system catalog is modeled as a directed graph $G = (V, E)$, where:
- $V$ is the set of all available feature modules ($|V| = 18$).
- $E \subset V \times V$ is the set of directed dependency edges, where $(u, v) \in E$ denotes that module $u$ depends on module $v$.

### Transitive Closure Definition
For any arbitrary subset of requested client features $S \subseteq V$, the required execution set $C(S)$ is the transitive closure:
$$C(S) = S \cup \{ v \in V \mid \exists u \in S, u \rightsquigarrow v \}$$
where $u \rightsquigarrow v$ indicates a directed path from $u$ to $v$ in $G$.

Because $G$ is strictly acyclic ($\forall v \in V, v \not\rightsquigarrow v$), the modules can be ordered into a topological sequence:
$$\text{ord}: V \to \{1, 2, \dots, |V|\} \quad \text{such that } (u, v) \in E \implies \text{ord}(v) < \text{ord}(u)$$
This topological order guarantees that during development sprints, base primitives (Authentication, Payment Gateways) are architected and verified before dependent modules (Booking, E-Commerce, LMS) are wired.

---

## 3. Recommended Architecture Topology Archetypes

### Archetype 1: E-Commerce & Digital Storefront
- **Base Engine:** Tier 2 Multi-Page Web App (`multipage`) — ₹55,000 / $750
- **Compulsory Feature Set:**
  1. `commerce`: E-Commerce Storefront & Cart (₹75,000 / $1,000)
  2. `payments`: Payment Gateway Integration (₹45,000 / $600)
  3. `auth`: User Auth & Client Portal (₹25,000 / $350)
  4. `email`: Automated Transactional Receipts (₹15,000 / $200)
- **Total Investment:** ₹215,000 INR / $2,900 USD
- **Sprint Turnaround:** 2–3 Weeks

### Archetype 2: Booking & Appointment Scheduling Platform
- **Base Engine:** Tier 2 Multi-Page Web App (`multipage`) — ₹55,000 / $750
- **Compulsory Feature Set:**
  1. `booking`: Booking & Appointment Scheduling (₹50,000 / $700)
  2. `payments`: Payment Gateway Integration (₹45,000 / $600)
  3. `auth`: User Auth & Client Portal (₹25,000 / $350)
  4. `email`: Automated Email Confirmations (₹15,000 / $200)
- **Total Investment:** ₹190,000 INR / $2,600 USD
- **Sprint Turnaround:** 2–3 Weeks

### Archetype 3: Custom Enterprise AI & Vector RAG Platform
- **Base Engine:** Tier 3 Full-Stack SaaS MVP (`saas`) — ₹175,000 / $2,400
- **Compulsory Feature Set:**
  1. `ai_rag`: Private AI Knowledge Base & Hybrid Search (₹125,000 / $1,700)
  2. `auth`: User Auth & Client Portal (₹25,000 / $350)
  3. `admin`: Admin Dashboard & Role Access Control (₹75,000 / $1,000)
- **Total Investment:** ₹400,000 INR / $5,450 USD
- **Recommended Maintenance:** Premium AI SLA (₹35,000 / $475/mo)
- **Sprint Turnaround:** 3–4 Weeks

### Archetype 4: Online Course Academy & LMS Portal
- **Base Engine:** Tier 3 Full-Stack SaaS MVP (`saas`) — ₹175,000 / $2,400
- **Compulsory Feature Set:**
  1. `lms`: LMS & Online Course Player (₹85,000 / $1,150)
  2. `payments`: Payment Gateway Integration (₹45,000 / $600)
  3. `auth`: User Auth & Client Portal (₹25,000 / $350)
  4. `cms`: Headless Blog & Course Content CMS (₹30,000 / $400)
- **Total Investment:** ₹360,000 INR / $4,900 USD
- **Sprint Turnaround:** 3–4 Weeks

### Archetype 5: Internal Operations CRM & Command Center
- **Base Engine:** Tier 3 Full-Stack SaaS MVP (`saas`) — ₹175,000 / $2,400
- **Compulsory Feature Set:**
  1. `crm`: CRM & Lead Management Module (₹60,000 / $800)
  2. `admin`: Admin Dashboard & Analytics RBAC (₹75,000 / $1,000)
  3. `auth`: User Auth & Client Portal (₹25,000 / $350)
- **Total Investment:** ₹335,000 INR / $4,550 USD
- **Sprint Turnaround:** 3 Weeks
