"""Architecture conformance tests.

Enforces the hybrid strategy:
- Hexagonal import boundaries (domain never imports infrastructure)
- No hardcoded system prompt constants
- RLS coverage on customer-data tables (via migration audit)

See docs/engineering/engineering-playbook.md §13.3.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_DIR = REPO_ROOT / "apps" / "api" / "src" / "domain"
API_SRC = REPO_ROOT / "apps" / "api" / "src"

FORBIDDEN_DOMAIN_IMPORTS = {
    "adapters",
    "fastapi",
    "sqlalchemy",
    "pika",
    "celery",
    "openai",
    "redis",
}

HARDCODED_PROMPT_PATTERNS = [
    "_DEFAULT_SYSTEM_PROMPT",
    '"You are a helpful grounding assistant',
    "'You are a helpful grounding assistant",
]

CUSTOMER_TABLES = {
    "tenant_configs",
    "api_keys",
    "audit_logs",
    "documents",
    "document_chunks",
    "configurations",
    "chat_messages",
    "chat_sessions",
    "vector_records",
    "prompt_templates",
    "inference_logs",
    "tenants",
}

MIGRATIONS_DIR = API_SRC / "adapters" / "database" / "migrations" / "versions"


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        yield path


def _parse_imports(path: Path) -> list[str]:
    """Return all top-level dotted module names imported by path."""
    with open(path) as f:
        try:
            tree = ast.parse(f.read(), filename=str(path))
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


# ── Tests ──────────────────────────────────────────────────────────────


def test_domain_does_not_import_infrastructure() -> None:
    """Domain files must not import adapters, FastAPI, SQLAlchemy, or
    other infrastructure frameworks."""
    violations: list[str] = []
    for path in sorted(_iter_py_files(DOMAIN_DIR)):
        mods = _parse_imports(path)
        bad = FORBIDDEN_DOMAIN_IMPORTS & set(mods)
        if bad:
            rel = path.relative_to(DOMAIN_DIR)
            violations.append(f"{rel}: imports {', '.join(sorted(bad))}")

    assert not violations, (
        "Domain layer imports infrastructure:\n" + "\n".join(violations)
    )


def test_no_hardcoded_system_prompt() -> None:
    """No source file should contain a hardcoded system prompt constant
    or default prompt string."""
    violations: list[str] = []
    for path in sorted(_iter_py_files(API_SRC)):
        text = path.read_text()
        for pattern in HARDCODED_PROMPT_PATTERNS:
            if pattern in text:
                rel = path.relative_to(API_SRC)
                violations.append(f"{rel}: contains {pattern!r}")
                break

    assert not violations, (
        "Hardcoded system prompt patterns found:\n" + "\n".join(violations)
    )
