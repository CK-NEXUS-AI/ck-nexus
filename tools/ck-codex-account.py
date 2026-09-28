#!/usr/bin/env python3
"""CK-Codex Account Switcher.

Manages isolated CODEX_HOME directories and delegates authentication to the
official Codex CLI. Credentials stay inside Codex's own profile directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def now() -> str:
    return datetime.now(UTC).isoformat()


def root() -> Path:
    configured = os.environ.get("CK_CODEX_ACCOUNTS_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".ck-codex-accounts"


def metadata_path() -> Path:
    return root() / "accounts.json"


def load() -> dict:
    path = metadata_path()
    if not path.exists():
        return {"version": 1, "active": None, "accounts": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid metadata file: {path}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("accounts", {}), dict):
        raise SystemExit(f"Invalid metadata schema: {path}")
    return data


def save(data: dict) -> None:
    base = root()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = metadata_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)


def validate_name(name: str) -> str:
    if not NAME_RE.fullmatch(name):
        raise SystemExit(
            "Invalid profile name. Use 1-64 chars: letters, digits, dot, underscore, hyphen."
        )
    return name


def profile_path(name: str) -> Path:
    return root() / "profiles" / validate_name(name)


def ensure_cli() -> str:
    configured = os.environ.get("CKNEXUS_CODEX_BIN", "codex")
    if "/" in configured:
        path = Path(configured).expanduser()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise SystemExit(f"Codex executable not found: {path}")
        return str(path)
    found = shutil.which(configured)
    if not found:
        raise SystemExit(
            "Codex CLI not found. Install the official @openai/codex package first."
        )
    return found


def secure_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def command_env(name: str) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    env["CODEX_HOME"] = str(profile_path(name))
    return env


def cmd_add(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    data = load()
    path = profile_path(name)
    if name in data["accounts"]:
        raise SystemExit(f"Profile already exists: {name}")
    secure_dir(path)
    timestamp = now()
    data["accounts"][name] = {"created_at": timestamp, "updated_at": timestamp}
    save(data)
    print(f"CREATED {name}")
    print(f"CODEX_HOME={path}")
    return 0


def cmd_login(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    data = load()
    if name not in data["accounts"]:
        cmd_add(argparse.Namespace(name=name))
        data = load()
    cli = ensure_cli()
    path = profile_path(name)
    secure_dir(path)
    print(f"Starting official Codex login for profile: {name}")
    print("Complete the browser sign-in yourself. Do not send credentials to CK-NEXUS.")
    result = subprocess.run([cli, "login"], env=command_env(name), check=False)
    if result.returncode == 0:
        data["accounts"][name]["updated_at"] = now()
        data["active"] = name
        save(data)
        print(f"ACTIVE {name}")
    return result.returncode


def cmd_status(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    data = load()
    if name not in data["accounts"]:
        raise SystemExit(f"Unknown profile: {name}")
    cli = ensure_cli()
    return subprocess.run(
        [cli, "login", "status"],
        env=command_env(name),
        check=False,
    ).returncode


def cmd_list(_: argparse.Namespace) -> int:
    data = load()
    active = data.get("active")
    for name in sorted(data["accounts"]):
        marker = "*" if name == active else " "
        print(f"{marker} {name}")
    if not data["accounts"]:
        print("(no profiles)")
    return 0


def cmd_env(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    data = load()
    if name not in data["accounts"]:
        raise SystemExit(f"Unknown profile: {name}")
    print(f"export CODEX_HOME={shlex_quote(str(profile_path(name)))}")
    return 0


def shlex_quote(value: str) -> str:
    # POSIX shell single-quote escaping without importing shell helpers.
    return "'" + value.replace("'", "'\\''") + "'"


def cmd_run(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    data = load()
    if name not in data["accounts"]:
        raise SystemExit(f"Unknown profile: {name}")
    if not args.command:
        raise SystemExit("Usage: ... run PROFILE -- COMMAND [ARGS...]")
    result = subprocess.run(args.command, env=command_env(name), check=False)
    if result.returncode == 0:
        data["active"] = name
        data["accounts"][name]["updated_at"] = now()
        save(data)
    return result.returncode


def cmd_remove(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    data = load()
    if name not in data["accounts"]:
        raise SystemExit(f"Unknown profile: {name}")
    if not args.confirm:
        raise SystemExit("Refusing to remove a profile without --confirm.")
    shutil.rmtree(profile_path(name))
    del data["accounts"][name]
    if data.get("active") == name:
        data["active"] = None
    save(data)
    print(f"REMOVED {name}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CK-Codex Account Switcher")
    sub = p.add_subparsers(dest="action", required=True)

    s = sub.add_parser("add")
    s.add_argument("name")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("login")
    s.add_argument("name")
    s.set_defaults(fn=cmd_login)

    s = sub.add_parser("status")
    s.add_argument("name")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("list")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("env")
    s.add_argument("name")
    s.set_defaults(fn=cmd_env)

    s = sub.add_parser("run")
    s.add_argument("name")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("remove")
    s.add_argument("name")
    s.add_argument("--confirm", action="store_true")
    s.set_defaults(fn=cmd_remove)

    return p


if __name__ == "__main__":
    args = parser().parse_args()
    raise SystemExit(args.fn(args))
