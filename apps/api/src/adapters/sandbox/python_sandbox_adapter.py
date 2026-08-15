"""Restricted Python REPL Sandbox Adapter.

Implements ReplSandboxProvider using AST validation and isolated namespaces
to safely execute data-processing Python scripts with execution timeouts.
"""

import ast
import asyncio
import io
import logging
import sys
import time
from typing import Any

from src.domain.rlm.abstractions import ReplExecutionResult, ReplSandboxProvider

logger = logging.getLogger(__name__)

# Forbidden module names and built-in function identifiers
PROHIBITED_NAMES: set[str] = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "shutil",
    "importlib",
    "open",
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "input",
}

SAFE_BUILTINS: dict[str, Any] = {
    "len": len,
    "sum": sum,
    "range": range,
    "sorted": sorted,
    "min": min,
    "max": max,
    "filter": filter,
    "map": map,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "round": round,
    "abs": abs,
    "zip": zip,
    "enumerate": enumerate,
    "any": any,
    "all": all,
}


class RestrictedASTValidator(ast.NodeVisitor):
    """AST visitor that raises SecurityError if prohibited nodes or names are encountered."""

    def visit_Import(self, node: ast.Import) -> None:
        raise SecurityError("Imports are prohibited inside the REPL sandbox.")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        raise SecurityError("Imports are prohibited inside the REPL sandbox.")

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in PROHIBITED_NAMES:
            raise SecurityError(f"Use of prohibited identifier '{node.id}' is blocked.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            raise SecurityError(f"Access to private attribute '{node.attr}' is blocked.")
        self.generic_visit(node)


class RestrictedPythonSandboxAdapter(ReplSandboxProvider):
    """Safe tenant-isolated Python AST execution sandbox adapter."""

    async def execute_script(
        self,
        tenant_id: str,
        code: str,
        context_dict: dict[str, Any] | None = None,
        timeout_seconds: float = 15.0,
    ) -> ReplExecutionResult:
        """Execute Python code string within AST safety bounds and timeout limits."""
        start_time = time.monotonic()
        if not code.strip():
            return ReplExecutionResult(
                output="", return_value=None, is_error=False, execution_time_ms=0.0
            )

        # 1. AST Safety Check
        try:
            parsed_ast = ast.parse(code, mode="exec")
            RestrictedASTValidator().visit(parsed_ast)
        except Exception:
            return ReplExecutionResult(
                output="",
                return_value=None,
                is_error=True,
                execution_time_ms=round((time.monotonic() - start_time) * 1000, 2),
            )

        # 2. Execution Setup
        stdout_capture = io.StringIO()

        def _custom_print(*args: Any, **kwargs: Any) -> None:
            sep = kwargs.get("sep", " ")
            end = kwargs.get("end", "\n")
            msg = sep.join(str(a) for a in args) + end
            stdout_capture.write(msg)

        safe_globals = {
            "__builtins__": {**SAFE_BUILTINS, "print": _custom_print},
        }

        local_vars: dict[str, Any] = {}
        if context_dict:
            local_vars.update(context_dict)

        # 3. Synchronous execution wrapper
        def _run_exec() -> tuple[Any, bool, str]:
            sys_stdout_old = sys.stdout
            try:
                sys.stdout = stdout_capture
                compiled = compile(parsed_ast, filename="<sandbox>", mode="exec")
                exec(compiled, safe_globals, local_vars)
                res_val = local_vars.get("result", local_vars.get("output", None))
                return res_val, False, stdout_capture.getvalue()
            except Exception as e:
                return f"Execution Error: {e!s}", True, stdout_capture.getvalue()
            finally:
                sys.stdout = sys_stdout_old

        # 4. Timeout-bounded execution
        try:
            ret_val, is_err, captured_out = await asyncio.wait_for(
                asyncio.to_thread(_run_exec), timeout=timeout_seconds
            )
        except TimeoutError:
            ret_val = f"TimeoutError: Script execution exceeded {timeout_seconds}s limit."
            is_err = True
            captured_out = stdout_capture.getvalue()

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return ReplExecutionResult(
            output=captured_out.strip(),
            return_value=ret_val,
            is_error=is_err,
            execution_time_ms=round(elapsed_ms, 2),
        )


class SecurityError(Exception):
    """Exception raised when Python code violates AST security constraints."""

    pass
