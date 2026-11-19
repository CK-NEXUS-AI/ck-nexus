#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(rb"(?i)authorization:\s*bearer\s+[A-Za-z0-9._~+/-]{12,}"),
    re.compile(rb"(?i)sonar_token\s*[=:]\s*[^\s]+"),
    re.compile(rb"(?i)(?:password|secret|private[_-]?key)\s*[=:]\s*[^\s]+"),
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_reports_no_secrets.py <report-dir>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1])
    token = os.getenv("SONAR_TOKEN", "").encode()
    failures: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if token and len(token) >= 8 and token in data:
            failures.append(f"{path}: exact SONAR_TOKEN value detected")
        for pattern in PATTERNS:
            if pattern.search(data):
                failures.append(f"{path}: secret-like material detected")
                break

    if failures:
        for item in failures:
            print(item, file=sys.stderr)
        return 1

    print(f"REPORT_SECRET_SCAN=PASS files={sum(1 for p in root.rglob('*') if p.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
