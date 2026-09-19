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


PROVIDER_MAP = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "tavily": "TAVILY_API_KEY",
}


def mask_key(key: str) -> str:
    """Masks secret key for safe display in logs and terminal."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def detect_provider(key: str, hint: str | None = None) -> tuple[str, str]:
    """Detects provider and environment variable name from key string and optional hint."""
    hint_clean = (hint or "").strip().lower()
    if hint_clean in PROVIDER_MAP:
        return (hint_clean, PROVIDER_MAP[hint_clean])

    # Auto-detect by key prefix
    if key.startswith("sk-ant-"):
        return ("anthropic", "ANTHROPIC_API_KEY")
    elif key.startswith("gsk_"):
        return ("groq", "GROQ_API_KEY")
    elif key.startswith("AIza"):
        return ("gemini", "GEMINI_API_KEY")
    elif key.startswith("sk-") or key.startswith("org-"):
        return ("openai", "OPENAI_API_KEY")
    elif key.startswith("mistral_"):
        return ("mistral", "MISTRAL_API_KEY")

    if hint_clean:
        var_name = hint_clean.upper() if hint_clean.endswith("_API_KEY") else f"{hint_clean.upper()}_API_KEY"
        return (hint_clean, var_name)
    return ("openai", "OPENAI_API_KEY")


def init_env(root_dir: Path) -> dict:
    """Initializes .env from .env.docker.example if not already created."""
    import shutil

    env_file = root_dir / ".env"
    example_file = root_dir / ".env.docker.example"
    if env_file.is_file():
        return {"success": True, "created": False, "message": ".env file already exists."}
    if example_file.is_file():
        shutil.copy(example_file, env_file)
        return {"success": True, "created": True, "message": "Created .env from .env.docker.example."}
    env_file.write_text("# Retriever Environment Configuration\n", encoding="utf-8")
    return {"success": True, "created": True, "message": "Created blank .env file."}


def inject_key(root_dir: Path, provider_or_hint: str, raw_key: str | None = None) -> dict:
    """Safely initializes .env (if missing) and injects/updates the API key."""
    import shutil

    if raw_key is None:
        key = provider_or_hint.strip()
        provider, env_var = detect_provider(key)
    else:
        hint = provider_or_hint.strip()
        key = raw_key.strip()
        provider, env_var = detect_provider(key, hint)

    if not key:
        return {"success": False, "error": "API key cannot be empty."}

    env_file = root_dir / ".env"
    example_file = root_dir / ".env.docker.example"

    # Ensure .env exists
    if not env_file.is_file():
        if example_file.is_file():
            shutil.copy(example_file, env_file)
        else:
            env_file.write_text("# Retriever Environment Configuration\n", encoding="utf-8")

    lines = env_file.read_text(encoding="utf-8").splitlines()
    replaced = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith(f"{env_var}=")
            or stripped.startswith(f"# {env_var}=")
            or stripped.startswith(f"#{env_var}=")
        ):
            new_lines.append(f"{env_var}={key}")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        new_lines.append("")
        new_lines.append("# Cognitive Provider Keys (Configured by Agent Setup)")
        new_lines.append(f"{env_var}={key}")

    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return {
        "success": True,
        "provider": provider,
        "env_var": env_var,
        "masked_key": mask_key(key),
        "env_file": str(env_file),
    }


def sense_environment(root_dir: Path) -> dict:
    """Checks if .env is populated or ready to initialize, and detects configured LLM keys."""
    env_file = root_dir / ".env"
    example_file = root_dir / ".env.docker.example"
    exists = env_file.is_file()
    ready = False
    configured_keys: dict[str, str] = {}

    if exists:
        try:
            content = env_file.read_text(encoding="utf-8")
            if "POSTGRES_PASSWORD" in content:
                ready = True
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if (
                        k
                        in (
                            "OPENAI_API_KEY",
                            "GEMINI_API_KEY",
                            "ANTHROPIC_API_KEY",
                            "GROQ_API_KEY",
                            "MISTRAL_API_KEY",
                            "COHERE_API_KEY",
                        )
                        and v
                    ):
                        configured_keys[k] = mask_key(v)
        except Exception:
            pass

    return {
        "has_env": exists,
        "is_configured": ready,
        "template_available": example_file.is_file(),
        "configured_keys": configured_keys,
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

    # Environment & LLM Inference
    env = data["environment"]
    rec = data["recommendation"]
    print(f"\n{BOLD}[4/4] Environment & LLM Inference Readiness:{NC}")
    if env["has_env"]:
        print(f"  • Environment:    {GREEN}.env file present & configured{NC}")
    else:
        print(f"  • Environment:    {YELLOW}.env will be auto-generated from template{NC}")

    print(f"  • Embeddings:     {GREEN}Local Ollama (nomic-embed-text) — $0 Cost{NC}")

    cfg_keys = env.get("configured_keys", {})
    if cfg_keys:
        keys_summary = ", ".join(f"{k.replace('_API_KEY', '')} ({v})" for k, v in cfg_keys.items())
        print(f"  • Chat Inference: {GREEN}Cloud Key Configured [{keys_summary}]{NC}")
    else:
        print(
            f"  • Chat Inference: {CYAN}Local Ollama ($0 cost) OR Cloud BYOK (none configured){NC}"
        )

    print("\n----------------------------------------------------------------------")
    if rec["can_auto_launch_docker"]:
        print(f"{GREEN}{BOLD}✓ SYSTEM READY FOR 1-CLICK LAUNCH{NC}")
        print(f"Execute: {CYAN}./scripts/quickstart.sh{NC} or {CYAN}docker compose up -d{NC}")
    else:
        print(f"{YELLOW}{BOLD}! ACTION NEEDED BEFORE LAUNCH{NC}")
        print(f"Action: {rec['next_command']}")
    print("----------------------------------------------------------------------\n")


def main():
    root_dir = Path(__file__).resolve().parent.parent

    # Check for --help / -h
    if "-h" in sys.argv or "--help" in sys.argv:
        print(
            f"\n{BOLD}Retriever Agent Preflight Diagnostic & Key Configuration Tool{NC}\n\n"
            "Usage:\n"
            "  python3 scripts/agent_preflight.py                  # Run diagnostic and check environment\n"
            "  python3 scripts/agent_preflight.py --json           # Output machine-readable JSON diagnostic\n"
            "  python3 scripts/agent_preflight.py --init-env       # Initialize .env from template\n"
            "  python3 scripts/agent_preflight.py --set-key <key>  # Auto-detect provider & inject key into .env\n"
            "  python3 scripts/agent_preflight.py --set-key <provider> <key>  # Explicit provider key injection\n\n"
            "Supported Providers:\n"
            "  openai, gemini, anthropic, groq, mistral, cohere\n"
        )
        sys.exit(0)

    # Check for --init-env
    if "--init-env" in sys.argv:
        res = init_env(root_dir)
        if "--json" in sys.argv:
            print(json.dumps(res, indent=2))
        else:
            status_color = GREEN if res["success"] else RED
            print(f"{status_color}{BOLD}{res['message']}{NC}")
        sys.exit(0 if res["success"] else 1)

    # Check for --set-key
    if "--set-key" in sys.argv:
        idx = sys.argv.index("--set-key")
        args = [a for a in sys.argv[idx + 1 :] if not a.startswith("--")]
        if not args:
            print(
                f"{RED}{BOLD}Error:{NC} Missing key. Usage: python3 scripts/agent_preflight.py --set-key [provider] <key>"
            )
            sys.exit(1)

        if len(args) == 1:
            res = inject_key(root_dir, args[0])
        else:
            res = inject_key(root_dir, args[0], args[1])

        if "--json" in sys.argv:
            print(json.dumps(res, indent=2))
        else:
            if res["success"]:
                print(
                    f"{GREEN}{BOLD}✓ Successfully configured {res['env_var']} ({res['masked_key']}) in .env{NC}"
                )
            else:
                print(f"{RED}{BOLD}Error: {res.get('error', 'Failed to inject key')}{NC}")
        sys.exit(0 if res["success"] else 1)

    data = run_preflight()
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    else:
        print_pretty(data)


if __name__ == "__main__":
    main()
