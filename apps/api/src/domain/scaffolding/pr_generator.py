"""Pull Request Template Generator Domain Service (M97).

Generates standardized Git branch names and comprehensive GitHub Pull Request
markdown descriptions for contributing verified scaffolded capabilities back
to the upstream open-source core repository. Zero framework imports.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.abstractions.scaffolding import ScaffoldingPlan


class PullRequestGenerator:
    """Pure domain service generating community pull request artifacts."""

    @staticmethod
    def generate_branch_name(plugin_id: str) -> str:
        """Create clean git feature branch identifier."""
        clean_slug = plugin_id.strip().lower().replace("_", "-").replace(" ", "-")
        return f"feat/plugin-{clean_slug}"

    @classmethod
    def generate_pr_markdown(cls, plan: "ScaffoldingPlan") -> str:
        """Generate comprehensive GitHub Pull Request markdown text."""
        files_list = "\n".join([f"- `{f.rel_path}` ({f.module_type.value})" for f in plan.scaffolded_files])

        hooks_summary = []
        if plan.manifest.integration_hooks.api_router:
            hooks_summary.append(f"- **FastAPI Route Mount:** `/v1/plugins/{plan.plugin_id}/*`")
        if plan.manifest.integration_hooks.battery_service:
            hooks_summary.append(f"- **Battery Service Registration:** Platform Battery `{plan.plugin_id}`")
        if plan.manifest.integration_hooks.agentic_tool:
            hooks_summary.append(
                f"- **Agentic Copilot Tool:** `{plan.manifest.integration_hooks.agentic_tool.name}`"
            )
        if plan.manifest.integration_hooks.workflow_step:
            hooks_summary.append(
                f"- **Durable Workflow Step:** `{plan.manifest.integration_hooks.workflow_step}`"
            )

        hooks_text = "\n".join(hooks_summary) if hooks_summary else "- Standalone Domain Service"

        return f"""# 🚀 [Plugin Contribution] {plan.display_name} (`{plan.plugin_id}`)

> **Generated via Autonomous FDE Metaprogrammer (Milestone 97 / v0.82.0)**  
> **Conformance Status:** ✅ AST Boundary Verified • 0 Framework Imports in Domain • Type Checked

---

## 📋 Capability Overview

{plan.description}

* **Plugin ID:** `{plan.plugin_id}`
* **Category:** `{plan.manifest.category.value}`
* **Target Domain:** `{plan.persona.value}`
* **Algorithm / Design Foundation:** {plan.manifest.algorithm_foundation}
* **Latency Profile:** `{plan.manifest.latency_profile}`

---

## 🏛️ Architectural Topology & Generated Slices

This capability conforms strictly to Retriever's Hexagonal Architecture specifications:

```text
src/plugins/custom/{plan.plugin_id}/
├── manifest.json              <-- Identity, hooks, and required secrets
├── domain/
│   ├── abstractions.py        <-- Pure protocols and Pydantic DTOs (0 framework imports)
│   └── service.py             <-- Pure domain logic & computation
├── adapters/
│   └── adapter.py             <-- Concrete infrastructure adapter
├── router.py                  <-- FastAPI APIRouter with tenant authentication
└── tests/
    └── test_plugin.py         <-- Unit tests & AST boundary assertion suite
```

### Generated Files
{files_list}

---

## 🔌 Runtime Integration Hooks

{hooks_text}

---

## 🧪 Verification & Automated Tests

All files have been verified through static AST parsing (`AstBoundaryValidator`) with **zero architectural leaks**:
* [x] **Hexagonal Boundary:** Domain imports neither `fastapi` nor `sqlalchemy`.
* [x] **Multi-Tenancy Isolation:** Context scoping verified for `tenant_id`.
* [x] **Self-Contained Tests:** Run the included Pytest suite:
  ```bash
  pytest src/plugins/custom/{plan.plugin_id}/tests/test_plugin.py -v
  ```

---

## 📝 Contributor Checklist

- [x] Conforms to `.agents/rules/patterns.md` architectural conventions.
- [x] Zero hardcoded secrets (secrets read from tenant configuration or environment).
- [x] Includes self-contained Pytest tests.
- [x] Verified via Autonomous Metaprogrammer AST gate.
"""
