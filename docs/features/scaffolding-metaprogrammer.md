# Autonomous FDE Metaprogrammer & Self-Extending Capability Studio

**Milestone:** M97 (v0.82.0)  
**System Layer:** System Extensibility & Metaprogramming (Battery #17)  
**Architecture:** Pure Hexagonal Domain + Static AST Boundary Validator + Dynamic Router Mounting Fault Barrier  

---

## 1. Executive Summary

Milestone 97 completes **Phase L (Forward Deployed Engineering Enterprise Agentic Stack)** by introducing the **Autonomous FDE Metaprogrammer & Self-Extending Capability Studio** as **Platform Battery #17**.

As enterprise requirements diverge across bespoke third-party systems (HubSpot, Salesforce, custom ERPs, internal databases, proprietary scoring algorithms), platform users fall into two profiles:
1. **Business Operators:** Want to achieve workflows without code, leveraging existing native platform batteries.
2. **Forward Deployed Engineers (FDEs):** Need to author, test, and mount production-grade custom integrations rapidly while guaranteeing zero architecture erosion.

Milestone 97 delivers an end-to-end cognitive solution:
- **Dual-Persona Solution Engine:** Automatically matches requirements against the 16 native platform batteries for low-code users, while generating full Hexagonal code slices for FDE engineers.
- **Static AST Boundary Gate:** Mathematical verification using Python's standard `ast` module, ensuring **0 framework imports** (`fastapi`, `sqlalchemy`, `celery`, `redis`, etc.) in domain slices before code is written to disk.
- **Git-Isolated Plugin Storage:** Plugins are written to `apps/api/src/plugins/custom/{plugin_id}/` (gitignored with `.gitkeep`), completely isolated from core platform repositories.
- **Dynamic In-Process Mounting with Fault Barrier:** Dynamic loading of FastAPI routers at `/v1/plugins/{plugin_id}/*` during application lifespan. Plugin import errors or exceptions are contained in an isolated try-catch barrier without degrading core API routes or other tenants.
- **1-Click Community PR Generator:** Automatic Git branch creation (`feat/plugin-{plugin_id}`) and comprehensive GitHub Pull Request Markdown generation for upstreaming capabilities into core platform batteries.
- **Cross-Platform UI Surfaces:** Interactive Capability Studio in the Retriever Admin Dashboard (`apps/web` at `/scaffold`) and Next.js SaaS Studio (`Prateek_website` at `/rag/app`).

---

## 2. Architecture Topology

```text
                  [User Natural Language Requirement]
                                    │
                                    ▼
                 ┌───────────────────────────────────────┐
                 │     RequirementAnalyzer Service       │
                 │   (Match 16 Native Batteries via AST) │
                 └──────────────────┬────────────────────┘
                                    │
                         Is Custom Code Required?
                                   / \
                         NO      /     \   YES (or FDE Persona)
                               /         \
                              ▼           ▼
             [Return Zero-Code Battery] ┌───────────────────────────────────────┐
             [Configuration & Match % ] │     Hexagonal Metaprogrammer Engine   │
                                        │ (Synthesizes 6 Verified Code Slices)  │
                                        └──────────────────┬────────────────────┘
                                                           │
                                                           ▼
                                        ┌───────────────────────────────────────┐
                                        │    AstBoundaryValidator Security Gate │
                                        │   - 0 Framework Imports in Domain     │
                                        │   - Protocol Typing Enforced          │
                                        │   - No Dangerous exec/eval Calls      │
                                        └──────────────────┬────────────────────┘
                                                           │
                                                   Passed AST Gate?
                                                         / \
                                                YES    /     \   NO
                                                     /         \
                                                    ▼           ▼
                        ┌─────────────────────────────────┐   [Reject with Line-Level]
                        │      CodeScaffolderAdapter      │   [Violations Diagnostics]
                        │ Writes to src/plugins/custom/   │
                        └───────────────┬─────────────────┘
                                        │
                                        ▼
                        ┌─────────────────────────────────┐
                        │      PluginManager Adapter      │
                        │ Dynamic importlib + Fault Guard │
                        └───────┬─────────────────┬───────┘
                                │                 │
            ┌───────────────────┼─────────────────┼───────────────────┐
            ▼                   ▼                 ▼                   ▼
    [Dynamic REST Route]  [Battery Service] [Copilot Tool]    [Workflow Step]
  /v1/plugins/{id}/*       Battery #17+      Agent Injected    Step Execution
```

---

## 3. The 6 Hexagonal Code Slices

For every scaffolded plugin, the Metaprogrammer synthesizes a complete, production-grade Hexagonal directory structure under `apps/api/src/plugins/custom/{plugin_id}/`:

| Relative Path | Hexagonal Role | Invariants Enforced |
| :--- | :--- | :--- |
| `domain/abstractions.py` | Abstract Protocols & Entities | **Zero framework imports**. Pure Python protocols, dataclasses, and enums defining the domain contract. |
| `domain/service.py` | Pure Business Logic | Implements domain protocol. Encapsulates computational logic with zero external dependencies. |
| `adapters/custom_adapter.py` | Concrete Infrastructure | Implements concrete I/O, external network calls, database interaction, structured logging, and circuit breakers. |
| `routers/router.py` | FastAPI HTTP Router | Exposes REST endpoints (`POST /execute`, `GET /health`), validates Pydantic models, injects services via dependencies. |
| `tests/test_plugin.py` | Pytest Verification Suite | Unit tests verifying domain logic, boundary protocols, and error conditions. |
| `manifest.json` | Plugin Declaration | Serialized `PluginManifest` with id, version, hooks, secrets, latency profile, and tenant isolation level. |

---

## 4. Static AST Security Gate Invariant

Before any generated file touches the file system or runtime, `AstBoundaryValidator` parses its Abstract Syntax Tree via Python's standard `ast.parse()`:

### Prohibited Domain Imports (`FORBIDDEN_DOMAIN_IMPORTS`)
Domain modules (`domain/abstractions.py`, `domain/service.py`) are strictly prohibited from importing:
- Web frameworks: `fastapi`, `starlette`
- ORM/Database: `sqlalchemy`, `alembic`
- Task queues: `celery`, `redis`, `pika`
- HTTP Clients: `httpx`, `requests`, `aiohttp`
- LLM SDKs: `openai`, `anthropic`
- Cloud compute: `modal`, `bentoml`, `subprocess`

### Dangerous Builtins
Across all generated files, calls to `eval()`, `exec()`, `__import__()`, or `breakpoint()` immediately trigger an AST rejection.

---

## 5. Dynamic In-Process Mounting & Fault Barrier

The `PluginManager` discovers and mounts plugins dynamically:
1. **Discovery:** Scans `apps/api/src/plugins/custom/*/manifest.json`.
2. **AST Gating:** Validates all Python files against the AST boundary validator.
3. **Dynamic Import:** Uses `importlib.util.spec_from_file_location` and `module_from_spec` to import the router module.
4. **Router Mounting:** Mounts onto the FastAPI application at `/v1/plugins/{plugin_id}`.
5. **Fault Barrier:** If any plugin fails to import, has missing dependencies, or raises syntax errors, `PluginManager` logs a warning and marks the plugin `is_active: false` (`DISABLED`). **Core FastAPI operation and other tenants remain 100% unaffected.**

---

## 6. REST API Reference (`/v1/scaffold/*`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/scaffold/analyze` | Evaluates requirements against native batteries and returns match confidence. |
| `POST` | `/v1/scaffold/generate` | Synthesizes a full `ScaffoldingPlan` with 6 Hexagonal code slices and AST audit. |
| `POST` | `/v1/scaffold/verify-code` | Standalone endpoint to audit raw Python code against the AST security gate. |
| `POST` | `/v1/scaffold/apply` | Writes the verified plan to disk and hot-mounts the plugin into FastAPI. |
| `POST` | `/v1/scaffold/reload` | Re-scans the custom plugins directory and mounts newly added plugins. |
| `GET` | `/v1/scaffold/plugins` | Lists all discovered custom plugins with active statuses and hook declarations. |
| `DELETE` | `/v1/scaffold/plugins/{id}`| Unmounts and deletes a custom plugin directory from disk. |
| `GET` | `/v1/scaffold/status` | Reports platform status, active custom plugins, and Battery #17 telemetry. |

---

## 7. Standalone Developer CLI (`scripts/retriever_cli.py`)

A high-performance CLI is available for developers and CI/CD pipelines:

```bash
# Synthesize a custom plugin plan
python3 scripts/retriever_cli.py scaffold "Sync customer leads from HubSpot" --domain crm --persona fde_engineer

# Synthesize and write directly to disk
python3 scripts/retriever_cli.py scaffold "Sync customer leads from HubSpot" --domain crm --apply

# Verify AST boundaries of any Python file
python3 scripts/retriever_cli.py verify-ast apps/api/src/plugins/custom/crm_sync/domain/service.py --domain

# List all discovered custom plugins
python3 scripts/retriever_cli.py list-plugins

# Trigger in-process reload
python3 scripts/retriever_cli.py reload-plugins
```

---

## 8. Automated Verification & Testing

The implementation is verified by a 15-test Pytest suite (`apps/api/tests/test_scaffolding.py`) and a 9-test Vitest suite (`Prateek_website/src/components/rag/__tests__/FeatureStudioPanel.test.tsx`):

```bash
# Backend Pytest Suite
cd /Users/prateeksharma/Developer/retriever
./apps/api/.venv/bin/pytest apps/api/tests/test_scaffolding.py

# Frontend Vitest Suite
cd /Users/prateeksharma/Developer/Prateek_website
npx vitest run src/components/rag/__tests__/FeatureStudioPanel.test.tsx

# Ruff Style Check
./apps/api/.venv/bin/ruff check apps/api/src/domain/scaffolding/ apps/api/src/adapters/scaffolding/ apps/api/src/routers/scaffold.py
```
