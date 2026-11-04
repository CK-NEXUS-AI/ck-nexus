#!/usr/bin/env python3
"""Read-only CK-NEXUS development status collector. Python stdlib only."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.getenv("CKNEXUS_DEV_STATUS_FILE", ROOT / "data/dev_status.json"))
TIMEOUT = 20
SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)(\s*[=:]\s*)[^\s,;]+"),
)


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        safe = {}
        for key, child in value.items():
            if re.search(r"(?i)api[_-]?key|token|secret|password|credential", str(key)):
                safe[str(key)] = "[REDACTED]"
            else:
                safe[str(key)] = redact(child)
        return safe
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        result = value
        for pattern in SECRET_PATTERNS:
            result = pattern.sub(
                lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]",
                result,
            )
        return result
    return value


def command(args: list[str], *, cwd: Path = ROOT) -> Any:
    safe_args = args
    if args and args[0] == "git":
        safe_args = ["git", "-c", f"safe.directory={ROOT}", *args[1:]]
    completed = subprocess.run(
        safe_args, cwd=cwd, text=True, capture_output=True, timeout=TIMEOUT, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{args[0]} exited {completed.returncode}: {completed.stderr[-500:]}")
    if "--json" in args:
        return json.loads(completed.stdout)
    return completed.stdout.strip()


def service_state(name: str) -> str:
    completed = subprocess.run(
        ["systemctl", "is-active", name],
        text=True,
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )
    state = completed.stdout.strip()
    if not state:
        raise RuntimeError(f"systemctl is-active returned no state for {name}")
    return state


def item(value: Any, source: str, status: str = "ok") -> dict[str, Any]:
    return {"value": redact(value), "source": source, "collected_at": now(), "status": status}


def failed(source: str, exc: Exception) -> dict[str, Any]:
    return {"value": None, "source": source, "collected_at": now(), "status": "error",
            "error": redact(f"{type(exc).__name__}: {exc}")}


def collect() -> dict[str, Any]:
    data: dict[str, Any] = {}
    try:
        head = command(["git", "rev-parse", "HEAD"])
        branch = command(["git", "branch", "--show-current"])
        dirty = bool(command(["git", "status", "--porcelain"]))
        upstream = subprocess.run(
            ["git", "-c", f"safe.directory={ROOT}", "rev-parse", "--abbrev-ref", "@{upstream}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=TIMEOUT,
        )
        ahead_behind = {"ahead": None, "behind": None}
        if upstream.returncode == 0:
            counts = command(["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
            ahead, behind = map(int, counts.split())
            ahead_behind = {"ahead": ahead, "behind": behind}
        data["git"] = item({"head": head, "branch": branch, "dirty": dirty, **ahead_behind},
                           "git rev-parse/status/rev-list")
    except Exception as exc:
        data["git"] = failed("git", exc)

    calls = {
        "open_prs": ["gh", "pr", "list", "--state", "open", "--limit", "500",
                     "--json", "number,title,isDraft,mergeStateStatus,statusCheckRollup,url"],
        "open_issues": ["gh", "issue", "list", "--state", "open", "--limit", "500",
                        "--json", "number,title,url"],
        "main_ci": ["gh", "run", "list", "--branch", "main", "--limit", "20",
                    "--json", "databaseId,name,status,conclusion,createdAt,headSha,url"],
    }
    for key, args in calls.items():
        if key in {"open_prs", "open_issues", "main_ci"} and not (
            os.getenv("GH_TOKEN", "").strip() or os.getenv("GITHUB_TOKEN", "").strip()
        ):
            data[key] = failed(
                "GitHub API (read-only token)",
                RuntimeError(
                    "no read-only GitHub token configured; broader credentials are not used"
                ),
            )
            continue
        try:
            value = command(args)
            if key == "main_ci":
                completed = [r for r in value if r.get("status") == "completed"]
                value = {
                    "runs": value,
                    "pass": sum(r.get("conclusion") == "success" for r in completed),
                    "fail": sum(
                        r.get("conclusion") not in ("success", "skipped", "neutral")
                        for r in completed
                    ),
                }
            data[key] = item(value, " ".join(args))
        except Exception as exc:
            data[key] = failed(" ".join(args), exc)

    try:
        raw = command(
            ["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--plain"]
        )
        names = []
        for line in raw.splitlines():
            parts = line.split()
            if parts and re.search(r"ck|nexus|creator|gateway|scanner|mcp", parts[0], re.I):
                names.append(parts[0])
        states = {}
        for name in names:
            try:
                states[name] = service_state(name)
            except Exception as exc:
                states[name] = {"status": "error", "detail": redact(str(exc))}
        data["services"] = item(states, "systemctl list-units + is-active")
    except Exception as exc:
        data["services"] = failed("systemctl", exc)

    try:
        listeners = command(["ss", "-ltnH"])
        mcp = [line for line in listeners.splitlines() if re.search(r":8765\b", line)]
        valid = bool(mcp) and all(re.search(r"127\.0\.0\.1:8765\b", line) for line in mcp)
        data["mcp"] = item(
            {"listener_lines": mcp, "loopback_only": valid},
            "ss -ltnH",
            status="ok" if valid else "error",
        )
    except Exception as exc:
        data["mcp"] = failed("ss -ltnH", exc)

    try:
        disk = command(["df", "-h", "/"])
        data["disk"] = item(disk, "df -h /")
    except Exception as exc:
        data["disk"] = failed("df -h /", exc)

    try:
        release = (ROOT / "RELEASE_STATUS.md").read_text(encoding="utf-8")
        decision = re.search(r"^Decision:\s*\*\*(.*?)\*\*", release, re.M)
        data["production_status"] = item(decision.group(1) if decision else None,
                                         "RELEASE_STATUS.md: Decision")
        if not decision:
            data["production_status"]["status"] = "error"
    except Exception as exc:
        data["production_status"] = failed("RELEASE_STATUS.md", exc)

    data["qwen_probe"] = load_qwen_probe_state()
    return {"schema_version": 1, "collected_at": now(), "items": data}


def load_qwen_probe_state() -> dict[str, Any]:
    state_file = OUTPUT.with_name("qwen_probe_state.json")
    try:
        previous = json.loads(state_file.read_text(encoding="utf-8"))
        result = previous.get("result")
        if not isinstance(result, dict):
            raise ValueError("invalid Qwen probe state")
        if result.get("last_success"):
            return item(result, "daily Qwen probe state file")
        return {
            "value": result,
            "source": "daily Qwen probe state file",
            "collected_at": previous.get("collected_at", now()),
            "status": "error",
        }
    except Exception as exc:
        return failed("daily Qwen probe state file", exc)


def probe_qwen_daily() -> dict[str, Any]:
    state_file = OUTPUT.with_name("qwen_probe_state.json")
    today = datetime.now(UTC).date().isoformat()
    try:
        previous = json.loads(state_file.read_text()) if state_file.exists() else {}
        if previous.get("date") == today:
            cached = previous.get("result")
            if isinstance(cached, dict) and cached.get("last_success"):
                return item(cached, "daily authenticated Qwen probe cache")
            return {
                "value": cached,
                "source": "daily authenticated Qwen probe cache",
                "collected_at": previous.get("collected_at", now()),
                "status": "error",
            }
        key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        base = os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/")
        model = os.getenv("QWEN_MODEL", "").strip()
        if not key or not model:
            return failed(
                "authenticated Qwen daily probe",
                RuntimeError("credentials or model not configured; no result cached"),
            )
        parsed = urlparse(base)
        allowed_host = (
            parsed.hostname in {"dashscope-intl.aliyuncs.com", "dashscope.aliyuncs.com"}
            or bool(parsed.hostname and parsed.hostname.endswith(".maas.aliyuncs.com"))
        )
        if (
            parsed.scheme != "https"
            or not allowed_host
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.path != "/compatible-mode/v1"
            or parsed.query
            or parsed.fragment
        ):
            return failed(
                "authenticated Qwen daily probe",
                RuntimeError("DASHSCOPE_BASE_URL is not an approved HTTPS DashScope endpoint"),
            )
        body = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": "Reply OK"}],
                "max_tokens": 8,
            }
        ).encode()
        req = Request(base + "/chat/completions", data=body, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        started = time.monotonic()
        try:
            with urlopen(req, timeout=15) as response:
                payload = json.loads(response.read(65536))
                success = response.status == 200 and bool(payload.get("choices"))
                result = {"last_success": now() if success else None,
                          "last_failure": None if success else now(),
                          "http_status": response.status,
                          "latency_seconds": round(time.monotonic() - started, 2),
                          "model": model}
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            result = {"last_success": None, "last_failure": now(),
                      "detail": type(exc).__name__}
        state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"date": today, "result": result, "collected_at": now()}, ensure_ascii=False)
        )
        os.chmod(tmp, 0o640)
        os.replace(tmp, state_file)
        if result.get("last_success"):
            return item(result, "authenticated DashScope chat completion (max_tokens=8)")
        return {
            "value": result,
            "source": "authenticated DashScope chat completion (max_tokens=8)",
            "collected_at": now(),
            "status": "error",
        }
    except Exception as exc:
        return failed("authenticated Qwen daily probe", exc)


def write_atomic(payload: dict[str, Any]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    safe = redact(payload)
    fd, tmp_name = tempfile.mkstemp(prefix=".dev_status.", suffix=".tmp", dir=OUTPUT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(safe, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_name, 0o640)
        os.replace(tmp_name, OUTPUT)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


if __name__ == "__main__":
    write_atomic(collect())
