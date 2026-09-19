## 📝 Description
Provide a concise explanation of the problem solved or feature added.

Fixes #(issue)

---

## 🏛️ Hexagonal Architecture & Invariants Check
Please verify that your changes adhere to Retriever's non-negotiable architectural rules:

- [ ] **Hexagonal Isolation:** No database (`sqlalchemy`), framework (`fastapi`), or SDK imports in `apps/api/src/domain/`.
- [ ] **Multi-Tenancy:** All queries, models, and operations are strictly scoped by `tenant_id`.
- [ ] **Local-First Embeddings:** Default pipelines preserve $0 local Ollama embeddings (`nomic-embed-text`).
- [ ] **Zero-Toy Compliance:** All endpoints and services implement genuine production logic (no mocks, synthetic padding, or simulated loops).

---

## 🧪 Testing & Verification
Describe the tests you ran to verify your changes:

- [ ] Unit & Integration tests pass: `uv run pytest apps/api/tests/`
- [ ] Architectural boundary test passes: `uv run pytest apps/api/tests/test_architecture.py`
- [ ] Linter passes: `uv run ruff check apps/api/src/ apps/api/tests/`
- [ ] Zero-toy audit passes: `python3 scripts/audit_zero_toy.py`

---

## 📚 Documentation
- [ ] Updated relevant documentation in `docs/` or API specifications if endpoints/configs changed.
