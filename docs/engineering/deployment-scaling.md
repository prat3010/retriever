# Deployment Scaling: Multi-Tenant vs. Single-Tenant Isolation

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
