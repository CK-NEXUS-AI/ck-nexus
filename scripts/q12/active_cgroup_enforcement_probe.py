from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def read_kv(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            values[parts[0]] = int(parts[1])
    return values


def delta(after: dict[str, int], before: dict[str, int], key: str) -> int:
    return after.get(key, 0) - before.get(key, 0)


def attached(group: Path, pid: int) -> bool:
    return str(pid) in (group / "cgroup.procs").read_text(encoding="utf-8").split()


def make_group(root: Path, name: str) -> Path:
    group = root / name
    group.mkdir(exist_ok=False)
    return group


def kill_residual(group: Path) -> None:
    try:
        pids = [int(value) for value in (group / "cgroup.procs").read_text().split()]
    except OSError:
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    time.sleep(0.05)


def cleanup(group: Path | None) -> None:
    if group is None:
        return
    kill_residual(group)
    for _ in range(20):
        try:
            group.rmdir()
            return
        except OSError:
            time.sleep(0.05)


def cpu_probe(root: Path, token: str) -> dict[str, Any]:
    group: Path | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        group = make_group(root, f"cknexus-q12-cpu-{token}")
        (group / "cpu.max").write_text("20000 100000", encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import time\nend=time.monotonic()+2.0\nx=0\n"
                "while time.monotonic()<end: x+=1\n",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (group / "cgroup.procs").write_text(str(process.pid), encoding="utf-8")
        pid_attached = attached(group, process.pid)
        before = read_kv(group / "cpu.stat")
        process.wait(timeout=8)
        after = read_kv(group / "cpu.stat")
        throttled = max(
            delta(after, before, "nr_throttled"),
            delta(after, before, "throttled_usec"),
        )
        return {"pid_attached": pid_attached, "throttle_delta": throttled, "passed": pid_attached and throttled > 0}
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        cleanup(group)


def memory_probe(root: Path, token: str) -> dict[str, Any]:
    group: Path | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        group = make_group(root, f"cknexus-q12-memory-{token}")
        (group / "memory.max").write_text(str(32 * 1024 * 1024), encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys,time\nsys.stdin.buffer.read(1)\n"
                "parts=[]\n"
                "for _ in range(160): parts.append(bytearray(1024*1024))\n"
                "time.sleep(2)\n",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (group / "cgroup.procs").write_text(str(process.pid), encoding="utf-8")
        pid_attached = attached(group, process.pid)
        before = read_kv(group / "memory.events")
        assert process.stdin is not None
        process.stdin.write(b"1")
        process.stdin.close()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        after = read_kv(group / "memory.events")
        event_delta = {
            key: delta(after, before, key) for key in ("max", "oom", "oom_kill")
        }
        limited = any(value > 0 for value in event_delta.values())
        return {"pid_attached": pid_attached, "event_delta": event_delta, "passed": pid_attached and limited}
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        cleanup(group)


def pids_probe(root: Path, token: str) -> dict[str, Any]:
    group: Path | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        group = make_group(root, f"cknexus-q12-pids-{token}")
        (group / "pids.max").write_text("8", encoding="utf-8")
        code = (
            "import subprocess,sys,time\n"
            "sys.stdin.buffer.read(1)\n"
            "children=[]\n"
            "for _ in range(32):\n"
            "  try: children.append(subprocess.Popen(['sleep','2']))\n"
            "  except OSError: break\n"
            "for child in children:\n"
            "  try: child.wait(timeout=4)\n"
            "  except Exception: child.kill(); child.wait()\n"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (group / "cgroup.procs").write_text(str(process.pid), encoding="utf-8")
        pid_attached = attached(group, process.pid)
        before = read_kv(group / "pids.events")
        assert process.stdin is not None
        process.stdin.write(b"1")
        process.stdin.close()
        process.wait(timeout=10)
        after = read_kv(group / "pids.events")
        max_delta = delta(after, before, "max")
        return {"pid_attached": pid_attached, "max_event_delta": max_delta, "passed": pid_attached and max_delta > 0}
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        cleanup(group)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded active CK-NEXUS Q12 cgroup v2 enforcement probe")
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    if os.getenv("CKNEXUS_ENVIRONMENT", "").strip().lower() != "staging":
        emit({"status": "BLOCKED", "reason": "CKNEXUS_ENVIRONMENT_must_be_staging"})
        return 2
    root = args.root.expanduser().resolve()
    if root == Path("/sys/fs/cgroup") or not root.is_dir() or not os.access(root, os.W_OK):
        emit({"status": "BLOCKED", "reason": "dedicated_delegated_root_required"})
        return 2
    token = f"{os.getpid()}-{time.time_ns()}"
    try:
        cpu = cpu_probe(root, token)
        memory = memory_probe(root, token)
        pids = pids_probe(root, token)
    except Exception as exc:
        emit({"status": "FAIL", "reason": type(exc).__name__})
        return 1
    passed = bool(cpu["passed"] and memory["passed"] and pids["passed"])
    emit({"status": "PASS" if passed else "FAIL", "cpu": cpu, "memory": memory, "pids": pids})
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
