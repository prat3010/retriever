#!/usr/bin/env python3
"""Retriever CLI (High-Octane Developer & FDE Scaffolding Edition - M97).

Provides command-line autonomous scaffolding, AST boundary verification,
and custom capability lifecycle management for self-hosted and CI environments.

Usage:
  # Analyze and scaffold a custom capability
  python3 scripts/retriever_cli.py scaffold --prompt "Sync HubSpot deals" --domain crm --persona fde_engineer --apply

  # Verify Python code against Hexagonal AST boundaries
  python3 scripts/retriever_cli.py verify apps/api/src/domain/

  # List all installed custom plugins
  python3 scripts/retriever_cli.py plugins
"""

import argparse
from pathlib import Path
import sys

# Ensure apps/api is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
API_SRC = REPO_ROOT / "apps" / "api"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from src.container import boundary_checker, code_scaffolder, metaprogrammer, plugin_manager  # noqa: E402
from src.domain.abstractions.scaffolding import SolutionPersona, UseCaseRequirement  # noqa: E402


def cmd_scaffold(args: argparse.Namespace) -> int:
    """Generate scaffolding plan and optionally apply to disk."""
    persona = SolutionPersona(args.persona)
    req = UseCaseRequirement(
        prompt=args.prompt,
        target_domain=args.domain,
        persona=persona,
    )

    print(f"\n🧠 [Metaprogrammer] Synthesizing capability for: '{args.prompt}' (Persona: {persona.value})")
    plan = metaprogrammer.generate_plan(req)

    print(f"\n📦 Plugin ID: {plan.plugin_id} ({plan.display_name})")
    print(f"📁 Category: {plan.manifest.category.value}")
    print(f"🛡️  AST Boundary Check: {'✅ PASSED' if plan.ast_audit_passed else '❌ FAILED'}")

    if plan.recommended_batteries:
        print("\n🔋 Matched Active Platform Batteries:")
        for b in plan.recommended_batteries:
            print(f"  • {b.battery_name} (Confidence: {int(b.match_confidence * 100)}%)")

    print(f"\n📝 Generated {len(plan.scaffolded_files)} Hexagonal Code Slices:")
    for f in plan.scaffolded_files:
        print(f"  • {f.rel_path} ({f.module_type.value})")

    if args.apply:
        print("\n🚀 Writing files to `src/plugins/custom/`...")
        res = code_scaffolder.apply_plan(plan, dry_run=args.dry_run)
        print(f"✅ Successfully wrote {len(res['files_written'])} files to {res['target_dir']}")
        mount_res = plugin_manager.mount_single_plugin(plan.plugin_id)
        if mount_res.get("mounted"):
            print(f"⚡ Hot-mounted into runtime at `/v1/plugins/{plan.plugin_id}/*`")
        else:
            print(f"⚠️  Mount note: {mount_res.get('error')}")

    if args.print_pr:
        print("\n--- 📋 Community PR Template ---")
        print(plan.pull_request_markdown)

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify source code file or directory against Hexagonal AST boundaries."""
    target = Path(args.path).resolve()
    if not target.exists():
        print(f"❌ Error: Path '{target}' does not exist.")
        return 1

    py_files = [target] if target.is_file() else list(target.rglob("*.py"))
    print(f"\n🛡️  [AST Boundary Gate] Inspecting {len(py_files)} Python files in {target}...")

    violations_found = 0
    for f in py_files:
        is_domain = "domain" in str(f)
        code = f.read_text(encoding="utf-8")
        res = boundary_checker.validate_code(code, filename=f.name, is_domain=is_domain)
        if not res.is_valid:
            violations_found += len(res.violations)
            print(f"\n❌ Violations in {f}:")
            for v in res.violations:
                print(f"  • {v}")

    if violations_found == 0:
        print(f"✅ All {len(py_files)} files strictly conform to Hexagonal boundaries (0 framework imports in domain).")
        return 0
    else:
        print(f"\n🚨 Failed with {violations_found} architectural boundary violations.")
        return 1


def cmd_plugins(args: argparse.Namespace) -> int:
    """List installed custom plugins."""
    plugins = plugin_manager.discover_plugins()
    print(f"\n🔌 Discovered {len(plugins)} Custom Plugin(s):")
    for p in plugins:
        status_icon = "🟢" if p.is_active else "⚪"
        print(f"  {status_icon} [{p.plugin_id}] {p.display_name} (v{p.version}) - {p.category}")
        print(f"     Description: {p.description}")
        if p.hooks.api_router:
            print(f"     Route: /v1/plugins/{p.plugin_id}/*")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Retriever FDE Scaffolding & Extensibility CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scaffold command
    p_scaffold = subparsers.add_parser("scaffold", help="Generate custom capability slices")
    p_scaffold.add_argument("--prompt", required=True, help="Requirement description")
    p_scaffold.add_argument("--domain", default="general", help="Target domain context")
    p_scaffold.add_argument("--persona", default="fde_engineer", choices=["business", "fde_engineer"])
    p_scaffold.add_argument("--apply", action="store_true", help="Write generated files to disk")
    p_scaffold.add_argument("--dry-run", action="store_true", help="Dry run write operations")
    p_scaffold.add_argument("--print-pr", action="store_true", help="Print community PR markdown template")

    # Verify command
    p_verify = subparsers.add_parser("verify", help="Check AST Hexagonal boundaries")
    p_verify.add_argument("path", help="Path to Python file or directory")

    # Plugins command
    subparsers.add_parser("plugins", help="List installed custom plugins")

    args = parser.parse_args()

    if args.command == "scaffold":
        return cmd_scaffold(args)
    elif args.command == "verify":
        return cmd_verify(args)
    elif args.command == "plugins":
        return cmd_plugins(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
