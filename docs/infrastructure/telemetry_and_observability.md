---
id: DeepDive_Telemetry_Observability_Prometheus
title: "Infrastructure Deep-Dive: OpenTelemetry Tracing, Prometheus Metrics & Audit Ledger"
tier: 7_async_infrastructure
platform: retriever
tags:
  - infra/telemetry
  - prometheus
  - opentelemetry
  - audit-logs
  - platform/retriever
blast_radius: MEDIUM
security_auth: SERVICE_ROLE
invariants:
  - "Every inference request MUST log token metrics, latency ms, and estimated cost in inference_logs."
  - "Security audit logs MUST form an append-only SHA-256 hash chain."
---

# Infrastructure Deep-Dive: OpenTelemetry Tracing, Prometheus Metrics & Audit Ledger

#infra #telemetry #prometheus #opentelemetry #audit #metrics #logging #retriever

> **Technical architecture, Prometheus `/metrics` instrumentation, OpenTelemetry distributed tracing spans, and immutable audit logs.**

---

## 1. Observability Stack Architecture

```mermaid
flowchart LR
    API[FastAPI Gateway] --> OTel[OpenTelemetry SDK]
    OTel --> Jaeger[(Jaeger Distributed Tracing)]
    
    API --> Prom[Prometheus Python Client]
    Prom --> Metrics[/metrics Endpoint]
    Metrics --> Grafana[(Grafana Dashboards)]
    
    API --> Audit[Chained SHA-256 Audit Logger]
    Audit --> AuditDB[(PostgreSQL audit_logs)]
```

---

## 2. Key Prometheus Metric Descriptors

| Metric Name | Type | Description |
|:---|:---|:---|
| `retriever_http_requests_total` | Counter | Total HTTP requests partitioned by status code, route, and tenant |
| `retriever_inference_latency_seconds` | Histogram | Grounded RAG token generation latency distribution (P50, P95, P99) |
| `retriever_embedding_duration_seconds` | Histogram | Duration of local nomic-embed vector embedding computation |
| `retriever_tokens_consumed_total` | Counter | Cumulative prompt and completion tokens billed per tenant |
| `retriever_semantic_cache_hits_total`| Counter | Number of requests served from Redis L2 semantic cache |

---

## 3. Full-Stack Auto-Instrumentation (Milestone 75)

- **SQLAlchemy & pgvector:** `SQLAlchemyInstrumentor().instrument(engine=engine)` records query latencies, vector similarity indexing time, and transaction lock durations.
- **Outbound HTTPX Clients:** `HTTPXClientInstrumentor().instrument()` traces external LLM provider calls (Ollama, Gemini, Groq, Tavily, Resend).
- **Celery Worker Queues:** `CeleryInstrumentor().instrument()` propagates trace spans across asynchronous ingestion and evaluation tasks.
- **W3C TraceContext:** Propagates `traceparent` headers between Next.js Edge proxy and FastAPI.

---

## 4. Multi-Channel Webhook Alerting Engine (Milestone 76)

- **Engine:** `alert_service.py` monitors real-time metric streams and dispatches push notifications to Slack, Discord, custom webhooks, or Resend email.
- **Triggers:**
  1. Rolling 1-hour Hallucination Index $> 30\%$.
  2. Monthly tenant token quota $\ge 90\%$ and $100\%$.
  3. P99 latency spikes $> 5.0\text{s}$.
  4. Multi-tenant RLS isolation breach attempts.

---

## 🔗 Related Architecture & Cross-References
- [Health & Probes API Specification](../api/health.md)
- [Caching & Performance Deep-Dive](caching_and_performance.md)
- [Unified Master Roadmap (Phase I)](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)

