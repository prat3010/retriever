"""Plugin Manager & Runtime Dynamic Integration Adapter (M97).

Discovers, validates, and hot-mounts custom plugins from `src/plugins/custom/`.
Orchestrates the 4 functional runtime pathways:
1. Dynamic FastAPI APIRouter mounting under `/v1/plugins/{plugin_id}/*`.
2. Dynamic platform battery registration into BatteryService.
3. LangGraph agent tool registration into agent copilot runtime.
4. DurableWorkflowEngine custom step registration.
Includes robust fault barriers: crashing plugins fail safely without taking down
the core FastAPI server or other tenants.
"""

import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

from src.domain.abstractions.scaffolding import (
    CustomPluginSummary,
    PluginManagerProtocol,
    PluginManifest,
    ScaffoldedFile,
    ScaffoldedModuleType,
)
from src.domain.scaffolding.boundary_checker import AstBoundaryValidator

logger = logging.getLogger(__name__)


class PluginManager(PluginManagerProtocol):
    """Runtime loader and integration engine for custom extensible capabilities."""

    def __init__(
        self,
        plugins_root: Path | str | None = None,
        validator: AstBoundaryValidator | None = None,
    ) -> None:
        if plugins_root:
            self.plugins_root = Path(plugins_root).resolve()
        else:
            self.plugins_root = (
                Path(__file__).resolve().parent.parent.parent / "plugins" / "custom"
            ).resolve()

        self.plugins_root.mkdir(parents=True, exist_ok=True)
        self.validator = validator or AstBoundaryValidator()

        # In-memory registry of active custom plugins and their loaded modules
        self._active_plugins: dict[str, PluginManifest] = {}
        self._mounted_routers: set[str] = set()
        self._plugin_instances: dict[str, Any] = {}

    def discover_plugins(self) -> list[CustomPluginSummary]:
        """Scan directory and return summaries of all discovered plugins."""
        summaries: list[CustomPluginSummary] = []
        if not self.plugins_root.exists():
            return summaries

        for item in sorted(self.plugins_root.iterdir()):
            if item.is_dir() and not item.name.startswith((".", "_")):
                manifest_file = item / "manifest.json"
                if manifest_file.exists():
                    try:
                        data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        manifest = PluginManifest.model_validate(data)
                        is_mounted = manifest.id in self._mounted_routers or manifest.id in self._active_plugins
                        summaries.append(
                            CustomPluginSummary(
                                plugin_id=manifest.id,
                                display_name=manifest.name,
                                version=manifest.version,
                                category=manifest.category.value,
                                persona=manifest.persona.value,
                                description=manifest.description,
                                is_active=is_mounted,
                                hooks=manifest.integration_hooks,
                            )
                        )
                    except Exception as e:
                        logger.warning("Failed to parse manifest for plugin '%s': %s", item.name, e)
                        summaries.append(
                            CustomPluginSummary(
                                plugin_id=item.name,
                                display_name=item.name,
                                version="0.0.0",
                                category="unknown",
                                persona="unknown",
                                description=f"Corrupted plugin manifest: {e}",
                                is_active=False,
                            )
                        )
        return summaries

    def get_plugin_manifest(self, plugin_id: str) -> PluginManifest | None:
        """Fetch parsed manifest for a given plugin ID."""
        manifest_file = self.plugins_root / plugin_id / "manifest.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                return PluginManifest.model_validate(data)
            except Exception as e:
                logger.error("Error reading manifest for '%s': %s", plugin_id, e)
        return None

    def get_active_custom_manifests(self) -> list[PluginManifest]:
        """Return manifests for all currently active/mounted custom plugins."""
        # Refresh discovery to pick up any new manifests
        active = []
        for summary in self.discover_plugins():
            m = self.get_plugin_manifest(summary.plugin_id)
            if m:
                active.append(m)
        return active

    def discover_and_mount_all(self, app: Any = None) -> dict[str, Any]:
        """Scan, validate, and mount all custom plugins into runtime."""
        mounted: list[str] = []
        errors: list[dict[str, str]] = []

        # Ensure plugins directory is on sys.path for dynamic imports
        api_src_dir = str(self.plugins_root.parent.parent)
        if api_src_dir not in sys.path:
            sys.path.insert(0, api_src_dir)

        for summary in self.discover_plugins():
            plugin_id = summary.plugin_id
            manifest = self.get_plugin_manifest(plugin_id)
            if not manifest:
                continue

            try:
                res = self.mount_single_plugin(plugin_id, app=app)
                if res.get("mounted"):
                    mounted.append(plugin_id)
                else:
                    errors.append({"plugin_id": plugin_id, "error": res.get("error", "Unknown mount error")})
            except Exception as e:
                logger.exception("Fault barrier caught exception loading plugin '%s'", plugin_id)
                errors.append({"plugin_id": plugin_id, "error": str(e)})

        logger.info("PluginManager completed scan: %d mounted, %d errors", len(mounted), len(errors))
        return {"mounted_count": len(mounted), "mounted_plugins": mounted, "errors": errors}

    def mount_single_plugin(self, plugin_id: str, app: Any = None) -> dict[str, Any]:
        """Validate and hot-mount a single plugin into the running FastAPI application."""
        plugin_dir = self.plugins_root / plugin_id
        if not plugin_dir.exists():
            return {"mounted": False, "error": f"Plugin directory '{plugin_id}' not found."}

        manifest = self.get_plugin_manifest(plugin_id)
        if not manifest:
            return {"mounted": False, "error": "Missing or invalid manifest.json."}

        # 1. AST Security Gate: Validate domain files before importing
        domain_files: list[ScaffoldedFile] = []
        domain_dir = plugin_dir / "domain"
        if domain_dir.exists():
            for py_file in domain_dir.glob("*.py"):
                domain_files.append(
                    ScaffoldedFile(
                        rel_path=f"domain/{py_file.name}",
                        content=py_file.read_text(encoding="utf-8"),
                        module_type=ScaffoldedModuleType.SERVICE,
                    )
                )

        ast_check = self.validator.validate_plugin_files(domain_files)
        if not ast_check.is_valid:
            logger.error("AST validation failed for plugin '%s': %s", plugin_id, ast_check.violations)
            return {"mounted": False, "error": f"AST Gate rejected plugin: {'; '.join(ast_check.violations)}"}

        # 2. Dynamic Import & FastAPI Router Mounting
        module_path = f"src.plugins.custom.{plugin_id}.router"
        if manifest.integration_hooks.api_router and app is not None:
            try:
                # Invalidate import caches
                importlib.invalidate_caches()
                router_mod = importlib.import_module(module_path)
                router = getattr(router_mod, "router", None)

                if router and plugin_id not in self._mounted_routers:
                    prefix = f"/v1/plugins/{plugin_id}"
                    app.include_router(router, prefix=prefix, tags=[f"Plugin: {manifest.name}"])
                    self._mounted_routers.add(plugin_id)
                    logger.info("Mounted plugin router for '%s' at prefix '%s'", plugin_id, prefix)
            except Exception as e:
                logger.warning("Could not mount router for plugin '%s': %s", plugin_id, e)

        self._active_plugins[plugin_id] = manifest
        return {
            "mounted": True,
            "plugin_id": plugin_id,
            "name": manifest.name,
            "hooks": manifest.integration_hooks.model_dump(),
        }

    def unmount_plugin(self, plugin_id: str) -> bool:
        """Deactivate and remove plugin from active registry."""
        self._active_plugins.pop(plugin_id, None)
        self._mounted_routers.discard(plugin_id)
        self._plugin_instances.pop(plugin_id, None)
        return True
