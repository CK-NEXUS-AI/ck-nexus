#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
SENTINEL = "CK-NEXUS-P0-SMOKE-PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Q11 live-provider smoke without exposing credentials")
    parser.add_argument("--script", default="scripts/test_openai_live.py")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = {
        "gate": "Q11",
        "result": "BLOCKED",
        "release_subject": EXPECTED_SUBJECT,
        "credential_configured": False,
        "credential_exposed": False,
        "sentinel_observed": False,
        "production_promotion_allowed": False,
        "errors": [],
    }
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        result["errors"].append("OPENAI_API_KEY is not configured")
    else:
        result["credential_configured"] = True
        env = os.environ.copy()
        try:
            proc = subprocess.run(
                ["python3", args.script],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            combined = f"{proc.stdout}\n{proc.stderr}"
            if key and key in combined:
                result["credential_exposed"] = True
                result["errors"].append("credential material appeared in process output")
            result["sentinel_observed"] = SENTINEL in combined
            if proc.returncode == 0 and result["sentinel_observed"] and not result["credential_exposed"]:
                result["result"] = "PASS"
                result["production_promotion_allowed"] = True
            else:
                result["errors"].append(f"live smoke failed with exit code {proc.returncode}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            result["errors"].append(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
