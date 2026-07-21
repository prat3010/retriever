"""Architecture conformance tests.

Enforces the hybrid strategy:
- Hexagonal import boundaries (domain never imports infrastructure)
- Routers access adapters through container, not directly
- main.py contains no route handlers
- No hardcoded system prompt constants

See docs/engineering/engineering-playbook.md §13.3.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_DIR = REPO_ROOT / "apps" / "api" / "src" / "domain"
API_SRC = REPO_ROOT / "apps" / "api" / "src"
ROUTER_DIR = API_SRC / "routers"
MAIN_PY = API_SRC / "main.py"

FORBIDDEN_DOMAIN_IMPORTS = {
    "adapters",
    "fastapi",
    "sqlalchemy",
    "pika",
    "celery",
    "openai",
    "redis",
    "routers",
}

HARDCODED_PROMPT_PATTERNS = [
    "_DEFAULT_SYSTEM_PROMPT",
    '"You are a helpful grounding assistant',
    "'You are a helpful grounding assistant",
]

ALLOWED_ADAPTER_IMPORTS_IN_ROUTERS = {
    "src.adapters.api",
    "src.adapters.telemetry",
    "src.adapters.cache",
    "src.adapters.database.connection",
}


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        yield path


def _parse_imports(path: Path) -> list[str]:
    """Return all top-level (first-component) module names imported by path."""
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


def _parse_full_imports(path: Path) -> list[str]:
    """Return all fully-qualified dotted module names imported by path."""
    with open(path) as f:
        try:
            tree = ast.parse(f.read(), filename=str(path))
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
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


def test_routers_do_not_bypass_container() -> None:
    """Routers must not import adapters directly — only through container
    or cross-cutting infrastructure (security, telemetry, cache)."""
    violations: list[str] = []
    for path in sorted(_iter_py_files(ROUTER_DIR)):
        mods = _parse_full_imports(path)
        for mod in mods:
            if not mod.startswith("src.adapters"):
                continue
            allowed = any(mod.startswith(a) for a in ALLOWED_ADAPTER_IMPORTS_IN_ROUTERS)
            if not allowed:
                rel = path.relative_to(ROUTER_DIR)
                violations.append(f"{rel}: imports {mod}")

    assert not violations, (
        "Routers import adapters directly (should use container):\n"
        + "\n".join(violations)
    )


def test_main_py_has_no_route_handlers() -> None:
    """main.py must not define route handlers — only exception handlers
    and lifecycle hooks."""
    with open(MAIN_PY) as f:
        tree = ast.parse(f.read(), filename=str(MAIN_PY))

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Attribute):
                continue
            if not isinstance(decorator.value, ast.Name):
                continue
            dname = f"{decorator.value.id}.{decorator.attr}"
            if dname.startswith("app.") and dname not in {
                "app.exception_handler",
                "app.on_event",
                "app.middleware",
            }:
                violations.append(f"Line {node.lineno}: @{dname} on {node.name}")

    assert not violations, (
        "main.py contains route handlers (should be in routers):\n"
        + "\n".join(violations)
    )


def test_event_bus_wired_in_container() -> None:
    """Container must expose an EventPublisher instance."""
    from src.container import container, event_publisher
    from src.domain.abstractions.events import EventPublisher

    assert isinstance(event_publisher, EventPublisher), (
        f"event_publisher must be an EventPublisher, got {type(event_publisher)}"
    )
    assert container.event_publisher is event_publisher, (
        "Module-level event_publisher must match container.event_publisher"
    )
