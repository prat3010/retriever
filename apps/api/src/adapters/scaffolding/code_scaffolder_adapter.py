"""Code Scaffolder File System Adapter (M97).

Safely manages physical creation, file writing, and deletion of custom
scaffolded plugin packages in `src/plugins/custom/{plugin_id}/`.
Includes strict path traversal guards preventing directory escape.
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Any

from src.domain.abstractions.scaffolding import ScaffoldingPlan

logger = logging.getLogger(__name__)


class CodeScaffolderAdapter:
    """File system infrastructure adapter writing and removing plugin packages."""

    def __init__(self, plugins_root: Path | str | None = None) -> None:
        if plugins_root:
            self.plugins_root = Path(plugins_root).resolve()
        else:
            # Default to apps/api/src/plugins/custom relative to this file
            self.plugins_root = (
                Path(__file__).resolve().parent.parent.parent / "plugins" / "custom"
            ).resolve()

        self.plugins_root.mkdir(parents=True, exist_ok=True)

    def _validate_plugin_id(self, plugin_id: str) -> None:
        """Ensure plugin_id is a safe alphanumeric snake_case identifier."""
        if not re.match(r"^[a-zA-Z0-9_]+$", plugin_id):
            raise ValueError(f"Invalid plugin_id '{plugin_id}'. Must be alphanumeric snake_case.")

    def apply_plan(self, plan: ScaffoldingPlan, dry_run: bool = False) -> dict[str, Any]:
        """Write all scaffolded files to disk in the isolated plugin directory."""
        self._validate_plugin_id(plan.plugin_id)

        target_dir = (self.plugins_root / plan.plugin_id).resolve()
        # Security sanity check: target_dir must be strictly a child of plugins_root
        if not str(target_dir).startswith(str(self.plugins_root)):
            raise PermissionError("Path traversal detected: Cannot write outside plugins root.")

        written_paths: list[str] = []

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            # Create package __init__.py if missing
            init_file = target_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f'"""Custom Plugin: {plan.display_name}"""\n', encoding="utf-8")
                written_paths.append("__init__.py")

        for f in plan.scaffolded_files:
            rel = f.rel_path.strip()
            if ".." in rel or rel.startswith("/") or rel.startswith("\\"):
                raise PermissionError(f"Path traversal detected in file path '{rel}'.")

            file_target = (target_dir / rel).resolve()
            if not str(file_target).startswith(str(target_dir)):
                raise PermissionError(f"Path traversal detected for '{rel}'.")

            if not dry_run:
                file_target.parent.mkdir(parents=True, exist_ok=True)
                file_target.write_text(f.content, encoding="utf-8")

            written_paths.append(rel)

        logger.info(
            "Scaffolder applied %d files for plugin '%s' (dry_run=%s)",
            len(written_paths),
            plan.plugin_id,
            dry_run,
        )

        return {
            "applied": True,
            "dry_run": dry_run,
            "plugin_id": plan.plugin_id,
            "target_dir": str(target_dir),
            "files_written": written_paths,
        }

    def delete_plugin(self, plugin_id: str) -> bool:
        """Remove an existing custom plugin package from disk."""
        self._validate_plugin_id(plugin_id)
        target_dir = (self.plugins_root / plugin_id).resolve()

        if not str(target_dir).startswith(str(self.plugins_root)):
            raise PermissionError("Path traversal detected.")

        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)
            logger.info("Deleted custom plugin directory '%s'", target_dir)
            return True

        return False
