# Executive Engineering Dossier & Professional Background

Candidate Name: Prateek Sharma (Prateeq)
Professional Title: Forward Deployed AI Engineer & Solutions Architect
Primary Contact Email: prateeqsharma@gmail.com
Direct Telephone: +91 9050433260
Physical Base: New Delhi, India (Operating Remotely Worldwide)
Primary Portfolio URL: https://prateeq.in
Cognitive RAG Platform: https://rag.prateeq.in
GitHub Organization: https://github.com/prat3010
LinkedIn Profile: https://linkedin.com/in/freshlimevodka

---

## 1. Professional Overview & Engineering Philosophy

Prateek Sharma is a Forward Deployed AI Engineer and Solutions Architect specializing in production-grade Retrieval-Augmented Generation (RAG) engines, PostgreSQL Row-Level Security (RLS) multi-tenancy, deterministic CPQ scoping compilers, and high-performance full-stack web platforms. 

### Core Engineering Principles
1. **The Ponytail Principle (Simplicity & YAGNI):** The simplest solution that completely solves the problem is strictly superior. Codebases must avoid speculative abstractions, unnecessary dependency sprawl, and simulated mock toys. Deletion of redundant layers is favored over unnecessary accumulation.
2. **Production Truth (Zero Fakes):** Every user-facing control, telemetry counter, and API endpoint connects directly to authentic backend infrastructure. If an external service or key is absent, the system fails cleanly with an informative diagnostic error rather than presenting synthetic mock data.
3. **Database-Enforced Multi-Tenancy:** Tenant isolation must never rely on fragile application-level `WHERE` clauses. Security boundaries are anchored directly into PostgreSQL connection session variables (`tenant_session`) and verified via Row-Level Security policies.
4. **Autonomous Client Enablement:** Commercial technical discovery should be self-service and deterministic. Client requirements are modeled as directed acyclic graphs (DAGs), compiling directly into transparent cost estimates, binding Statement of Work (SOW) documents, and automated deployment pipelines.

---

## 2. Core Competency & Systems Leadership Matrix

| Engineering Domain | Primary Technologies & Tooling | Production Implementations | Proficiency Level | Verification Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Cognitive RAG & Search** | Python 3.13, pgvector, Ollama (`nomic-embed-text`), ColBERT MaxSim, BM25, Redis | Retriever Cognitive Engine (`rag.prateeq.in`), hybrid reciprocal rank fusion, sub-25ms semantic caching | Expert / Architect | Automated Pytest harness, DeepEval validation |
| **Frontend Architecture** | Next.js 16 (App Router), React 19, TypeScript, Framer Motion, CSS Modules, Lenis | `prateeq.in`, Scoping Studio, Client Dashboard, Systems Terminal | Expert / Lead | Lighthouse 98+, pinned React-PDF compilers |
| **Database & Multi-Tenancy** | PostgreSQL 16, pgvector, Supabase BaaS, SQLAlchemy 2.0, Alembic, Redis | Tenant-isolated vector spaces, session-scoped RLS policies, audit ledgers | Expert / Lead | PostgreSQL RLS test suite, schema parity audits |
| **Security & Authentication** | PKCE OAuth 2.0, Supabase SSR Auth, JWT, Razorpay HMAC-SHA256, ReCAPTCHA v3 | Client Workspace session gate, tamper-proof invoice verification, API keys | Advanced | Cryptographic test mocks, session verification |
| **DevOps & Infrastructure** | Oracle Cloud Infrastructure (OCI VPS), Ubuntu 24.04, Docker, Nginx, Vercel | Zero-downtime Blue/Green symlink deployment, automated health rollback gates | Advanced | Live production services, automated CI/CD |
| **Developer Tooling & AST** | Python AST, Streamlit, Obsidian Canvas, Git Hooks, GitHub Actions CI/CD | PrateekSync developer cockpit (14 tabs), AST-driven architecture graph sync | Advanced | Zero-drift codebase audits, Obsidian topologies |

---

## 3. Commercial Engagement Economics & Delivery Models

Prateek operates on a transparent, milestone-governed engagement model with fixed-price deliverables to eliminate client billing surprises and scope ambiguity.

### Global & Domestic Pricing Structure
| Engagement Model | Duration / Scope | Rate (Global / USD) | Rate (Domestic / INR) | Key Deliverables & Commitments |
| :--- | :--- | :--- | :--- | :--- |
| **Hourly Advisory / Triage** | Ad-hoc / On-demand | $40 / hour | ₹3,000 / hour | Architectural consultation, bug root-cause analysis, security review |
| **Dedicated Day Rate** | 8 Hours Dedicated Sprint | $300 / day | ₹20,000 / day | Rapid prototyping, critical bug fixing, performance profiling |
| **AI Architecture Audit** | 60-Min Audit + Blueprint | $300 fixed | ₹20,000 fixed | Bottleneck analysis, cost/latency model, 3-page custom AI blueprint PDF |
| **Fixed-Price Milestones** | 1 to 4 Week Sprints | Per SOW Specification | Per SOW Specification | 50% deposit / 50% completion, guaranteed delivery, 30-day warranty |

### Commercial Governance Rules
- **Payment Split:** 50% upfront deposit to initiate development; 50% final balance upon staging sign-off prior to production DNS mapping.
- **Warranty:** All custom engagements include 30 days of complimentary post-launch technical support and bug warranty.
- **Turnaround Velocity:** Standard project delivery ranges from 1 to 3 weeks depending on engine tier and selected add-on modules.

---

## 4. Production Infrastructure & Deployment Topology

| System / Subsystem | Host Infrastructure | Network Domain | Role & Architectural Responsibilities |
| :--- | :--- | :--- | :--- |
| **Portfolio & Scoping Control Plane** | Vercel Serverless Edge | `https://prateeq.in` | Next.js 16 web app, client scoping wizard, interactive terminal, visitor analytics |
| **Retriever Cognitive Engine** | Oracle Cloud VPS (Ubuntu 24.04, 130.210.35.134) | `https://rag.prateeq.in` | FastAPI backend, pgvector storage, local Ollama embeddings, hybrid RRF search |
| **Retriever Admin Studio** | Vercel Deployment | `https://admin.rag.prateeq.in` | SaaS admin portal, tenant onboarding, document vector ingestion, telemetry |
| **Database & Telemetry Storage** | Supabase Enterprise Cloud | Managed PostgreSQL | Page visit telemetry, authenticated client workspaces, invoice ledger, blog posts |
