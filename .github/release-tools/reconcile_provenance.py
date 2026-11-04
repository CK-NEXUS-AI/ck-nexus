#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-run exact-subject release evidence provenance")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not os.environ.get("GITHUB_REPOSITORY"):
        os.environ["GITHUB_REPOSITORY"] = "spinlnw10-art/ck-nexus"
    cmd = [
        "python3",
        ".github/release-tools/verify_release_evidence_provenance.py",
        "--expected-subject",
        EXPECTED_SUBJECT,
        "--output",
        str(args.output),
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, timeout=180)
    if args.output.is_file():
        payload = json.loads(args.output.read_text(encoding="utf-8"))
    else:
        payload = {"result": "BLOCKED", "errors": ["provenance verifier produced no output"]}
    print(json.dumps(payload, indent=2, sort_keys=True))
    if proc.stderr.strip():
        print(proc.stderr.strip())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
