from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_IMPORTS = {
    "aiosqlite": "aiosqlite",
    "asyncpg": "asyncpg",
    "psycopg": "psycopg",
    "redis": "redis",
    "ruff": "ruff",
    "bandit": "bandit",
    "pip-audit": "pip_audit",
}


@dataclass(frozen=True)
class RegistryProbe:
    configured: bool
    host: str | None
    dns_resolves: bool | None


def _registry_host() -> RegistryProbe:
    # Never return the URL itself: registry URLs may embed credentials.
    raw = os.getenv("UV_INDEX_URL") or os.getenv("PIP_INDEX_URL")
    if not raw:
        return RegistryProbe(False, None, None)
    try:
        host = urlparse(raw).hostname
    except ValueError:
        host = None
    if not host:
        return RegistryProbe(True, None, False)
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        resolves = False
    else:
        resolves = True
    return RegistryProbe(True, host, resolves)


def installed_modules(required: dict[str, str] | None = None) -> dict[str, bool]:
    required = required or REQUIRED_IMPORTS
    return {name: importlib.util.find_spec(module) is not None for name, module in required.items()}


def evaluate() -> dict[str, object]:
    modules = installed_modules()
    registry = _registry_host()
    missing = sorted(name for name, present in modules.items() if not present)
    ready = not missing and registry.configured and registry.dns_resolves is True
    return {
        "ready": ready,
        "python": sys.version.split()[0],
        "registry": asdict(registry),
        "modules": modules,
        "missing_modules": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed CK-NEXUS trusted toolchain readiness gate.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = evaluate()
    rendered = json.dumps(result, indent=2, sort_keys=True) if args.as_json or args.output else None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.as_json:
        print(rendered)
    elif not args.output:
        status = "PASS" if result["ready"] else "FAIL"
        print(f"[{status}] trusted toolchain ready={str(result['ready']).lower()}")
        registry = result["registry"]
        print(
            "Registry: configured={configured} host={host} dns_resolves={dns_resolves}".format(**registry)
        )
        missing = result["missing_modules"]
        print("Missing modules: " + (", ".join(missing) if missing else "none"))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
