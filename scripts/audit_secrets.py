#!/usr/bin/env python3
"""
scripts/audit_secrets.py — Autonomous Secret & Token Leak Scanner

Scans codebase files and git working directory for accidentally leaked API keys,
private certificates, service-role secrets, and high-entropy authentication tokens.
"""

import sys
import re
from pathlib import Path

# High-risk secret regex patterns
SECRET_PATTERNS = [
    (r"(?:resend|RESEND)_[A-Za-z0-9_]*\s*[:=]\s*['\"](re_[0-9a-zA-Z]{24,})['\"]", "Live Resend API Key"),
    (r"(?:re_[0-9a-zA-Z]{24,32})", "Raw Resend Token Signature"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private Cryptographic Key"),
    (r"(?:ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{60,})", "GitHub Personal Access Token"),
    (r"(?:sk-ant-[0-9a-zA-Z_-]{40,})", "Anthropic Secret Key"),
    (r"(?:sk-proj-[0-9a-zA-Z_-]{40,})", "OpenAI Project Secret Key"),
    (r"(?:AIzaSy[0-9a-zA-Z_-]{33})", "Google Cloud / Gemini API Key"),
]

# Paths to ignore during scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".venv",
    ".venv-strix",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "coverage",
    "public",
    "dist",
    "build",
    "storage",
}

IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".pdf", ".lock",
    ".so", ".dylib", ".dll", ".a", ".o", ".pyc", ".pyd", ".bin", ".tar", ".gz", ".zip"
}

def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    findings = []
    if "test" in file_path.name.lower() or "mock" in file_path.name.lower():
        return findings

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.split("\n")
    for line_idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        if line_clean.startswith("//") or line_clean.startswith("#") or line_clean.startswith("*"):
            if "example" in line_clean.lower() or "placeholder" in line_clean.lower() or "your_" in line_clean.lower():
                continue

        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                if "YOUR_" in line or "process.env" in line or "os.environ" in line or "os.getenv" in line:
                    continue
                findings.append((line_idx, label, line_clean[:60] + "..."))
    return findings

def main():
    repo_root = Path(__file__).resolve().parent.parent
    print(f"🔒 Scanning {repo_root.name} for leaked secrets and credentials...")

    total_scanned = 0
    all_findings = []

    for path in repo_root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in IGNORED_EXTENSIONS:
            continue
        if path.name.startswith(".env") and not path.name.endswith(".example"):
            continue

        total_scanned += 1
        findings = scan_file(path)
        if findings:
            for line_no, label, preview in findings:
                all_findings.append((path.relative_to(repo_root), line_no, label, preview))

    if all_findings:
        print(f"\n❌ FAILED: Found {len(all_findings)} potential secret leaks across {total_scanned} files:")
        for rel_path, line_no, label, preview in all_findings:
            print(f"  - {rel_path}:{line_no} [{label}]: {preview}")
        sys.exit(1)
    else:
        print(f"✓ Scanned {total_scanned} files. 0 secrets or sensitive tokens detected!")
        sys.exit(0)

if __name__ == "__main__":
    main()
