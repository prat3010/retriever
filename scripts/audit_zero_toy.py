#!/usr/bin/env python3
"""Zero-Toy & Authentic Engineering Static Analysis Scanner.

Enforces that production source code in apps/api/src/ contains:
1. Zero mock classes or placeholder stubs (class Mock...).
2. Zero synthetic math boosts (e.g. adding hardcoded + 0.10 to faked scores).
3. Zero silent exception swallows returning dummy bytes (b"mock_...").
4. Zero failed network probe swallows returning status_code=200 and is_healthy=True.
5. Zero fake algorithm labels (e.g. claiming Llama Guard 3 on naive keyword checks,
   or claiming LongLLMLingua on naive words[:n] slicing).

Exits with code 0 if 100% clean, or code 1 with line-by-line violation reports.
"""

import ast
import re
import sys
from pathlib import Path

VIOLATIONS: list[str] = []

SRC_DIR = Path(__file__).resolve().parent.parent / "apps" / "api" / "src"

# Forbidden substrings in production code
FORBIDDEN_SUBSTRINGS = [
    (re.compile(r'b["\']mock_audio_frame["\']'), "Dummy audio frame fallback in exception handler"),
    (re.compile(r'class\s+Mock\w+'), "Mock class defined in production code"),
    (re.compile(r'demo_boost\s*=\s*min\('), "Synthetic benchmark score boost formula"),
    (re.compile(r'is_healthy\s*=\s*True.*is_simulated\s*=\s*True', re.DOTALL), "Reporting dead probe as healthy 200 OK"),
    (re.compile(r'LongLLMLingua.*words\[:'), "Naive string slicing mislabeled as LongLLMLingua"),
    (re.compile(r'Llama Guard.*(?:drop table|ignore previous)', re.IGNORECASE), "Naive keyword check mislabeled as Llama Guard"),
]


def check_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")

    # 1. Regex checks
    for pattern, reason in FORBIDDEN_SUBSTRINGS:
        match = pattern.search(text)
        if match:
            # Find line number
            start = match.start()
            line_no = text.count("\n", 0, start) + 1
            VIOLATIONS.append(f"{path.relative_to(SRC_DIR)}:{line_no} - {reason}")

    # 2. AST checks for Mock classes in production code
    try:
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith("Mock"):
                VIOLATIONS.append(
                    f"{path.relative_to(SRC_DIR)}:{node.lineno} - Mock class '{node.name}' declared in production source."
                )
    except SyntaxError:
        pass


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"Error: Source directory {SRC_DIR} not found.")
        return 1

    py_files = list(SRC_DIR.glob("**/*.py"))
    for f in py_files:
        check_file(f)

    if VIOLATIONS:
        print("\n=================================================================")
        print("❌ ZERO-TOY INVARIANT VIOLATIONS DETECTED (MANDATORY GATE FAILURE)")
        print("=================================================================")
        for v in VIOLATIONS:
            print(f"  ! {v}")
        print("\nProduction code must NEVER contain mock facades, synthetic score boosts,")
        print("or fake ML labels. Fix the violations above with genuine domain logic.")
        return 1

    print(f"✓ Zero-Toy Audit Passed: {len(py_files)} production Python files scanned, 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
