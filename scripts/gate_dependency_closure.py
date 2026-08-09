from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = ("gateway", "dev", "billing", "email", "github-app")
IMPORT_OVERRIDES = {
    "openai-agents": "agents",
    "opentelemetry-api": "opentelemetry",
    "pip-audit": "pip_audit",
    "pyjwt": "jwt",
    "python-dotenv": "dotenv",
    "python-multipart": "multipart",
}


@dataclass(frozen=True)
class RegistryStatus:
    configured: bool
    dns_resolves: bool | None


def registry_status() -> RegistryStatus:
    # URLs can embed credentials. Never persist or print the URL or hostname.
    raw = os.getenv("UV_INDEX_URL") or os.getenv("PIP_INDEX_URL")
    if not raw:
        return RegistryStatus(False, None)
    try:
        host = urlparse(raw).hostname
    except ValueError:
        host = None
    if not host:
        return RegistryStatus(True, False)
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return RegistryStatus(True, False)
    return RegistryStatus(True, True)


def required_names(pyproject_path: Path, groups: tuple[str, ...]) -> set[str]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {})
    missing_groups = sorted(group for group in groups if group not in optional)
    if missing_groups:
        raise ValueError("unknown optional dependency group(s): " + ", ".join(missing_groups))
    raw = list(project.get("dependencies", []))
    for group in groups:
        raw.extend(optional[group])
    return {Requirement(item).name.lower() for item in raw}


def locked_names(lock_path: Path) -> set[str]:
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    return {
        str(item.get("name", "")).lower()
        for item in data.get("package", [])
        if item.get("name")
    }


def installed(required: set[str]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for package in sorted(required):
        module = IMPORT_OVERRIDES.get(package, package.replace("-", "_"))
        try:
            result[package] = importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError, AttributeError, ValueError):
            result[package] = False
    return result


def evaluate(pyproject_path: Path, lock_path: Path, groups: tuple[str, ...]) -> dict[str, object]:
    required = required_names(pyproject_path, groups)
    locked = locked_names(lock_path)
    module_state = installed(required)
    missing_lock = sorted(required - locked)
    missing_modules = sorted(name for name, present in module_state.items() if not present)
    registry = registry_status()
    ready = not missing_lock and not missing_modules and registry.configured and registry.dns_resolves is True
    return {
        "ready": ready,
        "python": sys.version.split()[0],
        "groups": list(groups),
        "required_count": len(required),
        "locked_required_count": len(required) - len(missing_lock),
        "installed_required_count": len(required) - len(missing_modules),
        "missing_lock_packages": missing_lock,
        "missing_runtime_modules": missing_modules,
        "registry": asdict(registry),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed CK-NEXUS dependency closure gate.")
    parser.add_argument("--pyproject", type=Path, default=ROOT / "pyproject.toml")
    parser.add_argument("--lock", type=Path, default=ROOT / "uv.lock")
    parser.add_argument("--groups", nargs="*", default=list(DEFAULT_GROUPS))
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.pyproject, args.lock, tuple(args.groups))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"[FAIL] dependency closure: {exc}")
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.as_json:
        print(rendered)
    elif not args.output:
        print("[PASS] dependency closure" if result["ready"] else "[FAIL] dependency closure")
        print(
            f"Lock: {result['locked_required_count']}/{result['required_count']} required packages present"
        )
        print(
            f"Runtime: {result['installed_required_count']}/{result['required_count']} required modules present"
        )
        print("Missing lock packages: " + (", ".join(result["missing_lock_packages"]) or "none"))
        print("Missing runtime modules: " + (", ".join(result["missing_runtime_modules"]) or "none"))
        registry = result["registry"]
        print(
            "Registry: configured={configured} dns_resolves={dns_resolves}".format(**registry)
        )
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
