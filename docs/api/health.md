---
id: Retriever_API_v1_health
title: "API Specification: Health Probes & Uptime Monitoring (/v1/health)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/health
  - infra/kubernetes
  - monitoring
  - platform/retriever
blast_radius: LOW
security_auth: PUBLIC
invariants:
  - "Liveness probe MUST return 200 OK without requiring database connection."
  - "Readiness probe MUST verify PostgreSQL, Redis, and Ollama connections before returning 200 OK."
---

# API Specification: Health Probes & Uptime Monitoring (`/v1/health`)

#api #health #kubernetes #probes #monitoring #uptime #retriever

> **Authoritative specification for service uptime health checks, Kubernetes liveness (`/health/liveness`) and readiness (`/health/readiness`) probes.**

---

## 1. Health Probe Architecture

```mermaid
flowchart TD
    K8s[Kubernetes Orchestrator / Load Balancer]
    
    K8s -->|Every 10s| Live[/v1/health/liveness/]
    Live --> FastCheck[Check Process Memory & Event Loop]
    FastCheck --> LiveOK[200 OK]
    
    K8s -->|Every 15s| Ready[/v1/health/readiness/]
    Ready --> DB[PostgreSQL Connection Ping]
    Ready --> Redis[Redis L1/L2 Cache Ping]
    Ready --> Embed[Ollama Local Embedding Model Ping]
    DB & Redis & Embed --> ReadyOK[200 OK (All Dependencies Healthy)]
```

---

## 2. API Endpoints

### 2.1 Kubernetes Liveness Probe

- **HTTP Method:** `GET`
- **Path:** `/health/liveness`
- **Authentication:** Public
- **Response Schema (`200 OK`):**
```json
{
  "status": "alive",
  "version": "1.4.0",
  "timestamp": "2026-08-25T05:38:00Z"
}
```

---

### 2.2 Kubernetes Readiness Probe

- **HTTP Method:** `GET`
- **Path:** `/health/readiness`
- **Authentication:** Public
- **Response Schema (`200 OK`):**
```json
{
  "status": "ready",
  "dependencies": {
    "database": {
      "status": "healthy",
      "latencyMs": 2.1
    },
    "redis": {
      "status": "healthy",
      "latencyMs": 0.8
    },
    "ollamaEmbeddings": {
      "status": "healthy",
      "model": "nomic-embed-text",
      "latencyMs": 14.2
    }
  },
  "uptimeSeconds": 864200
}
```

---

## 🔗 Related Architecture & Cross-References
- [Telemetry & Observability Guide](../infrastructure/telemetry_and_observability.md)
- [Database Schemas & Persistence](../infrastructure/database_and_schemas.md)
