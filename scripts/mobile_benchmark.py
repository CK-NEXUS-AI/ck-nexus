from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rss_kib() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _read_meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        token = value.strip().split()[0] if value.strip() else "0"
        if token.isdigit():
            result[key] = int(token)
    return result


def _run(command: list[str], timeout: float) -> dict[str, object]:
    started = time.perf_counter()
    before = _rss_kib()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    elapsed = time.perf_counter() - started
    after = _rss_kib()
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": round(elapsed, 6),
        "harness_peak_rss_kib_before": before,
        "harness_peak_rss_kib_after": after,
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "stdout_bytes": len(completed.stdout.encode()),
        "stderr_bytes": len(completed.stderr.encode()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("benchmark command is required")

    output = Path(args.output)
    meminfo_before = _read_meminfo()
    record = {
        "schema": "ck-nexus.mobile-benchmark.v1",
        "claim": "mobile_runtime_candidate",
        "claim_status": "MEASURED_NOT_VERIFIED",
        "label": args.label,
        "captured_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "android_root": os.environ.get("ANDROID_ROOT"),
        "termux_version": os.environ.get("TERMUX_VERSION"),
        "mem_total_kib": meminfo_before.get("MemTotal"),
        "mem_available_kib_before": meminfo_before.get("MemAvailable"),
        "measurement": _run(command, args.timeout),
    }
    meminfo_after = _read_meminfo()
    record["mem_available_kib_after"] = meminfo_after.get("MemAvailable")
    record["limitations"] = [
        "Harness ru_maxrss measures the Python harness, not complete Android system memory.",
        "Use external process or Android system metrics for authoritative target-process RSS/PSS.",
        "A single successful run does not prove the 4 GB device class claim.",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": _sha256(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
