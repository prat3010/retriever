# ADR-019: Autonomous FDE Metaprogrammer & Self-Extending Capability Studio

**Status:** Accepted  
**Date:** 2026-09-05  
**Deciders:** Core Engineering Team, Forward Deployed Engineers (FDE)  
**Consulted:** System Architects, Multi-Tenancy Specialists, Security Auditors  
**Informed:** Enterprise Clients, Solution Architects, Platform Tenants  

---

## 1. Context and Problem Statement

As Retriever expanded to 16 enterprise batteries (including ColBERT reranking, GraphRAG HDBSCAN community clustering, Presidio PII redaction, Docling OCR, durable workflows, and serverless GPU vLLM/LoRA serving), a fundamental tension emerged between two distinct user profiles:

1. **Business Operators / Solution Architects:** Require rapid customization and workflow automation without writing Python code or managing deployment pipelines. They need to know which existing platform batteries fulfill their requirements and how to configure them with zero code.
2. **Forward Deployed Engineers (FDEs):** Build bespoke enterprise integrations, domain connectors (e.g. HubSpot, Salesforce, custom ERPs), proprietary scoring algorithms, or specialized vector transformers for paying enterprise clients. Historically, writing and mounting a custom capability required:
   - Manually authoring pure domain protocols and dataclasses.
   - Authoring infrastructure adapters and concrete services.
   - Authoring FastAPI routers and wiring dependency injection containers.
   - Authoring unit tests with Pytest.
   - Manually creating Git branches, writing Pull Request descriptions, and conducting code reviews to ensure domain purity.

Furthermore, dynamic loading of user-generated or agentic code in a shared multi-tenant SaaS runtime poses severe architectural and operational risks:
- **Architecture Erosion:** FDEs or AI agents might inadvertently import infrastructure frameworks (`fastapi`, `sqlalchemy`, `celery`, `redis`) directly into domain layers, violating Retriever's strict Hexagonal Architecture Boundary Rule.
- **Runtime Crashes (Poison Pill Plugins):** A syntax error or missing external dependency in a custom plugin could crash the FastAPI application during boot, causing downtime for all platform tenants.
- **File System Clutter & Merge Conflicts:** Auto-generated plugin files written directly into upstream source directories would trigger Git merge conflicts during platform upgrades.

Retriever required an **Autonomous Forward Deployed Engineering (FDE) Metaprogrammer & Self-Extending Capability Studio** capable of:
1. Solving requirements with zero code for business operators by matching against existing platform batteries.
2. Synthesizing full Hexagonal code slices (`abstractions.py`, `service.py`, `adapter.py`, `router.py`, `test_plugin.py`, `manifest.json`) for FDEs.
3. Enforcing static AST validation (0 framework imports in domain layers) before allowing code to touch disk or mount.
4. Dynamically discovering and mounting plugins into the running FastAPI app with an isolated fault barrier.
5. Providing 1-click community PR generation with Git branch naming and rich Markdown descriptions.
6. Registering the capability as Platform Battery #17 (`autonomous_fde_metaprogrammer`).

---

## 2. Decision Drivers

- **Dual-Persona Solution Engine:** Dual-mode interface supporting low-code battery matching for business operators and full AST-verified code synthesis for technical engineers.
- **Strict Hexagonal Boundary Invariant:** Domain code (`abstractions.py`, `service.py`) must never import framework libraries (`fastapi`, `sqlalchemy`, `redis`, etc.).
- **Runtime Fault Isolation & Zero-Downtime Hot Reload:** Custom plugins reside in `apps/api/src/plugins/custom/{plugin_id}/` (git-isolated). Plugin imports and route mounts are isolated so failures in one plugin never degrade core platform endpoints or other plugins.
- **Multi-Pathway Extensibility:** Generated plugins can register across 4 runtime pathways:
  1. Dynamic REST API router (`/v1/plugins/{plugin_id}/*`).
  2. Platform Battery Service registration (Battery #17+).
  3. Agentic Copilot tool injection (`IntegrationHooksDeclaration.agentic_tool`).
  4. Durable Workflow Engine step registration.
- **Open-Source Contribution Flywheel:** 1-click Git branch checkout (`feat/plugin-{plugin_id}`) and GitHub PR template generation to facilitate upstreaming verified capabilities into core platform batteries.

---

## 3. Considered Options

1. **Option 1: Sandboxed Python `exec()` / `eval()` at Runtime:**
   - *Downside:* Massive security vulnerability, untyped execution, impossible to debug, severe performance overhead, zero IDE autocomplete or Pytest verification.
2. **Option 2: External Microservice Generation & Kubernetes Helm Provisioning:**
   - *Downside:* Enormous DevOps overhead, high cloud resource consumption, latency penalties from network hops, excessive operational complexity for simple domain plugins.
3. **Option 3: Hexagonal Code Scaffolding with Static AST Verification & Dynamic Safe In-Process Mounting (Chosen):**
   - Synthesizes clean, typed Python files adhering to hexagonal boundaries.
   - Validates the Abstract Syntax Tree (AST) using Python's standard `ast` module before writing to disk.
   - Mounts dynamic FastAPI routers using `importlib.import_module` inside a try-catch fault barrier during lifespan.
   - Allows instant deployment to local workspace or 1-click export to GitHub Pull Requests.

---

## 4. Decision Outcome

We adopted **Option 3: Hexagonal Metaprogramming with AST Boundary Verification & Safe Dynamic Mounting**:

### 4.1 Domain Abstractions (`src/domain/abstractions/scaffolding.py`)
- `SolutionPersona`: Enum (`"business"`, `"fde_engineer"`).
- `PluginCategory`: Enum (`"connectors"`, `"retrieval"`, `"agentic_tool"`, `"workflow_step"`, `"safety_defense"`, `"computation"`, `"system_extensibility"`).
- `IntegrationHooksDeclaration`: Declarative hooks for REST router, battery service, agentic tool, and durable workflow step.
- `PluginManifest`: Strongly typed manifest defining metadata, dependencies, latency profile, and tenant isolation.
- `ScaffoldedFile`: Represents generated source files with relative paths, contents, and module types.
- `AstValidationResult`: Output of the AST security gate detailing syntax validity, violations, and forbidden imports.
- `ScaffoldingPlan`: The complete synthesis artifact containing recommendations, generated files, AST results, git branch, and PR markdown.
- Domain Protocols: `RequirementAnalyzerProtocol`, `AstBoundaryValidatorProtocol`, `MetaprogrammerProtocol`, `PrGeneratorProtocol`, `CodeScaffolderProtocol`, `PluginManagerProtocol`.

### 4.2 Domain Services (`src/domain/scaffolding/`)
- `RequirementAnalyzer`: Matches user prompt against the 16 platform batteries using tokenized keyword analysis and domain context. Determines if custom scaffolding is required.
- `AstBoundaryValidator`: Parses code with `ast.parse()`. Traverses `ast.Import` and `ast.ImportFrom` nodes. Enforces `FORBIDDEN_DOMAIN_IMPORTS` on domain files, checks for dangerous calls (`eval`, `exec`), and verifies type annotation presence.
- `Metaprogrammer`: Template-driven Hexagonal code generator producing 6 distinct slices:
  1. `domain/abstractions.py`: Pure Protocols, Dataclasses, and domain Enums (0 framework imports).
  2. `domain/service.py`: Business logic class implementing the protocol.
  3. `adapters/custom_adapter.py`: Concrete infrastructure adapter with error handling and logging.
  4. `routers/router.py`: FastAPI `APIRouter` with Pydantic request/response models and dependency injection.
  5. `tests/test_plugin.py`: Pytest unit tests verifying domain contracts and service logic.
  6. `manifest.json`: Serialization of `PluginManifest`.
- `PrGenerator`: Formats Git branch name (`feat/plugin-{plugin_id}`) and comprehensive GitHub Pull Request Markdown with architecture checklist, AST verification badge, and verification steps.

### 4.3 Infrastructure Adapters (`src/adapters/scaffolding/`)
- `CodeScaffolderAdapter`: Safely writes verified files to `apps/api/src/plugins/custom/{plugin_id}/`. Validates path containment within the plugin directory to prevent path traversal (`../`) attacks.
- `PluginManager`: Discovers installed plugins, reads `manifest.json`, validates files through `AstBoundaryValidator`, imports modules via `importlib.util.spec_from_file_location`, dynamically mounts routers onto FastAPI `app.include_router(router, prefix=f"/v1/plugins/{plugin_id}")`, and isolates any faulty plugin without crashing the server.

### 4.4 Database & Persistence Layer
- Added `custom_plugins` table in PostgreSQL with Alembic migration `j1k2l3m4n5o6_create_custom_plugins_table.py`.
- SQLAlchemy model `CustomPluginDb` tracking `plugin_id`, `tenant_id`, `display_name`, `version`, `category`, `persona`, `is_active`, `hooks`, and `manifest`.

### 4.5 CLI & Developer Experience
- Created `scripts/retriever_cli.py` supporting:
  - `retriever-cli scaffold "sync hubspot leads" --domain crm --persona fde_engineer --apply`
  - `retriever-cli verify-ast path/to/file.py --domain`
  - `retriever-cli list-plugins`
  - `retriever-cli reload-plugins`

### 4.6 Platform Battery Registration
- Registered Platform Battery #17 (`autonomous_fde_metaprogrammer`) under `BatteryCategory.SYSTEM_EXTENSIBILITY` in `apps/api/src/domain/batteries/battery_service.py`.
- Wired custom plugin discovery into `BatteryService` so installed plugins with `battery_service: true` dynamically appear in platform battery status queries and administrative dashboards.

### 4.7 Frontend Control Surfaces
- **Retriever Web Dashboard (`apps/web` at `/scaffold`):** Topbar integration, Dual-Persona toggle, battery recommendation list, AST security checklist, multi-file code viewer, 1-click Deploy, and installed plugins table.
- **SaaS App Studio (`Prateek_website` at `/rag/app`):** `FeatureStudioPanel.tsx` with Design System 2.0 dual-theme aesthetics, `<MagneticButton>`, `<NumberFlow>` animated metrics, `<Portal>` PR template modal, and full Vitest test suite.

---

## 5. Consequences

### Positive
- **Dramatic Acceleration of FDE Delivery:** New connectors and enterprise domain algorithms can be scaffolded, tested, and mounted in under 60 seconds instead of hours of boilerplate authoring.
- **Guaranteed Architectural Integrity:** AST validation mathematically prevents framework imports from creeping into domain layers.
- **Zero-Downtime Multi-Tenant Safety:** Broken plugins are marked `DISABLED` without affecting other tenants or taking down the FastAPI container.
- **Open-Source Velocity:** Any customer-built plugin can be transformed into an upstream platform pull request with one click.

### Negative / Trade-offs
- **In-Process Dynamic Import Limits:** Python `importlib` in a running process caches modules in `sys.modules`. Unloading or hot-reloading modified code requires careful cache clearing or container reloads.
- **Template Constraints:** Initial scaffolding produces standard Hexagonal CRUD and processing patterns. Complex distributed consensus or multi-service choreography requires subsequent FDE refinement.
