# Deployment Scaling: Multi-Tenant vs. Single-Tenant Isolation

---

## 0. Quick-Start Free Tier (Current)

The platform runs on a **near-zero-cost** stack:

| Component | Provider | Cost |
|-----------|----------|------|
| Component | Provider | Cost |
|-----------|----------|------|
| API server | [Oracle Cloud](https://oracle.com/cloud/free) (free VM) | $0 — 1 OCPU, 1 GB Physical RAM + 7 GB NVMe Swap (8 GB Memory Pool), Ubuntu 24.04, always-on |
| In-Memory Cache | Redis Server (Local VM) | $0 — Session cache, semantic caching, ZSET sliding-window rate limiting |
| Database | [Supabase](https://supabase.com) (free tier) | $0 — 500 MB, pgvector support, Row-Level Security, connection pooler |
| Embeddings | [Ollama](https://ollama.com) self-hosted on same VM | $0 — `nomic-embed-text` (274 MB), CPU-only, always-on, zero API rate limits |
| LLM | BYOK (bring your own key) | $0 platform cost — tenant provides their own OpenAI/Anthropic/Gemini key |
| Frontend CDN | [Vercel](https://vercel.com) (Hobby) | $0 — `retriever-ivory.vercel.app` & `prateeq.in`, auto-deploys from GitHub |
| Domain + SSL | GoDaddy + Let's Encrypt | ~$15/yr for domain; SSL is free and auto-renewing |

### 0.1 Architecture

```
Client App (Vercel) → Nginx (Oracle VM, SSL) → Uvicorn (Oracle VM) → Supabase (DB, vectors, RLS)
                                                     ↓                     ↓
                                         Redis (Cache / RateLimit)   Ollama (nomic-embed-text)
                                                     ↓
                                         LLM Provider (OpenAI / Gemini / Anthropic)
```

### 0.2 Deployment Steps

1. **Supabase** — Create project, copy `DATABASE_URL`. Run `initialize_database()` to create all tables (pgvector, RLS, indices):
   ```bash
   cd apps/api
   DATABASE_URL="postgresql+asyncpg://..." uv run python -m src.adapters.database.setup
   ```
2. **Oracle VM** — Provision `VM.Standard.E2.1.Micro` (Ubuntu 24.04). Allow ingress on ports 22, 80, 443 in VCN security list.
3. **On the VM (Swap & Prerequisites Setup)**:
   ```bash
   # Configure 7GB NVMe Swap (8GB effective memory pool)
   sudo fallocate -l 7G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   sudo sysctl vm.swappiness=10
   echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

   # Install deps & Redis
   sudo apt update && sudo apt install -y nginx certbot python3-pip git redis-server
   sudo systemctl enable --now redis-server

   # Install Ollama & pull embedding model
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull nomic-embed-text
   sudo systemctl enable --now ollama

   # Create app user and directory
   sudo useradd -m -s /bin/bash retriever
   sudo mkdir -p /opt/retriever && sudo chown retriever:retriever /opt/retriever

   # As retriever user:
   cd /opt/retriever
   git clone https://github.com/anomalyco/retriever .
   pip install uv
   uv sync

   # Create .env
   cp .env.example .env && nano .env
   ```
4. **systemd service** — Create `/etc/systemd/system/retriever-api.service`:
   ```ini
   [Unit]
   Description=Retriever API
   After=network.target ollama.service redis-server.service

   [Service]
   User=retriever
   WorkingDirectory=/opt/retriever/apps/api
   EnvironmentFile=/opt/retriever/.env
   ExecStart=/opt/retriever/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
5. **Nginx reverse proxy** — Configure `/etc/nginx/sites-available/rag.prateeq.in`:
   ```nginx
   server {
       listen 443 ssl;
       server_name rag.prateeq.in;
       ssl_certificate /etc/letsencrypt/live/rag.prateeq.in/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/rag.prateeq.in/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
6. **SSL** — `sudo certbot --nginx -d rag.prateeq.in`
7. **Enable and start services**:
   ```bash
   sudo systemctl enable --now ollama redis-server retriever-api nginx
   sudo systemctl status retriever-api  # verify running
   ```

### 0.3 Memory Topology & Performance

- **8 GB Total Virtual Memory Pool:** 1 GB Physical RAM + 7 GB NVMe Swap provides ample headroom for Ollama (`nomic-embed-text` ~274 MB), Redis (~30 MB), Uvicorn API workers, and concurrent vector queries without OOM thrashing.
- **Low Swappiness (`vm.swappiness=10`):** Keeps fast physical RAM dedicated to low-latency HTTP request handling and active query loops, relegating idle daemon pages to SSD swap.
- **Local Redis Layer:** Provides sub-millisecond semantic cache lookups and token-bucket rate limiting without external cloud roundtrips.

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
3.  In a future Docker-based deployment, the client's server would configure `docker-compose.yml` to pull from your private registry.
4.  To push updates or security patches, push the new image to your registry and trigger a pull/restart command (`docker compose pull && docker compose up -d`) on the client servers. *(Currently using bare systemd — Docker would be introduced when multi-client deployments require it.)*

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
