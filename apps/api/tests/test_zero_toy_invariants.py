"""Automated Zero-Toy & Authentic Engineering Regression Suite.

Ensures that no mock classes, synthetic score boosts, or fake algorithm
labels can ever be committed to the production codebase.
"""

import subprocess
import sys
from pathlib import Path


def test_zero_toy_invariants_pass() -> None:
    """Verifies that scripts/audit_zero_toy.py reports 0 violations."""
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    script_path = root_dir / "scripts" / "audit_zero_toy.py"

    assert script_path.is_file(), f"Audit script not found at {script_path}"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Zero-Toy Audit Failed:\n{result.stdout}\n{result.stderr}"
    assert "0 violations" in result.stdout
