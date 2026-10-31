#!/usr/bin/env python3
"""Read-only CK-NEXUS health check with redacted, checksummed evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    from scripts._safe_http import safe_urlopen
except ImportError:
    from _safe_http import safe_urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
REQUIRED_SERVICES = (
    "cknexus-api-gateway.service",
    "cknexus-scanner.service",
    "cknexus-watchdog.timer",
    "cknexus-mcp.service",
)
REQUIRED_CONTAINERS = ("ck-sentinel", "ck-ops", "ck-auditor")


def run(args: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", help="Evidence output directory (must be inside repo/evidence)"
    )
    args = parser.parse_args()
    now = dt.datetime.now().astimezone()
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    default_dir = ROOT / "evidence" / now.strftime("%Y-%m-%d") / "phase-1" / f"ck-health-{stamp}"
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_dir.resolve()
    evidence_root = (ROOT / "evidence").resolve()
    if not out.is_relative_to(evidence_root):
        print("ERROR: output directory must be under repository evidence/", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)

    checks: list[dict[str, object]] = []
    stderr_messages: list[str] = []

    def add(name: str, status: str, detail: str, duration_ms: int = 0) -> None:
        checks.append(
            {"name": name, "status": status, "detail": detail, "duration_ms": max(0, duration_ms)}
        )

    def timed(name: str, fn) -> None:
        start = time.monotonic()
        try:
            status, detail = fn()
        except Exception as exc:  # diagnostics must continue after individual failures
            status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
            stderr_messages.append(f"{name}: {type(exc).__name__}: {exc}")
        add(name, status, detail, int((time.monotonic() - start) * 1000))

    def check_systemd() -> tuple[str, str]:
        p = run(["systemctl", "is-system-running"], timeout=4)
        value = (p.stdout or p.stderr).strip() or f"exit={p.returncode}"
        failed = run(["systemctl", "--failed", "--no-legend", "--no-pager", "--plain"], timeout=4)
        failed_units = []
        if failed.returncode == 0:
            for line in failed.stdout.splitlines():
                parts = line.split()
                if (
                    parts
                    and parts[0].endswith(".service")
                    or (parts and parts[0].endswith(".timer"))
                ):
                    failed_units.append(parts[0])
        detail = (
            f"systemd={value}; failed_units={','.join(failed_units) if failed_units else 'none'}"
        )
        return ("PASS" if p.returncode == 0 and value == "running" else "WARN", detail)

    timed("systemd", check_systemd)

    for service in REQUIRED_SERVICES:

        def service_check(service: str = service) -> tuple[str, str]:
            p = run(["systemctl", "is-active", service], timeout=4)
            state = (p.stdout or p.stderr).strip() or f"exit={p.returncode}"
            return (
                "PASS" if p.returncode == 0 and state == "active" else "FAIL",
                f"{service}={state}",
            )

        timed(f"service:{service}", service_check)

    def disk_check() -> tuple[str, str]:
        usage = shutil.disk_usage("/")
        pct = round(usage.used * 100 / usage.total, 1)
        free_gib = round(usage.free / (1024**3), 2)
        status = "FAIL" if pct >= 95 else ("WARN" if pct >= 85 else "PASS")
        return status, f"root_used_percent={pct}; free_gib={free_gib}; warn_at=85%; fail_at=95%"

    timed("filesystem_root", disk_check)

    def docker_check() -> tuple[str, str]:
        p = run(["docker", "ps", "--format", "{{.Names}}"], timeout=6)
        if p.returncode != 0:
            return "FAIL", "docker ps failed; daemon/client unavailable"
        running = set(p.stdout.splitlines())
        missing = sorted(set(REQUIRED_CONTAINERS) - running)
        if missing:
            return "FAIL", f"required_containers_not_running={','.join(missing)}"
        return "PASS", f"required_containers_running={','.join(REQUIRED_CONTAINERS)}"

    timed("docker_required_containers", docker_check)

    def git_check() -> tuple[str, str]:
        status = run(["git", "-C", str(ROOT), "status", "--porcelain", "--branch"], timeout=5)
        if status.returncode != 0:
            return "FAIL", "git status failed"
        lines = status.stdout.splitlines()
        dirty_count = sum(1 for line in lines[1:] if line.strip())
        counts = run(
            ["git", "-C", str(ROOT), "rev-list", "--left-right", "--count", "main...origin/main"],
            timeout=5,
        )
        if counts.returncode != 0:
            return (
                "WARN",
                f"git_status_ok; dirty_entries={dirty_count}; branch_comparison_unavailable",
            )
        parts = counts.stdout.split()
        if len(parts) != 2:
            return "WARN", f"git_status_ok; dirty_entries={dirty_count}; unexpected_branch_counts"
        ahead, behind = map(int, parts)
        status_code = "WARN" if dirty_count or ahead or behind else "PASS"
        branch_line = lines[0] if lines else "branch_unknown"
        return (
            status_code,
            f"{branch_line}; dirty_entries={dirty_count}; main_ahead={ahead}; main_behind={behind}",
        )

    timed("git_worktree_and_drift", git_check)

    def openclaw_check() -> tuple[str, str]:
        path = shutil.which("openclaw")
        return (
            ("PASS", f"openclaw_cli={path}")
            if path
            else (
                "WARN",
                "openclaw CLI not installed/in PATH on VPS; Termux fallback remains available",
            )
        )

    timed("openclaw_cli_presence", openclaw_check)

    def bind_check() -> tuple[str, str]:
        p = run(["ss", "-lntH"], timeout=4)
        if p.returncode != 0:
            return "WARN", "could not inspect listeners with ss"
        lines = p.stdout.splitlines()
        local = any(re.search(r"(?:127\.0\.0\.1|\[::1\]):8765\s", line) for line in lines)
        wildcard = any(re.search(r"(?:0\.0\.0\.0|\*|\[::\]):8765\s", line) for line in lines)
        if local and not wildcard:
            return "PASS", "MCP port 8765 bound to loopback only"
        return "FAIL", f"loopback_listener={local}; wildcard_listener={wildcard}"

    timed("mcp_loopback_bind", bind_check)

    def mcp_protocol_check() -> tuple[str, str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "ck-health", "version": "1.0"},
            },
        }
        req = urllib.request.Request(
            "http://127.0.0.1:8765/mcp",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        try:
            with safe_urlopen(req, timeout=4) as response:
                body = response.read(1024 * 1024)
                parsed = json.loads(body.decode("utf-8"))
                if (
                    response.status == 200
                    and isinstance(parsed, dict)
                    and ("result" in parsed or "error" in parsed)
                ):
                    return (
                        "PASS",
                        f"MCP initialize HTTP={response.status}; JSON-RPC response present",
                    )
                return "FAIL", f"MCP initialize HTTP={response.status}; response shape unexpected"
        except urllib.error.HTTPError as exc:
            return "FAIL", f"MCP initialize HTTP={exc.code}"
        except Exception as exc:
            return "FAIL", f"MCP initialize failed: {type(exc).__name__}"

    timed("mcp_protocol_initialize", mcp_protocol_check)

    overall = (
        "FAIL"
        if any(c["status"] == "FAIL" for c in checks)
        else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    )
    lines = [
        "CK-NEXUS health report",
        f"observed_at={now.isoformat()}",
        f"host={socket.gethostname()}",
        f"status={overall}",
        f"repo={ROOT}",
        f"evidence_dir={out}",
        "",
    ]
    for item in checks:
        lines.append(
            f"[{item['status']}] {item['name']}: {item['detail']} ({item['duration_ms']} ms)"
        )
    lines.append("")
    stdout_text = "\n".join(lines) + "\n"
    stderr_text = "\n".join(stderr_messages)
    (out / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (out / "stderr.log").write_text((stderr_text + "\n") if stderr_text else "", encoding="utf-8")
    audit = {
        "timestamp": now.isoformat(),
        "action": "read-only health checks; evidence files created",
        "source_mutated": False,
        "services_restarted": False,
        "files_deleted": False,
        "secrets_recorded": False,
        "rollback": (
            "Remove only this generated evidence directory after review; "
            "no source/service rollback required."
        ),
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    result = {
        "schema_version": SCHEMA_VERSION,
        "phase": "1-ck-health",
        "observed_at": now.isoformat(),
        "status": overall,
        "host": socket.gethostname(),
        "checks": checks,
        "evidence": {
            "stdout": "stdout.log",
            "stderr": "stderr.log",
            "result": "result.json",
            "sha256sums": "SHA256SUMS",
            "audit": "audit.json",
        },
        "audit": {
            "action": "read-only health checks; evidence files created",
            "source_mutated": False,
            "secrets_recorded": False,
            "rollback": (
                "Remove only this generated evidence directory after review; "
                "no source/service rollback required."
            ),
        },
        "rollback_plan": (
            "Health checks are read-only; source files, Git refs, and services are not changed."
        ),
        "details": {
            "repo": str(ROOT),
            "evidence_dir": str(out),
            "openclaw_missing_on_vps_is_warning": True,
        },
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for path in (out / "stdout.log", out / "stderr.log", out / "result.json", out / "audit.json"):
        path.chmod(0o600)
    sums = []
    for name in ("stdout.log", "stderr.log", "result.json", "audit.json"):
        sums.append(f"{sha256(out / name)}  {name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (out / "SHA256SUMS").chmod(0o600)
    print(stdout_text, end="")
    print("SHA256SUMS:")
    print("\n".join(sums))
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
