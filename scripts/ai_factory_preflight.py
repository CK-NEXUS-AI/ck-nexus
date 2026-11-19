from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "ai_factory"
CONFIG = ROOT / "config" / "ai_factory.json"

TOOLS = ("git", "python", "pytest", "ruff", "docker", "gh")
PROVIDER_COMMANDS = {
    "claude": "claude",
    "gemini": "gemini",
    "goose": "goose",
    "openhands": "openhands",
    "ollama": "ollama",
}

SECRET_ENV_NAMES = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "COPILOT_GITHUB_TOKEN",
)


def command_version(command: str) -> str | None:
    try:
        completed = subprocess.run(
            [command, "--version"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first = completed.stdout.strip().splitlines()
    return first[0][:160] if first else None


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    tools = {
        name: {
            "available": shutil.which(name) is not None,
            "version": command_version(name) if shutil.which(name) else None,
        }
        for name in TOOLS
    }

    providers = {}
    for provider, command in PROVIDER_COMMANDS.items():
        providers[provider] = {
            "command_available": shutil.which(command) is not None,
            "secret_present": any(bool(os.environ.get(name)) for name in SECRET_ENV_NAMES)
            if provider in {"claude", "gemini"}
            else None,
        }

    git_sha = None
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()

    result = {
        "schema_version": 1,
        "kind": "CKNEXUS_AI_FACTORY_PREFLIGHT",
        "timestamp": datetime.now(UTC).isoformat(),
        "source_commit": git_sha,
        "mode": config["mode"],
        "github_actions": bool(os.environ.get("GITHUB_ACTIONS")),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "tools": tools,
        "providers": providers,
        "secrets_redacted": True,
        "hard_gates": config["hard_gates"],
        "verdict": "READY_FOR_DETERMINISTIC_GATES"
        if tools["git"]["available"] and tools["python"]["available"]
        else "BLOCKED",
    }

    path = OUT / "preflight.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
