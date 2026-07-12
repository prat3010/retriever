# ADR-004: Use RabbitMQ as Primary Asynchronous Message Broker

## Status
Accepted

## Context
Document ingestion processes—including layout extraction, OCR parsing, embedding generation, and vector indexing—are computationally heavy operations. Running these tasks synchronously within the API gateway thread pool degrades API search performance. We must offload these workloads to asynchronous worker instances.

## Problem
The task queue system must provide:
1. Durable message delivery guarantees (at-least-once processing).
2. Decoupled direct exchange routing for granular task distribution.
3. Dead-Letter Queue (DLQ) support for parsing and embedding generation failures.
4. Scale-independent worker consumption boundaries.
5. Idempotent worker scheduling.

## Decision
Utilize **RabbitMQ** as the primary platform message broker, integrated with **Celery** or native Python worker daemons.

## Alternatives Considered
* **Redis Pub/Sub:** Redis provides fast in-memory message delivery but lacks persistent storage queues, dead-letter routing, and message acknowledgment features, risking message loss during hardware outages.
* **AWS SQS:** A managed queue option, but introduces vendor lock-in, conflicts with our provider-agnostic deployment requirement, and is harder to run locally in development.
* **Apache Kafka:** Ideal for high-throughput stream processing, but introduces high operational complexity and memory resource costs for Retriever's transactional task distribution needs.

## Consequences
* **Durable Processing:** Tasks are persisted on RabbitMQ nodes, protecting against message loss if worker containers crash.
* **Flexible Routing:** Supports direct and topic exchanges, allowing task division (e.g. routing PDF parsing to dedicated sandbox nodes and embedding tasks to GPU nodes).
* **DLQ Verification:** Retries are isolated from active queues. Tasks that fail repeatedly route to `dead.letter` queues for auditing.
* **Worker Scaling:** Background workers scale horizontally based on active RabbitMQ queue backlogs.
* **Operational Constraint:** Requires monitoring broker disks to prevent resource-limit freezes during high ingestion volumes.

## Future Review Criteria
* Re-evaluate queue latencies if daily document ingestion volumes exceed 1,000,000 files.
* Monitor RabbitMQ cluster CPU and memory limits during batch ingestion runs.
