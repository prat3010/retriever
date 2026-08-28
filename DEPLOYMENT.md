# Retriever — Oracle Cloud Deployment Guide

Deployed on **Oracle Cloud** (free tier, `VM.Standard.E2.1.Micro`) + **Supabase** (free tier).  
Total monthly cost: **$0**.

---

## Architecture

```
rag.prateeq.in
        │
    ┌───▼──────────────┐
    │   Nginx (SSL)    │   port 443 → proxy_pass → port 8000 (300s timeout)
    │   Let's Encrypt  │
    └───┬──────────────┘
        │
    ┌───▼──────────────┐       ┌────────────────────────┐
    │  API (systemd)   │ ──→   │  Ollama (systemd)      │
    │  uvicorn :8000   │       │  :11434 (nomic-embed)  │
    └───┬──────────┬───┘       └────────────────────────┘
        │          │           ┌────────────────────────┐
        │          └─────────→ │  Redis (systemd)       │
        │                      │  :6379 (caching/locks) │
        │                      └────────────────────────┘
    ┌───▼──────────────┐
    │  Supabase        │
    │  PostgreSQL      │
    │  + pgvector      │
    └──────────────────┘

8 GB Unified Memory Pool: 1 GB Physical RAM + 7 GB NVMe Swap (vm.swappiness=10)
```

---

## Prerequisites

| Account | Sign up at |
|---------|-----------|
| GitHub | github.com |
| Oracle Cloud | cloud.oracle.com |
| Supabase | supabase.com |

---

## Phase 2: Oracle Instance Setup

### 1. SSH In

```sh
ssh -i ~/.ssh/oracle_rsa ubuntu@<PUBLIC_IP>
```

### 2. Configure 7GB NVMe Swap (8GB Total Usable Memory)

```sh
# Allocate 7GB swapfile on high-speed NVMe boot volume
sudo fallocate -l 7G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Tune kernel swappiness to preserve low-latency network buffers in physical RAM
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

### 3. Install Dependencies & Redis

```sh
# System packages & Redis server
sudo apt-get update && sudo apt-get install -y \
    python3 python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    redis-server git curl

# Enable & start Redis
sudo systemctl enable --now redis-server

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text
```

### 3. Deploy the App

```sh
# Clone repo
cd /opt
sudo git clone https://github.com/prat3010/retriever.git
sudo chown -R ubuntu:ubuntu retriever
cd retriever

# Python setup
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv pip compile apps/api/pyproject.toml -o requirements.txt
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://postgres.<YOUR_PROJECT_REF>:<YOUR_DB_PASSWORD>@aws-1-us-west-2.pooler.supabase.com:5432/postgres?prepared_statement_cache_size=0
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
ADMIN_MASTER_KEY=<SECURE_RANDOM_256BIT_HEX_KEY>
OPENAI_API_KEY=<YOUR_OPENROUTER_OR_OPENAI_KEY>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
KEY_ENCRYPTION_KEY=<SECURE_32_BYTE_BASE64_KEY>
SECRET_KEY=<SECURE_JWT_SECRET_KEY>
EOF
```

### 4. Create systemd Service for the API

```sh
sudo tee /etc/systemd/system/retriever-api.service << 'EOF'
[Unit]
Description=Retriever API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/retriever
ExecStart=/opt/retriever/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
EnvironmentFile=/opt/retriever/.env
Environment=PYTHONPATH=/opt/retriever/packages/processing-core/src
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now retriever-api
```

### 5. Set Up Nginx + SSL

```sh
# Point DNS first: A record for rag.prateeq.in → <PUBLIC_IP>

# Nginx config
sudo tee /etc/nginx/sites-available/retriever << 'EOF'
server {
    listen 80;
    server_name rag.prateeq.in;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/retriever /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL
sudo certbot --nginx -d rag.prateeq.in --non-interactive --agree-tos -m you@email.com
```

### 6. Verify

```sh
curl https://rag.prateeq.in/health/liveness
curl https://rag.prateeq.in/health/readiness
```

---

## Environment Variables

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Supabase pooler connection string (same as before) |
| `EMBEDDING_PROVIDER` | `ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `ADMIN_MASTER_KEY` | Set a secure random value |
| `INTERNAL_API_KEY` | Shared secret for remote storage fallback |

---

## Updating

Production deploys are automated: pushing to `main` with changes under `apps/api/`, `packages/`, or `workers/` triggers `.github/workflows/deploy-api.yml`, which SSHes into the Oracle VM (deploy key in GitHub Secrets), pulls, and restarts `retriever-api`.

Manual update (for emergency local fixes):

```sh
ssh -i ~/.ssh/oracle_rsa ubuntu@<PUBLIC_IP>
cd /opt/retriever
git pull
sudo systemctl restart retriever-api
```

---

## Production Operations

### Nightly Database Backups

`/opt/retriever/scripts/backup-db.sh` runs via cron every night at 02:30 UTC and dumps **every table** as gzipped CSV into `/opt/retriever/backups/` (14-day retention, manifest per run).

Why CSV-per-table instead of `pg_dump`: the app connects through the Supabase **transaction pooler**, and `pg_dump` requires session-scoped state that pgbouncer drops (it hangs). `\copy` per table is a single statement and pooler-safe. Schema is not dumped — it lives in the repo as Alembic migrations.

Manual run + sanity check:

```sh
ssh -i ~/.ssh/oracle_rsa ubuntu@<PUBLIC_IP>
/opt/retriever/scripts/backup-db.sh
ls -la /opt/retriever/backups/ | tail -5
```

### Restore Procedure

1. Create a fresh Supabase project (or use an existing one).
2. Point `DATABASE_URL` in `/opt/retriever/.env` at the new project, restart the API, and let Alembic rebuild the schema (`alembic upgrade head` runs at startup).
3. Restore data per table from the latest backup:

```sh
# on the Oracle VM, with .env updated
cd /opt/retriever/backups
for f in 2026-07-31-*.csv.gz; do
  table="${f#*-}"; table="${table%.csv.gz}"
  gzip -dc "$f" | psql "$DATABASE_URL" -c "\copy \"$table\" FROM STDIN WITH (FORMAT csv, HEADER)"
done
```

4. Rebuild vector indexes if needed (`POST /v1/admin/tenants/{tenantId}/documents/reindex` or the batch `scripts/process-pending.sh`).

### LLM Key Quota Alerting

`/opt/retriever/scripts/quota-alert.sh` runs daily at 08:00 UTC. It queries the provider's usage endpoint (OpenRouter `/auth/key` for the platform key) and pushes a warning when remaining credit drops below 20% (critical at 10%).

- Push channel: ntfy.sh topic from `NTFY_TOPIC` in `.env` (subscribe in the ntfy app, no account needed).
- Optional: `ALERT_WEBHOOK` in `.env` for a Slack/Discord incoming webhook.
- Free-tier / unlimited keys report as non-monitorable — the alert then recommends a prepaid key.

### Nginx Hardening (current state)

Applied on the live server:

- `limit_req_zone api:10m rate=20r/s` + `limit_req burst=40 nodelay` on `/` — per-IP rate limiting at the proxy layer.
- `Strict-Transport-Security` (max-age 31536000), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'`.
- fail2ban active with an `sshd` jail (maxretry 4, bantime 1h).
- Port 8000 is closed at the security-group level; all traffic goes through nginx on 443/80.

### Staging Environment

There is no separate staging server. The recommended process:

1. Run the repo locally (dev machine) with the same `.env` template — this is the fastest feedback loop.
2. Push to a feature branch; `ci.yml` runs lint + tests (407 tests) on every PR.
3. Merge to `main` → `deploy-api.yml` auto-deploys to Oracle and runs a post-deploy smoke test (liveness + readiness).

If a true isolated staging is ever needed, deploy a second Oracle free-tier VM following this guide and swap `CORS_ORIGINS`/`DATABASE_URL` to point at a separate Supabase project.

---

## Root Cause Addendum: Initial Chat Outage (2026-07)

**Symptom:** Chat was broken at initial production deploy; search worked, chat returned provider errors.

**Root cause:** Both LLM keys configured at the time had exhausted their quotas simultaneously — the Gemini key and the OpenAI key were both at 0 credit. The M19 Smart Model Failover correctly detected the failure and routed to the fallback provider, but there was no healthy provider left to fall back to, so every chat request failed after exhausting retries.

**Why it wasn't caught:** No quota monitoring existed, and free-tier keys do not fail loudly until hard-blocked.

**Lessons applied:**
1. Quota alerting now runs daily (`quota-alert.sh`) with ntfy/webhook push before the keys hit zero.
2. Prefer prepaid keys with a real usage limit so the alert has a threshold to measure.
3. Fallback only protects against transient outages (timeout, 5xx) — not against all providers being out of credit at once.

---

## Cleaning Up (if you ever stop using Render)

The old Render service can be deleted from the Render dashboard.  
Old Render-specific files in this repo (`deploy/start.py`) have already been removed.

---

## **Related Architecture & Cross-References**

- [Oracle Ampere Deployment Reference](ORACLE_DEPLOYMENT_REFERENCE.md)
- [Oracle Ampere VM Provisioning Guide](ORACLE_AMPERE_CLAIM_GUIDE.md)
- [System Status & Production Hardening](PROJECT_STATUS.md)
