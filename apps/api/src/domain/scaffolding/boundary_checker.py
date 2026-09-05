"""AST Boundary Validator Domain Service (M97).

Parses Python source code using Python's standard `ast` module and enforces
strict Hexagonal architecture boundaries and security gates. Verifies that
domain-level modules contain zero infrastructure imports and follow typing
standards before code can be written to disk or mounted into the runtime.
Zero infrastructure or framework imports.
"""

import ast
from typing import ClassVar

from src.domain.abstractions.scaffolding import (
    AstBoundaryValidatorProtocol,
    AstValidationResult,
    ScaffoldedFile,
    ScaffoldedModuleType,
)


class AstBoundaryValidator(AstBoundaryValidatorProtocol):
    """Pure domain AST parser and architecture boundary validator."""

    # Prohibited imports in pure domain layers (Hexagonal boundary enforcement)
    FORBIDDEN_DOMAIN_IMPORTS: ClassVar[set[str]] = {
        "fastapi",
        "starlette",
        "sqlalchemy",
        "alembic",
        "celery",
        "redis",
        "pika",
        "httpx",
        "requests",
        "aiohttp",
        "openai",
        "anthropic",
        "modal",
        "bentoml",
        "subprocess",
    }

    # Prohibited dangerous constructs across all scaffolded code
    DANGEROUS_FUNCTIONS: ClassVar[set[str]] = {
        "eval",
        "exec",
        "__import__",
        "breakpoint",
    }

    def validate_code(
        self,
        code: str,
        filename: str = "snippet.py",
        is_domain: bool = True,
    ) -> AstValidationResult:
        """Inspect source code string and assert Hexagonal and security rules."""
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            return AstValidationResult(
                is_valid=False,
                syntax_valid=False,
                violations=[f"Syntax error on line {e.lineno}: {e.msg}"],
                summary=f"Code syntax error in {filename}.",
            )

        violations: list[str] = []
        forbidden_found: list[str] = []
        has_annotations = True
        total_functions = 0
        annotated_functions = 0

        for node in ast.walk(tree):
            # Check prohibited dangerous execution functions
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in self.DANGEROUS_FUNCTIONS:
                    violations.append(
                        f"Security violation on line {node.lineno}: Prohibited call to dangerous function '{func_name}'"
                    )

            # Check Hexagonal domain import boundaries
            if is_domain:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in self.FORBIDDEN_DOMAIN_IMPORTS:
                            forbidden_found.append(root)
                            violations.append(
                                f"Hexagonal boundary violation on line {node.lineno}: "
                                f"Domain code cannot import infrastructure framework '{root}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        root = node.module.split(".")[0]
                        if root in self.FORBIDDEN_DOMAIN_IMPORTS:
                            forbidden_found.append(root)
                            violations.append(
                                f"Hexagonal boundary violation on line {node.lineno}: "
                                f"Domain code cannot import from infrastructure framework '{root}'"
                            )

            # Check function type annotations
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Ignore dunder methods like __init__
                if not node.name.startswith("__"):
                    total_functions += 1
                    if node.returns is not None or any(arg.annotation is not None for arg in node.args.args):
                        annotated_functions += 1

        if total_functions > 0 and (annotated_functions / total_functions) < 0.5:
            has_annotations = False
            violations.append(
                f"Type annotation warning: Only {annotated_functions}/{total_functions} functions have type hints in {filename}."
            )

        is_valid = len([v for v in violations if not v.startswith("Type annotation warning")]) == 0

        summary = (
            f"Verified {filename}: All Hexagonal rules passed (0 framework imports in domain)."
            if is_valid
            else f"Validation failed for {filename} with {len(violations)} architectural violations."
        )

        return AstValidationResult(
            is_valid=is_valid,
            violations=violations,
            forbidden_imports_found=sorted(set(forbidden_found)),
            type_annotations_present=has_annotations,
            syntax_valid=True,
            summary=summary,
        )

    def validate_plugin_files(self, files: list[ScaffoldedFile]) -> AstValidationResult:
        """Validate an entire collection of scaffolded plugin files."""
        all_violations: list[str] = []
        all_forbidden: list[str] = []
        all_valid = True

        for f in files:
            # Manifest JSON does not undergo Python AST parsing
            if f.module_type == ScaffoldedModuleType.MANIFEST:
                continue

            is_domain = f.module_type in (
                ScaffoldedModuleType.ABSTRACTIONS,
                ScaffoldedModuleType.SERVICE,
            )
            res = self.validate_code(f.content, filename=f.rel_path, is_domain=is_domain)
            if not res.is_valid:
                all_valid = False
            all_violations.extend([f"[{f.rel_path}] {v}" for v in res.violations])
            all_forbidden.extend(res.forbidden_imports_found)

        summary = (
            f"All {len(files)} files passed static AST verification (0 framework imports in domain)."
            if all_valid
            else f"AST verification failed across {len(all_violations)} violations."
        )

        return AstValidationResult(
            is_valid=all_valid,
            violations=all_violations,
            forbidden_imports_found=sorted(set(all_forbidden)),
            type_annotations_present=True,
            syntax_valid=True,
            summary=summary,
        )
