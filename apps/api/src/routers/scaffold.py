"""FastAPI Router for Autonomous FDE Metaprogrammer & Scaffolding Studio (M97).

Exposes REST APIs for dual-persona capability matching, AST boundary verification,
automated code scaffolding, physical package emission, and runtime plugin hot-mounting.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from src.container import container
from src.domain.abstractions.scaffolding import (
    AstValidationResult,
    CustomPluginSummary,
    ScaffoldedFile,
    ScaffoldingPlan,
    UseCaseRequirement,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/scaffold",
    tags=["scaffolding", "metaprogrammer"],
)


@router.post("/analyze")
def analyze_scaffolding_requirement(payload: UseCaseRequirement) -> dict[str, Any]:
    """Analyze requirements against platform batteries and evaluate capability gap."""
    analyzer = container.requirement_analyzer
    recommendations = analyzer.analyze(payload)
    needs_custom = analyzer.assess_capability_gap(payload)

    return {
        "persona": payload.persona.value,
        "recommendations": [r.model_dump() for r in recommendations],
        "needs_custom_scaffold": needs_custom,
        "total_matched": len(recommendations),
    }


@router.post("/generate", response_model=ScaffoldingPlan)
def generate_scaffolding_plan(payload: UseCaseRequirement) -> ScaffoldingPlan:
    """Synthesize complete Hexagonal architecture plan with AST-verified code slices."""
    metaprogrammer = container.metaprogrammer
    return metaprogrammer.generate_plan(payload)


@router.post("/verify", response_model=AstValidationResult)
def verify_scaffolding_code(files: list[ScaffoldedFile]) -> AstValidationResult:
    """Validate arbitrary Python code files against Hexagonal AST boundary rules."""
    validator = container.boundary_checker
    return validator.validate_plugin_files(files)


@router.post("/apply")
def apply_scaffolding_plan(
    plan: ScaffoldingPlan,
    dry_run: bool = Query(default=False, description="Simulate emission without writing to disk"),
) -> dict[str, Any]:
    """Write verified plugin to `src/plugins/custom/{plugin_id}/` and hot-mount it."""
    # Pre-flight AST validation
    validator = container.boundary_checker
    validation_res = validator.validate_plugin_files(plan.scaffolded_files)
    if not validation_res.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"AST Security Gate Rejected Plugin: {'; '.join(validation_res.violations)}",
        )

    scaffolder = container.code_scaffolder
    write_res = scaffolder.apply_plan(plan, dry_run=dry_run)

    mounted = False
    if not dry_run:
        plugin_mgr = container.plugin_manager
        # Attempt to hot-mount into the runtime
        mount_res = plugin_mgr.mount_single_plugin(plan.plugin_id)
        mounted = mount_res.get("mounted", False)

    return {
        "success": True,
        "applied": True,
        "dry_run": dry_run,
        "plugin_id": plan.plugin_id,
        "files_written": write_res.get("files_written", []),
        "mounted": mounted,
    }


@router.post("/reload")
def reload_custom_plugins() -> dict[str, Any]:
    """Scan `src/plugins/custom/` and hot-reload all active plugins."""
    plugin_mgr = container.plugin_manager
    res = plugin_mgr.discover_and_mount_all()
    return {
        "success": True,
        "mounted_count": res.get("mounted_count", 0),
        "mounted_plugins": res.get("mounted_plugins", []),
        "errors": res.get("errors", []),
    }


@router.get("/plugins", response_model=list[CustomPluginSummary])
def list_custom_plugins() -> list[CustomPluginSummary]:
    """Return inventory of all discovered custom plugins on the filesystem."""
    plugin_mgr = container.plugin_manager
    return plugin_mgr.discover_plugins()


@router.delete("/plugins/{plugin_id}")
def delete_custom_plugin(plugin_id: str) -> dict[str, Any]:
    """Remove an installed custom plugin from disk and unmount it."""
    scaffolder = container.code_scaffolder
    plugin_mgr = container.plugin_manager

    deleted = scaffolder.delete_plugin(plugin_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found.",
        )

    plugin_mgr.unmount_plugin(plugin_id)
    return {"success": True, "deleted": True, "plugin_id": plugin_id}


@router.get("/status")
def get_scaffolding_status() -> dict[str, Any]:
    """Health check endpoint for Battery #17 (Autonomous FDE Metaprogrammer)."""
    return {
        "battery_id": "autonomous_fde_metaprogrammer",
        "name": "Autonomous FDE Metaprogrammer & Capability Studio",
        "status": "active",
        "supported_personas": ["business", "fde_engineer"],
        "ast_boundary_enforcement": True,
        "version": "v0.82.0",
        "milestone": "M97",
    }
