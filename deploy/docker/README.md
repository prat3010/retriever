# 🐳 Retriever Container Architecture & Docker Compose Guide

This directory contains the production multi-stage container definitions and orchestration recipes for running **Retriever** in isolated container environments.

---

## 🏛️ Stack Architecture

```text
               User / Browser (Port 3000)      API Clients (Port 8000)
                           │                              │
                           ▼                              ▼
                 ┌───────────────────┐          ┌───────────────────┐
                 │ retriever-web     │ ───────► │ retriever-api     │
                 │ (Next.js Studio)  │          │ (FastAPI Backend) │
                 └───────────────────┘          └─────────┬─────────┘
                                                          │
                                ┌─────────────────────────┼─────────────────────────┐
                                ▼                         ▼                         ▼
                      ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
                      │ postgres          │     │ redis             │     │ ollama            │
                      │ (pgvector:pg16)   │     │ (Redis 7 AOF)     │     │ (nomic-embed)     │
                      └───────────────────┘     └───────────────────┘     └───────────────────┘
```

---

## 📦 Container Specifications

### 1. `retriever-api` (`Dockerfile.api`)
- **Base Image:** `python:3.12-slim`
- **Build Strategy:** Multi-stage build minimizing image footprint.
- **Port:** `8000`
- **Entrypoint Script:** `scripts/docker-entrypoint.sh` running `alembic upgrade head`, seeding the demo tenant, and launching `uvicorn`.

### 2. `retriever-web` (`Dockerfile.web`)
- **Base Image:** `node:20-alpine`
- **Build Strategy:** Standalone Next.js output optimization (`output: 'standalone'`).
- **Port:** `3000`

### 3. Persistent Data Services
- **`postgres`:** `pgvector/pgvector:pg16` mounted to volume `postgres_data`.
- **`redis`:** `redis:7-alpine` mounted to volume `redis_data` with `--appendonly yes`.
- **`ollama`:** `ollama/ollama:latest` mounted to volume `ollama_data` with pre-cached `nomic-embed-text` embeddings.

---

## 🚀 Running the Stack

### 1. Start with Docker Compose
```bash
# Clone repository
git clone https://github.com/prat3010/retriever.git
cd retriever

# Copy environment template
cp .env.docker.example .env

# Launch all 5 services
docker compose up -d
```

### 2. Check Service Health
```bash
docker compose ps
```

### 3. View Logs
```bash
# Follow API logs
docker compose logs -f api

# Follow Web Studio logs
docker compose logs -f web
```

### 4. Teardown
```bash
# Stop containers (preserves volume data)
docker compose down

# Stop containers and purge volumes
docker compose down -v
```
