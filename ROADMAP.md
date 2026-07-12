# Product Roadmap

This document outlines the implementation phases and milestones for the Retriever platform.

---

## Roadmap Overview

| Milestone | Title | Focus Area | Status | Target |
|---|---|---|---|---|
| **M1** | Repository Foundation | Directory layout, configurations, CI/CD, linting, Docker environment | **Completed** | Q3 2026 |
| **M2** | Authentication & Tenant Foundation | Identity interfaces, relational schemas, Postgres RLS contexts, API keys, cache | **Completed** | Q3 2026 |
| **M3** | Ingestion & Sandbox Parsing | Celery parsing tasks, PDF/DOCX layouts, text chunking, secure sandboxes | **Active** | Q3 2026 |
| **M4** | Retrieval, Fusion & Reranking | pgvector indexes, hybrid search, Reciprocal Rank Fusion, Cohere reranking | *Planned* | Q3 2026 |
| **M5** | Generative Inference & Citations | LLM adapters, prompt orchestrations, context window packing, citation audits | *Planned* | Q3 2026 |
| **M6** | Observability & Hardening | Structured logging, Prometheus metrics, tracer spans, rate limits | *Planned* | Q4 2026 |

---

## Detailed Milestone Targets

### [Completed] Milestone 1: Repository Foundation
- Establish workspace structure for FastAPI, Next.js, and background workers.
- Setup Ruff formatting and TypeScript linting boundaries.
- Build Docker configurations and docker-compose templates.
- Automate checks with GitHub Actions.

### [Completed] Milestone 2: Authentication & Tenant Foundation
- Design abstract identity interfaces (ports) and database schemas.
- Implement thread-local transaction hooks setting PostgreSQL RLS variables.
- Hash client tokens using SHA-256 for secure API validations.
- Implement L1 caching via Redis with write-through logic.
- Configure Tenancy boundary breach checks (Revocation Kill-Switch).

### [Active] Milestone 3: Ingestion & Sandbox Parsing
- Define unstructured layout parsing algorithms for PDF, Markdown, and text files.
- Sandbox parsing executables to isolate runtime threats.
- Implement token-aware sliding window chunkers inside background queues.
- Integrate event broker (RabbitMQ) handling document lifecycle events.
