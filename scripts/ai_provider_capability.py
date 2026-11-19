from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ai_product_factory.json"


def discover() -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    providers = {}
    for name, spec in config.get("providers", {}).items():
        command = spec.get("command")
        providers[name] = {
            "enabled": bool(spec.get("enabled", False)),
            "command_available": bool(command and shutil.which(command)),
            "model_agnostic": bool(spec.get("model_agnostic", True)),
            "requires_external_secret": bool(spec.get("requires_external_secret", False)),
        }
    return {
        "schema_version": 1,
        "kind": "AI_PROVIDER_CAPABILITY_DISCOVERY",
        "providers": providers,
        "github_actions": bool(os.environ.get("GITHUB_ACTIONS")),
        "secret_values_exposed": False,
    }


def route(discovery: dict, required_capability: str) -> dict:
    candidates = [
        name
        for name, spec in discovery["providers"].items()
        if spec["enabled"] and spec["command_available"]
    ]
    if candidates:
        return {
            "status": "ROUTE_AVAILABLE",
            "required_capability": required_capability,
            "candidates": candidates,
        }
    return {
        "status": "BLOCK_PATH",
        "required_capability": required_capability,
        "candidates": [],
        "reason": "no_enabled_provider_with_available_runtime",
    }


if __name__ == "__main__":
    print(json.dumps(discover(), indent=2, sort_keys=True))
