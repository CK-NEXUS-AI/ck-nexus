#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fail-closed Q12 delegated cgroup v2 verification")
    parser.add_argument("--gate-script", default="scripts/agnes_cgroup_v2_staging_gate.py")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    root = os.environ.get("CKNEXUS_AGNES_CGROUP_ROOT", "")
    result = {
        "gate": "Q12",
        "result": "BLOCKED",
        "release_subject": EXPECTED_SUBJECT,
        "non_root": os.geteuid() != 0,
        "delegated": False,
        "production_promotion_allowed": False,
        "errors": [],
    }
    if os.geteuid() == 0:
        result["errors"].append("Q12 must run as a non-root service identity")
    elif not root:
        result["errors"].append("CKNEXUS_AGNES_CGROUP_ROOT is not configured")
    else:
        root_path = Path(root)
        controllers = root_path / "cgroup.controllers"
        if not root_path.is_dir() or not os.access(root_path, os.W_OK):
            result["errors"].append("delegated cgroup root is missing or not writable")
        elif not controllers.is_file():
            result["errors"].append("cgroup.controllers is missing")
        else:
            available = set(controllers.read_text(encoding="utf-8").split())
            required = {"cpu", "memory", "pids"}
            if not required.issubset(available):
                result["errors"].append("required cpu/memory/pids controllers are unavailable")
            else:
                result["delegated"] = True
                try:
                    proc = subprocess.run(
                        ["python3", args.gate_script],
                        check=False,
                        capture_output=True,
                        text=True,
                        env=os.environ.copy(),
                        timeout=120,
                    )
                    payload = json.loads(proc.stdout)
                    expected = {
                        "cpu_max": "20000 100000",
                        "memory_max": "67108864",
                        "pids_max": "16",
                    }
                    for key, value in expected.items():
                        if payload.get(key) != value:
                            result["errors"].append(f"{key} mismatch")
                    if payload.get("escape_attempt_blocked") is not True:
                        result["errors"].append("escape attempt was not proven blocked")
                    if proc.returncode == 0 and not result["errors"]:
                        result.update(payload)
                        result["result"] = "PASS"
                        result["production_promotion_allowed"] = True
                except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                    result["errors"].append(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
