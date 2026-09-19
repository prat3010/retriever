"""Tests for scripts/agent_preflight.py.

Validates environment sensing, key detection, format masking, and safe
atomic key injection into .env files.
"""

import sys
from pathlib import Path

# Add scripts directory to path to import agent_preflight
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))

from agent_preflight import (
    detect_provider,
    init_env,
    inject_key,
    mask_key,
    sense_environment,
)


def test_detect_provider_auto_detection():
    # Anthropic
    p, var = detect_provider("sk-ant-api03-12345")
    assert p == "anthropic"
    assert var == "ANTHROPIC_API_KEY"

    # Groq
    p, var = detect_provider("gsk_987654321")
    assert p == "groq"
    assert var == "GROQ_API_KEY"

    # Gemini
    p, var = detect_provider("AIzaSyD-123456789")
    assert p == "gemini"
    assert var == "GEMINI_API_KEY"

    # OpenAI
    p, var = detect_provider("sk-proj-openai123")
    assert p == "openai"
    assert var == "OPENAI_API_KEY"


def test_detect_provider_with_hint():
    p, var = detect_provider("custom-key-123", hint="gemini")
    assert p == "gemini"
    assert var == "GEMINI_API_KEY"

    p, var = detect_provider("custom-key-456", hint="mistral")
    assert p == "mistral"
    assert var == "MISTRAL_API_KEY"

    p, var = detect_provider("custom-key-789", hint="cohere")
    assert p == "cohere"
    assert var == "COHERE_API_KEY"


def test_mask_key():
    assert mask_key("") == ""
    assert mask_key("short") == "****"
    assert mask_key("sk-proj-12345678") == "sk-p...5678"


def test_init_env(tmp_path: Path):
    example_file = tmp_path / ".env.docker.example"
    example_file.write_text("POSTGRES_PASSWORD=testpass\n", encoding="utf-8")

    res = init_env(tmp_path)
    assert res["success"] is True
    assert res["created"] is True
    assert (tmp_path / ".env").is_file()
    assert "POSTGRES_PASSWORD=testpass" in (tmp_path / ".env").read_text(encoding="utf-8")

    # Second call should not overwrite
    res2 = init_env(tmp_path)
    assert res2["created"] is False


def test_inject_key_replaces_existing(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ENVIRONMENT=development\n# OPENAI_API_KEY=\nDATABASE_URL=test\n",
        encoding="utf-8",
    )

    res = inject_key(tmp_path, "openai", "sk-proj-testkey123456")
    assert res["success"] is True
    assert res["env_var"] == "OPENAI_API_KEY"
    assert res["masked_key"] == "sk-p...3456"

    content = env_file.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-proj-testkey123456" in content
    assert "# OPENAI_API_KEY=" not in content


def test_inject_key_appends_new(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("ENVIRONMENT=development\n", encoding="utf-8")

    res = inject_key(tmp_path, "AIzaSyD-new-gemini-key")
    assert res["success"] is True
    assert res["provider"] == "gemini"
    assert res["env_var"] == "GEMINI_API_KEY"

    content = env_file.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=AIzaSyD-new-gemini-key" in content


def test_sense_environment_configured_keys(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_PASSWORD=test\nOPENAI_API_KEY=sk-proj-12345678\nGEMINI_API_KEY=AIzaSyD-testkey123\n",
        encoding="utf-8",
    )

    sensed = sense_environment(tmp_path)
    assert sensed["has_env"] is True
    assert sensed["is_configured"] is True
    assert "OPENAI_API_KEY" in sensed["configured_keys"]
    assert "GEMINI_API_KEY" in sensed["configured_keys"]
    assert sensed["configured_keys"]["OPENAI_API_KEY"] == "sk-p...5678"
