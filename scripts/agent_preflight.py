#!/usr/bin/env python3
"""
Retriever — Agent Preflight & Host Diagnostic Engine
====================================================
Inspects host hardware, container runtimes, port bindings, and environment
configuration. Designed for instant diagnostic reporting to AI coding agents
(Cursor, Windsurf, Claude Code, Antigravity, GitHub Copilot) and human developers.

Usage:
    python3 scripts/agent_preflight.py          # Formatted human terminal output
    python3 scripts/agent_preflight.py --json   # Machine-readable JSON output
"""

import json
import platform
import socket
import subprocess
import sys
from pathlib import Path

# Terminal colors
BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
DIM = "\033[2m"
NC = "\033[0m"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local TCP port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    """Runs a shell command safely, returning (success, stdout/stderr)."""
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        output = res.stdout.strip() or res.stderr.strip()
        return (res.returncode == 0, output)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return (False, "")


def sense_hardware() -> dict:
    """Detects CPU architecture, OS, and GPU/Metal acceleration."""
    sys_name = platform.system()
    machine = platform.machine().lower()
    accel = "CPU (Standard)"

    if sys_name == "Darwin":
        if "arm" in machine:
            accel = "Apple Silicon Metal (MPS / Neural Engine)"
        else:
            accel = "Intel Core (macOS CPU)"
    elif sys_name == "Linux":
        ok, out = run_cmd(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
        if ok and out:
            gpu_name = out.split("\n")[0].strip()
            accel = f"NVIDIA CUDA Acceleration ({gpu_name})"

    return {
        "os": sys_name,
        "arch": machine,
        "acceleration": accel,
    }


def sense_docker() -> dict:
    """Checks Docker runtime and Compose plugin status."""
    has_docker, docker_ver = run_cmd(["docker", "--version"])
    daemon_ok, _ = run_cmd(["docker", "info"])

    compose_ok, compose_ver = run_cmd(["docker", "compose", "version"])
    if not compose_ok:
        compose_ok, compose_ver = run_cmd(["docker-compose", "--version"])

    return {
        "installed": has_docker,
        "version": docker_ver if has_docker else None,
        "daemon_running": daemon_ok,
        "compose_available": compose_ok,
        "compose_version": compose_ver if compose_ok else None,
    }


def sense_ollama() -> dict:
    """Checks local Ollama service and nomic-embed-text availability."""
    running = is_port_in_use(11434)
    has_model = False

    if running:
        # Check if nomic-embed-text is pulled
        ok, out = run_cmd(["ollama", "list"])
        if ok and "nomic-embed-text" in out:
            has_model = True

    return {
        "local_daemon_running": running,
        "has_embedding_model": has_model,
        "managed_by_docker": not running,  # If not local, docker-compose manages it
    }


def sense_ports() -> dict:
    """Audits required platform ports for conflicts."""
    port_map = {
        8000: "Retriever FastAPI Engine",
        3000: "Web Admin Dashboard",
        5432: "PostgreSQL 16 (pgvector)",
        6379: "Redis 7 (Cache & Queues)",
        11434: "Ollama (Embeddings)",
    }
    status = {}
    for port, service in port_map.items():
        in_use = is_port_in_use(port)
        status[port] = {
            "service": service,
            "in_use": in_use,
            "available": not in_use,
        }
    return status


def sense_environment(root_dir: Path) -> dict:
    """Checks if .env is populated or ready to initialize."""
    env_file = root_dir / ".env"
    example_file = root_dir / ".env.docker.example"
    exists = env_file.is_file()
    ready = False

    if exists:
        try:
            content = env_file.read_text(encoding="utf-8")
            if "POSTGRES_PASSWORD" in content:
                ready = True
        except Exception:
            pass

    return {
        "has_env": exists,
        "is_configured": ready,
        "template_available": example_file.is_file(),
    }


def run_preflight() -> dict:
    """Runs complete diagnostic audit."""
    root_dir = Path(__file__).resolve().parent.parent

    hw = sense_hardware()
    dk = sense_docker()
    ol = sense_ollama()
    ports = sense_ports()
    env = sense_environment(root_dir)

    # Calculate overall readiness
    can_docker_launch = dk["installed"] and dk["daemon_running"] and dk["compose_available"]
    port_conflicts = [p for p, info in ports.items() if info["in_use"] and p in (8000, 3000)]

    readiness = "READY" if can_docker_launch and not port_conflicts else "NEEDS_SETUP"

    return {
        "readiness": readiness,
        "hardware": hw,
        "docker": dk,
        "ollama": ol,
        "ports": ports,
        "environment": env,
        "recommendation": {
            "can_auto_launch_docker": can_docker_launch,
            "port_conflicts": port_conflicts,
            "next_command": (
                "./scripts/quickstart.sh"
                if can_docker_launch
                else "open Docker Desktop or install Docker"
            ),
        },
    }


def print_pretty(data: dict):
    """Renders ANSI formatted diagnostic report."""
    print(f"\n{CYAN}{BOLD}Retriever — Agent Preflight & Host Diagnostic{NC}")
    print(f"{DIM}Autonomous system sensing for AI coding assistants & developers{NC}")
    print("----------------------------------------------------------------------")

    # Hardware
    hw = data["hardware"]
    print(f"{BOLD}[1/4] Host Hardware & Acceleration:{NC}")
    print(f"  • Platform:     {CYAN}{hw['os']} ({hw['arch']}){NC}")
    print(f"  • Acceleration: {GREEN}{hw['acceleration']}{NC}")

    # Docker
    dk = data["docker"]
    print(f"\n{BOLD}[2/4] Container Runtime:{NC}")
    if dk["installed"] and dk["daemon_running"]:
        print(f"  • Docker Daemon:  {GREEN}Active & Running{NC}")
        print(f"  • Compose Plugin: {GREEN}Available ({dk['compose_version']}){NC}")
    elif dk["installed"] and not dk["daemon_running"]:
        print(f"  • Docker Daemon:  {RED}Installed but NOT running (Start Docker Desktop){NC}")
    else:
        print(f"  • Docker Daemon:  {RED}Not installed{NC}")

    # Ports
    ports = data["ports"]
    print(f"\n{BOLD}[3/4] Platform Port Allocations:{NC}")
    for port, info in ports.items():
        if info["available"]:
            print(f"  • Port {port:5d} ({info['service']:<27}): {GREEN}Available{NC}")
        else:
            print(f"  • Port {port:5d} ({info['service']:<27}): {YELLOW}Active / Occupied{NC}")

    # Environment & Launch
    env = data["environment"]
    rec = data["recommendation"]
    print(f"\n{BOLD}[4/4] Environment & Launch Readiness:{NC}")
    if env["has_env"]:
        print(f"  • Environment:    {GREEN}.env file present & configured{NC}")
    else:
        print(f"  • Environment:    {YELLOW}.env will be auto-generated from template{NC}")

    print("\n----------------------------------------------------------------------")
    if rec["can_auto_launch_docker"]:
        print(f"{GREEN}{BOLD}✓ SYSTEM READY FOR 1-CLICK LAUNCH{NC}")
        print(f"Execute: {CYAN}./scripts/quickstart.sh{NC} or {CYAN}docker compose up -d{NC}")
    else:
        print(f"{YELLOW}{BOLD}! ACTION NEEDED BEFORE LAUNCH{NC}")
        print(f"Action: {rec['next_command']}")
    print("----------------------------------------------------------------------\n")


def main():
    data = run_preflight()
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
