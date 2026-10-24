from __future__ import annotations

import re
import subprocess
from pathlib import Path

PATTERNS = {
    "openai_key": re.compile(r"(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "github_pat": re.compile(r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(item.decode()) for item in out.split(b"\0") if item]


def main() -> int:
    hits: list[str] = []
    for path in tracked_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                hits.append(f"{name}: {path}")
    if hits:
        print("SECRET SCAN: FAIL")
        print("\n".join(hits))
        return 1
    print(f"SECRET SCAN: PASS ({len(tracked_files())} tracked files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
