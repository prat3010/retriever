# ADR-003: Use FastAPI for Backend API Serving Gateway

## Status
Accepted

## Context
The Retriever platform needs a high-performance web gateway to expose REST APIs, stream completion tokens using Server-Sent Events (SSE), and handle multipart document uploads. The application serving layer must remain stateless to support horizontal autoscaling under concurrent user loads.

## Problem
The web framework must support:
1. Low latency request dispatching.
2. Async/await primitives to support concurrent requests without thread starvation.
3. Automated OpenAPI documentation generation.
4. Clean integration with type systems (Python type hints) to ensure safety for developers and AI agents.
5. Flexible middleware integration for authentication, tracing, and rate limiting.

## Decision
Utilize **FastAPI** (Python v3.11+) as the primary backend web framework.

## Alternatives Considered
* **Django / Django REST Framework:** A robust framework, but its synchronous request lifecycle and heavy ORM are not optimized for real-time Server-Sent Events (SSE) streaming.
* **Flask:** Highly modular, but lacks native async support, out-of-the-box OpenAPI documentation, and strict type validation using Pydantic.
* **Node.js (Express / NestJS):** Excellent for async I/O, but Python is preferred for the backend serving layer to simplify integration with AI libraries (e.g., NumPy, PyTorch, tokenizers, and parsing frameworks).

## Consequences
* **Async Performance:** Uses Python's `asyncio` loop and ASGI servers (Uvicorn/Gunicorn) to process connections concurrently, preventing thread starvation.
* **Ingress Validation:** Uses Pydantic to validate API request payloads, returning standard HTTP errors on validation failure.
* **Auto-generated Docs:** Exposes interactive Swagger and ReDoc documentation routes (`/docs`, `/redoc`) dynamically.
* **Ecosystem Compatibility:** Simplifies integration with Python data science, OCR, and AI frameworks.
* **Developer Constraint:** Developers must avoid blocking I/O calls (e.g., standard `requests` calls) in asynchronous request paths, using async alternatives (e.g., `httpx`, `asyncpg`) instead.

## Future Review Criteria
* Monitor CPU utilization under high SSE stream volumes. If Python's event loop bottlenecks routing throughput, evaluate migrating token streaming logic to a dedicated Go/Rust service.
