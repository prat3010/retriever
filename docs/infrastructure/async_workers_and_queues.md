---
id: DeepDive_AsyncWorkers_Celery_RabbitMQ
title: "Infrastructure Deep-Dive: Distributed Celery Workers, RabbitMQ Queues & Beat Scheduler"
tier: 7_async_infrastructure
platform: retriever
tags:
  - infra/celery
  - rabbitmq
  - queues
  - workers
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Long-running OCR and vector embedding tasks MUST run on dedicated Celery queues."
---

# Infrastructure Deep-Dive: Distributed Celery Workers, RabbitMQ Queues & Beat Scheduler

#infra #celery #rabbitmq #queues #workers #async #retriever

> **Technical architecture, task routing topologies, retry backoff policies, and Celery Beat periodic jobs.**

---

## 1. Task Queue Topology & Routing

```mermaid
flowchart LR
    API[FastAPI Gateway] -->|AMQP Dispatch| Broker[(RabbitMQ Broker)]
    
    Broker --> Q1[Queue: ingestion.parse]
    Broker --> Q2[Queue: knowledge.embed]
    Broker --> Q3[Queue: evaluation.run]
    Broker --> Q4[Queue: periodic.reconcile]
    
    Q1 --> W1[Worker Pool: Docling Layout & OCR]
    Q2 --> W2[Worker Pool: Local nomic-embed GPU]
    Q3 --> W3[Worker Pool: RAGAS Evaluation Engine]
    Q4 --> W4[Worker: Beat Quota & Billing Cron]
```

---

## 2. Dedicated Queue Matrix

| Queue Name | Typical Payload | Prefetch Count | Concurrency Model | Max Retries |
|:---|:---|:---:|:---:|:---:|
| `ingestion.parse` | 50MB PDF/DOCX Binaries | 1 | Pre-fork (Processes) | 3 |
| `knowledge.embed` | 200 Text Chunks | 8 | Thread Pool / CUDA | 5 |
| `evaluation.run` | Chat Conversation Trace | 4 | Gevent / Asyncio | 2 |
| `periodic.reconcile` | Stripe / Razorpay Sync | 2 | Gevent | 3 |

---

## 🔗 Related Architecture & Cross-References
- [Document Ingestion API](../api/document.md)
- [Caching & Performance](caching_and_performance.md)
