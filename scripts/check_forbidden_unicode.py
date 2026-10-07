from __future__ import annotations

import argparse
import subprocess
import sys
import unicodedata
from pathlib import Path


SCANNED_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".ps1",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}


def _changed_files(base: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _is_forbidden(character: str) -> bool:
    codepoint = ord(character)
    if codepoint in {0x200D, 0xFE0F}:
        return True
    if 0x1F000 <= codepoint <= 0x1FAFF:
        return True
    if 0x2600 <= codepoint <= 0x27BF:
        return True
    return unicodedata.category(character) == "So"


def _scan(path: Path) -> list[tuple[int, int, str]]:
    if path.suffix.lower() not in SCANNED_SUFFIXES or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    findings: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for column, character in enumerate(line, start=1):
            if _is_forbidden(character):
                findings.append((line_number, column, f"U+{ord(character):04X}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--changed-from")
    args = parser.parse_args()

    paths = [Path(value) for value in args.files]
    if args.changed_from:
        paths.extend(_changed_files(args.changed_from))

    unique_paths = sorted(set(paths))
    failed = False
    for path in unique_paths:
        for line_number, column, codepoint in _scan(path):
            failed = True
            print(f"{path}:{line_number}:{column}: forbidden unicode {codepoint}")

    if failed:
        print("Forbidden decorative or emoji Unicode characters detected.")
        return 1
    print("Forbidden Unicode check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
