---
name: retriever-conformance
description: Enforces Hexagonal Architecture boundaries, zero-over-engineering rules, and automated verification (Ruff, Pytest, Alembic) for Retriever milestone execution.
---

# Retriever Engineering Conformance Skill

This skill defines the mandatory coding, architectural, and verification standards for implementing features and milestones in the Retriever platform.

## 1. Hexagonal Architecture Boundaries

- **Domain Isolation (`src/domain/`)**:
  - Domain abstractions and business logic must **NEVER** import infrastructure, ORM, framework, or database libraries (e.g., `sqlalchemy`, `fastapi`, `redis`, `pgvector`, `pydantic_settings`).
  - Domain entities must interact with external systems exclusively through interfaces defined in `src/domain/abstractions/`.

- **Adapter Isolation (`src/adapters/`)**:
  - Infrastructure implementations (database repositories, vector search, LLM clients, rate limiters) belong in `src/adapters/`.
  - Adapters must implement domain abstraction protocols.

## 2. Automated Quality & Verification Protocol

Before finishing any task or marking a milestone complete, you **MUST** run:

1. **Linting & Formatting:**
   ```bash
   ruff check --fix
   ```
2. **Unit & Architecture Conformance Tests:**
   ```bash
   pytest
   ```
   *Note: Ensure `tests/test_architecture.py` passes cleanly.*

## 3. Database Schema & Migration Protocol

- Whenever modifying SQLAlchemy models in `apps/api/src/adapters/database/models.py`:
  - Ensure multi-tenancy `tenant_id` foreign keys and compound indexes are defined.
  - Generate or write corresponding Alembic migrations under `apps/api/alembic/versions/`.

## 4. Minimal Code & YAGNI Principle

- Reach for standard library solutions before adding new external dependencies.
- Avoid speculative abstractions, unnecessary flexibility, or over-engineered helper frameworks.
- Prefer small, targeted diffs over broad file rewrites.
