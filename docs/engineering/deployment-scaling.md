# Deployment Scaling: Multi-Tenant vs. Single-Tenant Isolation

---

## 0. Quick-Start Free Tier (Current)

The platform runs on a **zero-cost** stack:

| Component | Provider | Cost |
|-----------|----------|------|
| API server | [Render](https://render.com) (free web service) | $0 — 512 MB RAM, 0.1 CPU, auto-sleep after 15 min idle |
| Database | [Supabase](https://supabase.com) (free tier) | $0 — 500 MB, pgvector support, Row-Level Security |
| Embeddings | [HuggingFace Inference API](https://huggingface.co/inference-api) (free) | $0 — ~1000 req/min with free token, model `all-mpnet-base-v2` (768-dim) |
| LLM | Client BYOK (bring your own key) | $0 platform cost — tenant provides their own OpenAI/Anthropic/Gemini key |
| Proxy | [Cloudflare Workers](https://workers.cloudflare.com) (free) | $0 — 100k req/day, routes client apps to Render |

### 0.1 Architecture

```
Client App → Cloudflare Proxy → Render (API) → Supabase (DB, vectors, RLS)
                                                → HuggingFace (embeddings)
                                                → Tenant's LLM provider
```

### 0.2 Deployment Steps

1. **Supabase** — Create project, copy `DATABASE_URL`. Run `initialize_database()` to create all tables (pgvector, RLS, indices):
   ```bash
   cd apps/api
   DATABASE_URL="postgresql+asyncpg://..." uv run python -m src.adapters.database.setup
   ```
2. **Render** — Create a new Web Service, connect GitHub repo, set:
   - Runtime: Docker
   - Dockerfile Path: `Dockerfile` (at repo root)
   - Plan: Free
   - Env vars: `DATABASE_URL`, `ENVIRONMENT=production`, `HF_API_TOKEN` (optional)
3. **Cloudflare Workers** — Deploy the proxy (handles CORS, routing, rate limiting):
   ```bash
   cd packages/client-proxy-worker
   npx wrangler deploy
   ```
4. Point the proxy at `https://your-app.onrender.com` and client apps at the proxy URL.

### 0.3 Caveats (Free Tier)

- Render free service **sleeps after 15 minutes of inactivity** — first request after idle takes ~30s to cold-start.
- Supabase free tier: 500 MB DB, 2 GB bandwidth, 50k monthly active users.
- HuggingFace free inference: ~30 req/min unauthenticated, ~1000 req/min with free token.
- No Redis, no Celery — ingestion and chat are synchronous.

This document outlines the strategy for handling two distinct operational scenarios using the single, unified Retriever codebase:
1.  **Scenario A (Personal/Shared Instance):** A single central deployment supporting multiple applications, each isolated logically as a separate tenant.
2.  **Scenario B (Private/Enterprise Instance):** An isolated backend instance deployed physically inside a client's own cloud virtual private cloud (VPC).

---

## 1. Architectural Parity: Multi-Tenant is Single-Tenant

Because the Retriever codebase was architected around **PostgreSQL Row-Level Security (RLS)**, we do not need separate code branches for different deployment scenarios. A dedicated, single-tenant enterprise instance runs the exact same code as the multi-tenant SaaS instance.

```
                  +----------------------------------------------+
                  |            Unified Code Repository           |
                  +----------------------+-----------------------+
                                         |
                      +------------------+------------------+
                      |                                     |
                      v                                     v
         [Scenario A: Multi-Tenant]            [Scenario B: Single-Tenant]
      - Single physical VPS & Database       - Dedicated Client VPC & Database
      - Multiple Tenant Rows in Database     - Exactly One Tenant Row in Database
      - Different apps isolated via RLS      - Complete physical infrastructure separation
```

---

## 2. Operational Playbook for Dedicated Instances

When shipping Retriever as a dedicated, private instance for a client:

### A. Environment Configuration
On the client's cloud host, the environment variables (`.env`) point exclusively to the client's database, caching servers, and storage buckets:
- `DATABASE_URL`: Pointing to client's private database (e.g. Supabase or AWS RDS Postgres with pgvector).
- `REDIS_URL` & `RABBITMQ_URL`: Configured for client-specific brokers.
- `STORAGE_PROVIDER`: `s3` pointing to the client's private S3/R2 storage bucket.

### B. Bootstrapping the Instance
1.  Spin up the client's virtual machines and database.
2.  Deploy the Retriever Docker stack.
3.  Run the database initialization script `initialize_database()` (from `apps/api/src/adapters/database/setup.py`). This compiles the `pgvector` extension, creates all tables, and applies the RLS policies.
4.  Log into their admin dashboard (e.g., `https://dashboard.clientdomain.com`).
5.  Create exactly **one** tenant representing the client company. 

---

## 3. Long-Term Scale Operationalization

To manage multiple client deployments efficiently without drowning in support overhead:

### A. Private Container Registry (Single Source of Truth)
Never distribute source code directly to clients if you can avoid it. Instead:
1.  Set up a private container registry (e.g., GitHub Container Registry - GHCR, AWS ECR, or Docker Hub).
2.  Publish your compiled, tested backend API and Worker docker images to the registry under versioned tags (e.g., `retriever-api:v1.2.0`).
3.  On the client's server, configure `docker-compose.yml` to pull from your private registry.
4.  To push updates or security patches, push the new image to your registry and trigger a pull/restart command (`docker compose pull && docker compose up -d`) on the client servers.

### B. Infrastructure-as-Code (IaC)
Automate the deployment using tools like **Terraform** or **Ansible**.
*   **Terraform:** Configures and provisions the AWS/DigitalOcean resources (VMs, managed DBs, DNS records).
*   **Ansible:** Connects to the provisioned VMs, installs Docker, pulls the containers from your private registry, writes the environment files, and runs migrations.
This reduces deployment setup time from hours to a single command.

### C. Licensing & Revenue Structure
Since the client pays for their own cloud hosting bills (billing is tied directly to their AWS/Supabase account), you can charge a pricing structure based on:
1.  **Upfront Setup & Customization Fee:** To configure prompts, ingest their initial corpus, and integrate with their SSO/JWT auth systems.
2.  **Software License Fee (Annual/Monthly):** For access to new feature releases, performance upgrades, and container updates.
3.  **Support SLA Retainer:** For guaranteed response times if their private instance encounters downtime.
