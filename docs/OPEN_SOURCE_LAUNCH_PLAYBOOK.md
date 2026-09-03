# Retriever — Open-Source Launch Playbook & Pre-Flight Manual

> **A Comprehensive Step-by-Step Blueprint for Decoupling, Packaging, Documenting, and Publicly Launching Retriever as an Elite Open-Source Cognitive RAG Platform.**
> 
> *Target Execution:* To be executed post-milestone completion when transitioning the repository from private to public.

---

## 🎯 Executive Summary & Positioning Strategy

Retriever's open-source release must not be perceived as "just another LangChain tutorial wrapper". The AI ecosystem is inundated with toy scripts that break in production.

### The Core Positioning Angle:
> **"The Developer's Batteries-Included, Multi-Tenant Cognitive RAG Platform on PostgreSQL."**
> 
> *Tired of paying $100+/mo for Pinecone, struggling with cross-tenant data leaks, and stitching together 10 different SaaS tools for reranking, OCR, and rate limiting? Retriever delivers a production-grade, self-hosted RAG platform featuring PostgreSQL Row-Level Security (RLS), ColBERT MaxSim late-interaction reranking, Docling OCR layout parsing, and built-in Scikit-Learn operational intelligence (anti-abuse anomaly sentinels, project effort regression, and zero-cookie visitor clustering) — completely free with zero-cost local Ollama embeddings.*

---

## 📋 The 6-Phase Pre-Flight Checklist

```text
[Phase 1: Decoupling & Sanitization] ──► [Phase 2: 3-Minute Docker Test] ──► [Phase 3: Documentation Overhaul]
                                                                                      │
[Phase 6: Career & Consulting Hub]  ◄── [Phase 5: Launch Distribution]  ◄── [Phase 4: Licensing & Community]
```

---

## 🔒 Phase 1: Codebase & Architecture Decoupling

Before making the repository public, every trace of private infrastructure, personal configurations, and sibling repository couplings must be eliminated.

### Checklist:
- [ ] **Zero Hardcoded Sibling Couplings:**
  - Audit all files for relative references to `../Prateek_website` or `Prateek_Ecosystem_Vault`.
  - Ensure `apps/api` and `apps/web` run completely standalone.
- [ ] **Decouple Domain URLs:**
  - Remove hardcoded `https://rag.prateeq.in` or `https://prateeq.in` defaults in source files; replace with configurable environment variables:
    ```env
    NEXT_PUBLIC_RETRIEVER_API_URL=http://localhost:8000
    RETRIEVER_PUBLIC_HOST=http://localhost:3000
    ```
- [ ] **Run Comprehensive Secret Scan:**
  - Execute secret audit script and verify zero credentials:
    ```bash
    python3 scripts/audit_secrets.py
    ```
  - Ensure `.env`, `*.pem`, `*.key`, `service_role_key`, and deployment server IPs (`DEPLOYMENT.md`) remain strictly in `.gitignore`.
- [ ] **AST Boundary Verification:**
  - Run architectural boundary tests to guarantee strict Hexagonal architecture:
    ```bash
    pytest apps/api/tests/test_architecture.py -v
    ```
- [ ] **Git History Scrub (If needed):**
  - Verify that past commits do not contain sensitive tokens in git history using `git log -S "secret"` or `trufflehog`.

---

## 🐳 Phase 2: The "3-Minute Developer Test" (Zero-Friction Packaging)

Developers judge open-source tools within the first 3 minutes of cloning. If setup requires manual configuration of 5 different services, 80% of developers abandon the repo.

### Checklist:
- [ ] **Unified `docker-compose.yml`:**
  - A single command must spin up all necessary infrastructure:
    1. **PostgreSQL 16** with `pgvector` pre-installed and auto-migrated.
    2. **Redis 7** for semantic caching and rate limiting.
    3. **Ollama** container with pre-pulled `nomic-embed-text` embedding model.
    4. **FastAPI Core Gateway** (`apps/api`).
    5. **Next.js Admin Studio** (`apps/web` - optional flag).
- [ ] **Automated First-Run Seeding:**
  - On first boot, the system must automatically create a default demo tenant (`tn_demo_workspace`) and emit a ready-to-use API key directly in the console output.
- [ ] **One-Line Copy-Paste Test:**
  - Test on a fresh, clean machine:
    ```bash
    git clone https://github.com/prat3010/retriever.git
    cd retriever
    docker compose up -d
    curl http://localhost:8000/health/readiness
    ```
  - Verification threshold: Response `{"status":"ready"}` in under 120 seconds.

---

## 📚 Phase 3: Documentation & User Manual Overhaul

Open-source developers don't read internal roadmaps or private milestone progress trackers. Documentation must be user-centric, polished, and actionable.

### Checklist:
- [ ] **Public `README.md` Polish:**
  - **Hero Badges:** CI/CD Build Status, Tests (617+ passing), Python 3.12, PostgreSQL 16, License (Apache 2.0), Docker Ready.
  - **1-Sentence Punchy Pitch:** Solves multi-tenancy, cost, and retrieval accuracy.
  - **Architecture Topology Diagram:** Clean ASCII or SVG diagram illustrating Hexagonal core, pgvector RLS, and ColBERT operator.
  - **Comparison Matrix:**
    | Capability | Retriever | Pinecone / Qdrant | LangChain Baseline | Dify / AnythingLLM |
    |:---|:---:|:---:|:---:|:---:|
    | **Self-Hosted On-Prem** | ✅ 1-Click Docker | ❌ Closed Cloud | ⚠️ Partial | ✅ Yes |
    | **Strict DB-Level Multi-Tenancy (RLS)** | ✅ Native Postgres | ⚠️ Namespace only | ❌ App code filter | ⚠️ Basic |
    | **ColBERT MaxSim Late-Interaction** | ✅ Built-in | ❌ Dense only | ❌ Complex setup | ❌ Cross-encoder only |
    | **Zero-Cost Embeddings** | ✅ Local Ollama | ❌ Paid API | ❌ Paid API | ⚠️ Configurable |
    | **Telemetry Anomaly Sentinel (M83)** | ✅ Isolation Forest | ❌ None | ❌ None | ❌ None |
    | **Effort & Timeline Regressor (M84)** | ✅ Quantile Gradient Boost | ❌ None | ❌ None | ❌ None |
    | **Zero-Cookie Visitor Clustering (M85)** | ✅ KMeans Intent ML | ❌ None | ❌ None | ❌ None |
    | **Presigned Citation Downloads** | ✅ S3/R2 Presigned | ❌ None | ❌ Custom code | ⚠️ Partial |
- [ ] **Comprehensive User Manual (`docs/USER_MANUAL.md`):**
  - Section 1: Quickstart & First Query (curl and Python SDK examples).
  - Section 2: Document Ingestion (PDF parsing, OCR, chunking algorithms).
  - Section 3: Hybrid Search & ColBERT Reranking API Guide.
  - Section 4: Multi-Tenancy & Workspace Isolation Configuration.
  - Section 5: Streaming Chat with SSE & Clickable Citations.
  - Section 6: Embedding the 1-Line Widget (`widget.js`) onto external websites.
  - Section 7: Telemetry Sentinel & Anomaly Detection Administration (M83).
  - Section 8: CPQ Software Effort & Timeline Confidence Estimator (M84).
  - Section 9: Zero-Cookie Visitor Intent Clustering & Lead Scorer (M85).
  - Section 10: Toggle Flags (`ENABLE_ML_MODULES=false`) for Pure-RAG Deployments.
- [ ] **Clean Public Roadmap (`ROADMAP.md`):**
  - Replace internal milestone logs with a forward-looking, developer-facing roadmap (e.g. GraphRAG v2, Multi-Modal Audio RAG, Kubernetes Operator Helm chart).

---

## ⚖️ Phase 4: Licensing & Community Standards

To ensure enterprise adoption and community contributions while protecting the core author, open-source governance must be configured.

### Checklist:
- [ ] **Adopt Apache 2.0 License:**
  - Add `LICENSE` file containing the standard Apache License 2.0.
  - *Rationale:* Enterprise-friendly, protects against patent litigation, allows commercial self-hosting while ensuring author credit.
- [ ] **Create `CONTRIBUTING.md`:**
  - Guidelines for setting up development virtual environment (`uv pip install`).
  - Running automated tests (`pytest apps/api/tests/`).
  - Formatting requirements (`ruff check --fix`).
  - PR submission and commit message conventions.
- [ ] **Create Community Templates (`.github/`):**
  - `.github/ISSUE_TEMPLATE/bug_report.md`
  - `.github/ISSUE_TEMPLATE/feature_request.md`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).

---

## 📢 Phase 5: The Public Launch Distribution Playbook

A great project dies in silence without targeted distribution. Launching requires coordinated technical storytelling across engineering communities.

### Channel 1: Hacker News ("Show HN")
- **Timing:** Tuesday or Wednesday at 8:00 AM EST (optimal front-page traction window).
- **Title Formula:**
  > `Show HN: Retriever – Self-hosted multi-tenant RAG platform with ColBERT, pgvector RLS & built-in ML intelligence`
- **Post Copy Structure:**
  1. *The Hook:* Why standard RAG fails in real production (tenant leakage, token costs, dense embedding blindness, lack of operational batteries).
  2. *The Solution:* How Retriever solves it at the database engine layer (PostgreSQL RLS), token level (ColBERT MaxSim), and operational intelligence layer (Scikit-Learn).
  3. *The Stack:* Python 3.12, FastAPI, PostgreSQL 16, pgvector, Ollama, Next.js 16.
  4. *Live Demo Link:* `https://rag.prateeq.in` + GitHub link.
  5. *Founder Engagement:* Stay in the comments for 6 hours answering deep technical questions about vector math, latency benchmarks, and memory usage.

### Channel 2: Twitter / X Technical Architecture Breakdown
- **Format:** 6-tweet technical visual thread with architecture diagrams and animated GIFs:
  - *Tweet 1:* The Hook + Short video/GIF showing 1-click Docker launch and streaming citation chat.
  - *Tweet 2:* Why PostgreSQL RLS beats application-level tenant filtering (with SQL snippet).
  - *Tweet 3:* How ColBERT MaxSim late-interaction finds exact code symbols and error IDs that cosine similarity misses.
  - *Tweet 4:* The built-in Scikit-Learn operational intelligence (Isolation Forest anomaly sentinel, timeline effort regression, zero-cookie visitor clustering).
  - *Tweet 5:* Benchmark stats: 631 automated tests, sublinear latency, zero OpenAI cost via local Ollama.
  - *Tweet 6:* GitHub repo link + call for stars and contributors.

### Channel 3: Targeted Reddit Communities
- **`r/LocalLLaMA`:** Focus on 100% private, self-hosted AI, local Ollama embeddings (`nomic-embed-text`), and zero API key requirements.
- **`r/selfhosted`:** Focus on the clean `docker-compose.yml`, multi-tenancy, and low resource footprint.
- **`r/Python`:** Focus on Hexagonal architecture, asyncpg, Celery queues, and clean domain abstractions.
- **`r/MachineLearning`:** Focus on the ColBERT MaxSim operator implementation and hybrid search fusion math.

### Channel 4: Awesome-Lists & Ecosystem PRs
- Submit pull requests adding Retriever to curated GitHub lists:
  - `awesome-rag`
  - `awesome-generative-ai`
  - `awesome-python`
  - `awesome-selfhosted`

---

## 💼 Phase 6: Inbound Career & Commercial Capture Engine

Open-sourcing Retriever is the ultimate professional leverage. The repository must be configured to convert GitHub traffic into high-paying opportunities.

### Checklist:
- [ ] **Author Attribution & Hiring Signal:**
  - Header in `README.md`:
    ```markdown
    Built with high-agency systems engineering by **[Prateek Sharma](https://prateeq.in)**.
    💼 *Available for Forward Deployed Engineering, AI Platform Architecture, and Enterprise Deployments.*
    ```
- [ ] **"Deploy with the Creator" CTA:**
  - Add a dedicated section in `README.md`:
    > **Need Retriever deployed in your private AWS/GCP cloud or customized for enterprise compliance?**  
    > [Book an Architecture Discovery Call](https://prateeq.in/scoping) or reach out directly at `prateeqsharma@gmail.com`.
- [ ] **GitHub Profile README Integration:**
  - Pin `retriever` as the #1 showcase repository on `github.com/prat3010`.
  - Display real-time test badge, architecture diagram, and live production demo link.

---

## 🏁 Post-Launch Maintenance & Community Rhythm

Once public, maintaining momentum is key:
1. **First 48 Hours:** Respond to every single GitHub issue, discussion, and tweet within 30 minutes.
2. **Weekly Release Cadence:** Tag micro-releases (`v0.70.0`, `v0.71.0`) with automated changelogs.
3. **Good First Issues:** Label 5–10 beginner-friendly tasks (e.g. "Add Cohere reranker adapter", "Improve Docker startup logs") with `good first issue` to invite open-source contributors.
