# ADR-008: Hexagonal Architecture Decoupling & Pure Domain Isolation

## Status
Accepted

## Context
As Retriever evolved from a monolithic prototype into an enterprise platform with dozens of cognitive modules, tight coupling to web frameworks (FastAPI), ORMs (SQLAlchemy), and external vendor SDKs (OpenAI, Anthropic, LangChain) introduced high fragility, making unit testing difficult and violating the Single Responsibility Principle.

## Problem
We need an architectural discipline that:
1. Keeps the core business logic (prompt construction, chunking algorithms, retrieval ranking, evaluation metrics) 100% independent of databases and web routers.
2. Allows swapping underlying infrastructure (e.g. switching vector engines or LLM providers) without modifying domain logic.
3. Guarantees that automated domain test suites run instantaneously without requiring live databases, network connections, or mock servers.

## Decision
Enforce strict **Hexagonal Architecture (Ports and Adapters)** across `apps/api`:
1. `src/domain/abstractions/`: Defines pure abstract protocols (`Protocol`, `ABC`) and Pydantic data contracts. **Forbidden from importing FastAPI, SQLAlchemy, HTTP clients, or cloud SDKs.**
2. `src/domain/`: Implements domain services depending strictly on abstractions.
3. `src/adapters/`: Encapsulates all infrastructure (PostgreSQL database models, Redis cache, external AI SDKs).
4. `src/routers/`: Thin HTTP adapters mapping REST routes to domain services via dependency injection (`src/container.py`).
5. **Automated Enforcement:** Maintained via `apps/api/tests/test_architecture.py` which scans AST import graphs on every CI run, failing if any domain file imports infrastructure.

## Consequences
* **Positive:** Domain logic can be unit-tested in isolation in milliseconds.
* **Positive:** Zero vendor lock-in; swapping an upstream provider or database adapter requires writing one adapter class.
* **Negative:** Requires creating abstract interfaces (`Protocols`) and dependency injection wiring in `container.py`, introducing minor boilerplate.

## Future Review Criteria
* Review if dependency injection wiring complexity exceeds 500 lines in `container.py`.
