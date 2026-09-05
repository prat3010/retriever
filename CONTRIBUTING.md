# Contributing to Retriever

Thank you for your interest in contributing to **Retriever**! We welcome contributions from developers, researchers, and SREs to make Retriever the gold standard in enterprise, self-hosted cognitive architecture.

---

## 🏛️ Architectural Invariants (Hexagonal Core)

Retriever is engineered with a strict **Hexagonal Architecture (Ports and Adapters)**. Before submitting code, ensure you understand our architectural boundaries:

1. **Domain Isolation (`apps/api/src/domain/`):**
   - Must contain **pure Python logic** and abstract interfaces (`abstractions/`).
   - **ZERO** framework, database, or SDK imports. Never import `fastapi`, `sqlalchemy`, `pydantic_settings`, `openai`, `google.genai`, or `redis` in domain files.
   - Enforced by automated AST tests: `uv run pytest apps/api/tests/test_architecture.py`.

2. **Infrastructure Adapters (`apps/api/src/adapters/`):**
   - Implements domain interfaces to interact with databases (PostgreSQL, pgvector), brokers (RabbitMQ, Celery), vector caches (Redis), and LLM providers.

3. **Application Gateways (`apps/api/src/routers/`):**
   - FastAPI routers handling HTTP/SSE input validation, authentication, and dispatching to domain services.

4. **Multi-Tenancy Isolation:**
   - Every database entity, query method, and API route must strictly scope operations by `tenant_id` using native PostgreSQL Row-Level Security (RLS). Never leak cross-tenant context.

5. **Local-First & Embedding Invariant:**
   - Default vector embedding generation uses local Ollama models (`nomic-embed-text`) or local fastembed models. Never hardcode external paid embedding APIs into core pipelines.

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.11, 3.12, or 3.13
- [`uv`](https://github.com/astral-sh/uv) (Extremely fast Python package manager)
- Docker & Docker Compose
- Node.js 20+ & npm (if working on the Admin UI in `apps/web/`)

### Quickstart
```bash
# 1. Clone repository
git clone https://github.com/prat3010/retriever.git
cd retriever

# 2. Start backing services (PostgreSQL 16 with pgvector, Redis, Ollama)
docker compose up -d

# 3. Install Python dependencies with uv
uv sync

# 4. Run database migrations
uv run alembic upgrade head

# 5. Launch FastAPI development server
uv run uvicorn apps.api.src.main:app --reload --port 8000
```

Verify backend health at: `http://localhost:8000/health/readiness`  
Interactive Swagger docs: `http://localhost:8000/docs`

---

## 🧪 Testing & Code Quality

All pull requests must pass automated unit tests, architectural boundary verification, and linting:

```bash
# 1. Run all unit and integration tests (730+ tests)
uv run pytest apps/api/tests/ -v

# 2. Run architectural boundary tests (Strict Hexagonal imports)
uv run pytest apps/api/tests/test_architecture.py -v

# 3. Code formatting and linting check
uv run ruff check apps/api/src/ apps/api/tests/
uv run ruff format --check apps/api/src/ apps/api/tests/
```

To automatically format code:
```bash
uv run ruff format apps/api/src/ apps/api/tests/
uv run ruff check --fix apps/api/src/ apps/api/tests/
```

---

## 🤝 Pull Request Guidelines

1. **Create a Feature Branch:** `git checkout -b feature/my-new-feature` or `fix/issue-description`.
2. **Commit Messages:** Follow conventional commits (e.g., `feat(cognitive): add colbert reranker cache`, `fix(auth): handle expired jwt gracefully`).
3. **Add Tests:** Every new endpoint, adapter, or domain feature must include automated pytest tests in `apps/api/tests/`.
4. **Update Documentation:** If your change modifies API payloads or configuration, update the relevant file in `docs/api/` or `docs/cognitive/`.
5. **Open a PR:** Ensure CI checks pass. Provide a clear summary of what your PR accomplishes and how you verified it.
