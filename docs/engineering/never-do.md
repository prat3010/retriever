# Architectural Bans: "Never Do" Rules

This document specifies the ten architectural rules that must never be violated in the Retriever codebase, explaining the technical reasoning behind each constraint. These rules are absolute and will block project compilation and integration pipelines if violated.

---

## 1. Never bypass Row-Level Security (RLS)

* **Rule:** All database transactions accessing customer data must set the active session tenant context variables before executing SQL commands. Database connection pools must use a restricted role that lacks superuser privileges.
* **Reasoning:** Row-Level Security is Retriever's primary defense against cross-tenant data leaks. Bypassing RLS or calling tables via superuser connections risks exposing Tenant A's documents, vectors, or chat histories to Tenant B, resulting in a critical security breach.

## 2. Never hardcode prompts in application source code

* **Rule:** All system instructions, persona definitions, and chat guidelines must be stored in database configuration tables and loaded dynamically at runtime via the prompt registry configuration system.
* **Reasoning:** Prompt engineering is iterative and business-driven. Hardcoding prompts in code requires application rebuilds and redeployments for simple prompt edits, degrading platform agility and tenant customization.

## 3. Never call LLM providers directly from API routes

* **Rule:** Web routes in the API gateway must interact with Large Language Models only through the abstract `LlmProvider` port.
* **Reasoning:** Standardizing on ports decouples serving layers from external APIs. Direct calls leak vendor SDK parameters (e.g. OpenAI model profiles) into HTTP handlers, preventing us from implementing fallback model routing, caching, and rate limiting.

## 4. Never couple business logic to framework code

* **Rule:** Core domain logic (located in `domain/core/`) must remain pure Python/TypeScript, isolated from web framework components (FastAPI dependencies, HTTP request objects, Next.js routers, and ORM decorators).
* **Reasoning:** Tying domain logic to frameworks makes it difficult to run unit tests without running servers, limits our ability to port core code to other execution contexts (e.g., CLI tools or separate background daemons), and binds us to framework-specific lifecycles.

## 5. Never expose secrets or PII in logs or responses

* **Rule:** Access keys, database passwords, JWT tokens, and sensitive customer data (SSNs, raw chunks text content) must be redacted from system logs. API error messages must never output database traces or internal file system paths.
* **Reasoning:** Logs and error messages are often forwarded to external telemetry systems. Leaking credentials or PII in logs creates security vulnerabilities and violates regulatory compliance frameworks (SOC 2, HIPAA, GDPR).

## 6. Never duplicate domain logic across modules

* **Rule:** Core business calculations (e.g. Reciprocal Rank Fusion, token count limits, coordinate mapping) must live in a single domain module and be reused via interface bindings.
* **Reasoning:** Duplicating domain logic leads to code drift, where changes to core formulas (like RRF ranking weights) are applied in one file but missed in another, producing inconsistent search results.

## 7. Never introduce new technologies without an ADR

* **Rule:** Adding database engines, search libraries, communication protocols, or major packages requires proposing a new Architecture Decision Record (ADR) under `docs/decisions/` and obtaining maintainer approval.
* **Reasoning:** Unvetted dependencies introduce security vulnerabilities, compatibility issues, and increase the maintenance footprint of the repository.

## 8. Never violate dependency direction

* **Rule:** Dependencies must flow inward toward abstraction interfaces. Outer layers (adapters, routers) may import ports, but inner domains must never import adapters or infrastructure components.
* **Reasoning:** Violating dependency direction creates tight coupling, causing changes in infrastructure (e.g., migrating from pgvector to Qdrant) to ripple through and break core business logic.

## 9. Never perform blocking I/O in asynchronous request paths

* **Rule:** Fast API routers running on asynchronous loops must use non-blocking async clients (e.g., `httpx` instead of `requests`, `asyncpg` instead of standard `psycopg2`) for network and database queries.
* **Reasoning:** A single blocking call inside an async function blocks the entire event loop thread, stopping the server from processing other concurrent requests and degrading system performance.

## 10. Never access the database directly from frontend applications

* **Rule:** The frontend reference UI (Next.js) must fetch data only by sending HTTP/SSE requests to the API Gateway. The frontend is prohibited from importing database drivers or executing SQL.
* **Reasoning:** The frontend runs in client environments. Direct database access requires exposing database connection credentials or bypasses tenant identity verification, violating security boundaries.
