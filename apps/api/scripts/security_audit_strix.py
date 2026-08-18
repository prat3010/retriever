#!/usr/bin/env python3
"""
Local Security Audit Script using Strix AI Penetration Testing Framework (usestrix/strix)
for the Retriever SaaS RAG Backend.
"""

import argparse
import os
import shutil
import subprocess
import sys

# Ensure retriever apps/api directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(API_DIR, "../.."))
sys.path.insert(0, API_DIR)

from scripts.generate_openapi import generate_openapi


def check_docker() -> bool:
    """Verify if Docker is installed and running."""
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, check=False)
        return res.returncode == 0
    except FileNotFoundError:
        return False


def get_strix_command() -> list[str]:
    """Return command list for invoking strix."""
    strix_path = shutil.which("strix")
    if strix_path:
        return [strix_path]
    return ["uvx", "--from", "strix-agent", "strix"]


def main():
    parser = argparse.ArgumentParser(
        description="Run Strix AI security scan on Retriever FastAPI service."
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "standard", "deep"],
        default="quick",
        help="Scan mode depth",
    )
    parser.add_argument(
        "--target-url",
        default="http://localhost:8000",
        help="Target URL for dynamic scan",
    )
    parser.add_argument(
        "--max-budget",
        type=float,
        default=None,
        help="Maximum LLM spend budget in USD",
    )
    args = parser.parse_args()

    print("==========================================================")
    print(" Starting Strix Security Audit for Retriever")
    print(f" Target URL: {args.target_url}")
    print(f" Scan Mode:  {args.mode}")
    print("==========================================================")

    if not check_docker():
        print("❌ Error: Docker is not running. Please start Docker first.")
        sys.exit(1)
    print("✓ Docker is running.")

    # 1. Regenerate OpenAPI schema
    print(" Generating OpenAPI specification...")
    generate_openapi()
    openapi_path = os.path.abspath(os.path.join(ROOT_DIR, "docs/openapi.json"))

    # 2. Build Strix command
    strix_cmd = get_strix_command()
    print(f"✓ Using Strix invocation: {' '.join(strix_cmd)}")

    # 3. Environment configuration
    env = os.environ.copy()
    if "STRIX_LLM" not in env:
        env["STRIX_LLM"] = "openrouter/anthropic/claude-3.5-sonnet"
    if "OPENROUTER_API_KEY" in env and "LLM_API_KEY" not in env:
        env["LLM_API_KEY"] = env["OPENROUTER_API_KEY"]

    instruction = (
        "Focus on multi-tenant tenant_id isolation, API key authentication, "
        "SQL injection in vector queries, broken access control, and prompt injection resilience."
    )

    cmd = strix_cmd + [
        "--target",
        openapi_path,
        "--target",
        os.path.join(API_DIR, "src"),
        "--target",
        args.target_url,
        "--scan-mode",
        args.mode,
        "--non-interactive",
        "--instruction",
        instruction,
    ]

    if args.max_budget:
        cmd.extend(["--max-budget", str(args.max_budget)])

    print("==========================================================")
    print(f" Running Strix Command: {' '.join(cmd)}")
    print("==========================================================")

    try:
        subprocess.run(cmd, env=env, check=False)
    except Exception as e:
        print(f"⚠️ Strix process finished: {e}")

    print("==========================================================")
    print(" Scan Complete! Check ./strix_runs/ for findings.")
    print("==========================================================")


if __name__ == "__main__":
    main()
