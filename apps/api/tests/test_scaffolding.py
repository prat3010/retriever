"""Comprehensive Automated Pytest Suite for Milestone 97.

Verifies:
1. Pure Hexagonal Domain Boundary Conformance (0 framework imports in domain).
2. Requirement Analyzer dual-persona matching and capability gap detection.
3. AST Boundary Checker violation detection and security gates.
4. Autonomous Metaprogrammer code synthesis across all 6 Hexagonal slices.
5. PR Template Generator markdown and git branch formatting.
6. Code Scaffolder file emission, traversal protection, and cleanup.
7. Plugin Manager runtime discovery, AST gating, and dynamic mounting.
8. Platform Battery #17 registration in BatteryService.
9. FastAPI REST Endpoints via TestClient (/v1/scaffold/*).
"""

import ast
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.scaffolding.code_scaffolder_adapter import CodeScaffolderAdapter
from src.adapters.scaffolding.plugin_manager import PluginManager
from src.container import container
from src.domain.abstractions.batteries import BatteryCategory, BatteryStatus
from src.domain.abstractions.scaffolding import (
    ScaffoldedFile,
    ScaffoldedModuleType,
    SolutionPersona,
    UseCaseRequirement,
)
from src.domain.scaffolding.boundary_checker import AstBoundaryValidator
from src.domain.scaffolding.metaprogrammer import AutonomousMetaprogrammer
from src.domain.scaffolding.requirement_analyzer import RequirementAnalyzer
from src.main import app

client = TestClient(app)


# ── 1. Hexagonal Boundary Conformance Test ──────────────────────────────────


def test_scaffolding_hexagonal_boundary() -> None:
    """Ensure all files under domain/abstractions and domain/scaffolding have 0 framework imports."""
    domain_dir = Path(__file__).resolve().parent.parent / "src" / "domain"
    scaffold_domain_files = [
        domain_dir / "abstractions" / "scaffolding.py",
        domain_dir / "scaffolding" / "requirement_analyzer.py",
        domain_dir / "scaffolding" / "boundary_checker.py",
        domain_dir / "scaffolding" / "metaprogrammer.py",
        domain_dir / "scaffolding" / "pr_generator.py",
    ]
    forbidden = {"fastapi", "sqlalchemy", "celery", "redis", "pika", "httpx", "modal", "bentoml", "subprocess"}

    for f in scaffold_domain_files:
        assert f.exists(), f"Domain file {f} must exist"
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    root = name.name.split(".")[0]
                    assert root not in forbidden, f"Hexagonal violation in {f.name}: imported {root}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    assert root not in forbidden, f"Hexagonal violation in {f.name}: imported {root}"


# ── 2. Requirement Analyzer Tests ───────────────────────────────────────────


def test_requirement_analyzer_business_flow() -> None:
    """Verify business prompt matches existing batteries with high confidence."""
    analyzer = RequirementAnalyzer()
    req = UseCaseRequirement(
        prompt="Scan PDF medical forms, redact patient PII with HIPAA compliance, and alert Slack",
        target_domain="healthcare",
        persona=SolutionPersona.BUSINESS,
    )
    matches = analyzer.analyze(req)
    matched_ids = [m.battery_id for m in matches]

    assert "docling_layout_ocr" in matched_ids
    assert "compliance_vault_pii" in matched_ids
    assert "slack_workspace_bot" in matched_ids
    assert all(m.match_confidence > 0.5 for m in matches)

    # For business persona with matching batteries, capability gap is False
    assert analyzer.assess_capability_gap(req) is False


def test_requirement_analyzer_fde_gap() -> None:
    """Verify FDE persona or custom integration prompts trigger capability gap."""
    analyzer = RequirementAnalyzer()
    req = UseCaseRequirement(
        prompt="Custom HubSpot deal synchronizer with metadata filters and webhook trigger",
        target_domain="crm",
        persona=SolutionPersona.FDE_ENGINEER,
    )
    assert analyzer.assess_capability_gap(req) is True


# ── 3. AST Boundary Checker Tests ───────────────────────────────────────────


def test_boundary_checker_detects_forbidden_imports() -> None:
    """Verify validator flags framework imports in domain code."""
    validator = AstBoundaryValidator()

    bad_domain_code = """
from fastapi import APIRouter
import sqlalchemy

def do_logic() -> str:
    return "logic"
"""
    res = validator.validate_code(bad_domain_code, filename="bad_service.py", is_domain=True)
    assert res.is_valid is False
    assert "fastapi" in res.forbidden_imports_found
    assert "sqlalchemy" in res.forbidden_imports_found
    assert len(res.violations) >= 2


def test_boundary_checker_detects_dangerous_eval() -> None:
    """Verify validator blocks dangerous eval calls."""
    validator = AstBoundaryValidator()
    dangerous_code = """
def run_command(cmd: str) -> None:
    eval(cmd)
"""
    res = validator.validate_code(dangerous_code, filename="eval_test.py", is_domain=False)
    assert res.is_valid is False
    assert any("eval" in v for v in res.violations)


def test_boundary_checker_passes_clean_code() -> None:
    """Verify validator passes clean, type-annotated code."""
    validator = AstBoundaryValidator()
    clean_code = """
from pydantic import BaseModel

class CleanDTO(BaseModel):
    id: str

def clean_function(val: str) -> str:
    return val.strip()
"""
    res = validator.validate_code(clean_code, filename="clean.py", is_domain=True)
    assert res.is_valid is True
    assert len(res.violations) == 0


# ── 4. Metaprogrammer Code Generation Tests ─────────────────────────────────


def test_metaprogrammer_generates_complete_slices() -> None:
    """Verify metaprogrammer synthesizes all 6 Hexagonal slices."""
    metaprog = AutonomousMetaprogrammer()
    req = UseCaseRequirement(
        prompt="Sync Jira issue tickets and enrich with priority embeddings",
        target_domain="devops",
        persona=SolutionPersona.FDE_ENGINEER,
    )
    plan = metaprog.generate_plan(req)

    assert plan.plugin_id == "jira_issue" or "jira" in plan.plugin_id
    assert plan.needs_custom_scaffold is True
    assert len(plan.scaffolded_files) == 6

    paths = [f.rel_path for f in plan.scaffolded_files]
    assert "manifest.json" in paths
    assert "domain/abstractions.py" in paths
    assert "domain/service.py" in paths
    assert "adapters/adapter.py" in paths
    assert "router.py" in paths
    assert "tests/test_plugin.py" in paths

    # Verify AST conformance
    assert plan.ast_audit_passed is True
    assert plan.git_branch_name.startswith("feat/plugin-")
    assert "Autonomous FDE Metaprogrammer" in plan.pull_request_markdown


# ── 5. Code Scaffolder File System Tests ─────────────────────────────────────


def test_code_scaffolder_apply_and_traversal_guard() -> None:
    """Verify scaffolder writes files safely and rejects path traversal."""
    with tempfile.TemporaryDirectory() as temp_dir:
        scaffolder = CodeScaffolderAdapter(plugins_root=temp_dir)
        metaprog = AutonomousMetaprogrammer()

        req = UseCaseRequirement(
            prompt="Stripe charge auditor and tax classifier",
            target_domain="fintech",
            persona=SolutionPersona.FDE_ENGINEER,
        )
        plan = metaprog.generate_plan(req)

        # Apply plan
        res = scaffolder.apply_plan(plan, dry_run=False)
        assert res["applied"] is True
        assert len(res["files_written"]) >= 6

        plugin_folder = Path(temp_dir) / plan.plugin_id
        assert plugin_folder.exists()
        assert (plugin_folder / "manifest.json").exists()
        assert (plugin_folder / "domain" / "service.py").exists()

        # Path traversal guard test
        bad_plan = plan.model_copy(deep=True)
        bad_plan.scaffolded_files.append(
            ScaffoldedFile(
                rel_path="../escaped.py",
                content="print('bad')",
                module_type=ScaffoldedModuleType.SERVICE,
            )
        )
        with pytest.raises(PermissionError):
            scaffolder.apply_plan(bad_plan, dry_run=False)

        # Delete plugin test
        deleted = scaffolder.delete_plugin(plan.plugin_id)
        assert deleted is True
        assert not plugin_folder.exists()


# ── 6. Plugin Manager Dynamic Loading Tests ─────────────────────────────────


def test_plugin_manager_discovery_and_mounting() -> None:
    """Verify plugin manager discovers plugins and executes fault barriers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        scaffolder = CodeScaffolderAdapter(plugins_root=temp_dir)
        manager = PluginManager(plugins_root=temp_dir)
        metaprog = AutonomousMetaprogrammer()

        req = UseCaseRequirement(
            prompt="HubSpot deal pipeline sync",
            target_domain="crm",
            persona=SolutionPersona.FDE_ENGINEER,
        )
        plan = metaprog.generate_plan(req)
        scaffolder.apply_plan(plan, dry_run=False)

        summaries = manager.discover_plugins()
        assert len(summaries) == 1
        assert summaries[0].plugin_id == plan.plugin_id

        manifest = manager.get_plugin_manifest(plan.plugin_id)
        assert manifest is not None
        assert manifest.name == plan.display_name

        # Mount test
        mount_res = manager.mount_single_plugin(plan.plugin_id)
        assert mount_res["mounted"] is True

        manager.unmount_plugin(plan.plugin_id)


# ── 7. Platform Battery #17 Registration ────────────────────────────────────


def test_battery_service_has_metaprogrammer_battery() -> None:
    """Verify Battery #17 is registered in BatteryService catalog under SYSTEM_EXTENSIBILITY."""
    battery_svc = container.battery_service
    resp = battery_svc.get_platform_batteries()

    battery_17 = next(
        (b for b in resp.batteries if b.id == "autonomous_fde_metaprogrammer"),
        None,
    )
    assert battery_17 is not None, "autonomous_fde_metaprogrammer must be registered"
    assert battery_17.status == BatteryStatus.ACTIVE
    assert battery_17.category == BatteryCategory.SYSTEM_EXTENSIBILITY
    assert "M97" in battery_17.milestone
    assert "AST-Driven Program Synthesis" in battery_17.algorithm_foundation


# ── 8. FastAPI REST Endpoints via TestClient ────────────────────────────────


def test_scaffold_analyze_api() -> None:
    """Test POST /v1/scaffold/analyze endpoint."""
    res = client.post(
        "/v1/scaffold/analyze",
        json={
            "prompt": "Scan clinical trial forms and redact patient identifiers",
            "target_domain": "medical",
            "persona": "business",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["persona"] == "business"
    assert data["total_matched"] >= 1
    assert any(b["battery_id"] == "docling_layout_ocr" for b in data["recommendations"])


def test_scaffold_generate_api() -> None:
    """Test POST /v1/scaffold/generate endpoint."""
    res = client.post(
        "/v1/scaffold/generate",
        json={
            "prompt": "Custom Linear issue tracker sync",
            "target_domain": "engineering",
            "persona": "fde_engineer",
        },
    )
    assert res.status_code == 200
    plan = res.json()
    assert plan["needs_custom_scaffold"] is True
    assert plan["ast_audit_passed"] is True
    assert len(plan["scaffolded_files"]) == 6
    assert plan["git_branch_name"].startswith("feat/plugin-")


def test_scaffold_verify_api() -> None:
    """Test POST /v1/scaffold/verify endpoint."""
    res = client.post(
        "/v1/scaffold/verify",
        json=[
            {
                "rel_path": "domain/test.py",
                "content": "from pydantic import BaseModel\nclass Good(BaseModel):\n    pass\n",
                "module_type": "abstractions",
            }
        ],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["syntax_valid"] is True


def test_scaffold_status_api() -> None:
    """Test GET /v1/scaffold/status health endpoint."""
    res = client.get("/v1/scaffold/status")
    assert res.status_code == 200
    data = res.json()
    assert data["battery_id"] == "autonomous_fde_metaprogrammer"
    assert data["status"] == "active"
    assert data["milestone"] == "M97"


def test_scaffold_plugins_crud_api() -> None:
    """Test GET /v1/scaffold/plugins endpoint."""
    res = client.get("/v1/scaffold/plugins")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
