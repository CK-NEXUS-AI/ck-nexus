from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creator_app.agnes.execution.phase3.hardening import CgroupLimits, CgroupV2Manager  # noqa: E402


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="CK-NEXUS delegated cgroup v2 staging enforcement gate")
    parser.add_argument("--root", default=os.getenv("CKNEXUS_AGNES_CGROUP_ROOT", "/sys/fs/cgroup"))
    args = parser.parse_args()

    if os.getenv("CKNEXUS_ENVIRONMENT", "").strip().lower() != "staging":
        emit({"status": "BLOCKED", "reason": "CKNEXUS_ENVIRONMENT_must_be_staging"})
        return 2

    manager = CgroupV2Manager(Path(args.root).expanduser().resolve(), group_prefix="cknexus-r18-probe")
    health = manager.health()
    if not health.get("ready"):
        emit({"status": "BLOCKED", "reason": "delegated_cgroup_v2_unavailable", "health": health})
        return 2

    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    cgroup = None
    try:
        cgroup = manager.create(
            f"{os.getpid()}-{child.pid}",
            CgroupLimits(cpu_quota_us=20_000, cpu_period_us=100_000, memory_max_bytes=64 * 1024 * 1024, pids_max=16),
        )
        manager.attach(cgroup, child.pid)
        time.sleep(0.05)
        procs = (cgroup / "cgroup.procs").read_text(encoding="utf-8").split()
        observed = {
            "cpu.max": (cgroup / "cpu.max").read_text(encoding="utf-8").strip(),
            "memory.max": (cgroup / "memory.max").read_text(encoding="utf-8").strip(),
            "pids.max": (cgroup / "pids.max").read_text(encoding="utf-8").strip(),
            "pid_attached": str(child.pid) in procs,
        }
        passed = observed == {
            "cpu.max": "20000 100000",
            "memory.max": str(64 * 1024 * 1024),
            "pids.max": "16",
            "pid_attached": True,
        }
        emit({"status": "PASS" if passed else "FAIL", "health": health, "observed": observed})
        return 0 if passed else 1
    except Exception as exc:
        emit({"status": "FAIL", "reason": type(exc).__name__, "health": health})
        return 1
    finally:
        child.terminate()
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=2)
        if cgroup is not None:
            manager.cleanup(cgroup)


if __name__ == "__main__":
    raise SystemExit(main())
