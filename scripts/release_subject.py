#!/usr/bin/env python3
"""Deterministic CK-NEXUS release-subject calculator.

The subject is SHA-256 over the exact byte stream emitted by:
    git ls-tree -r <commit> -- <scope pathspecs>

This intentionally preserves the existing workflow algorithm. It hashes tracked
Git tree entries (mode, type, object ID, and path), not working-tree bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from collections.abc import Sequence
from pathlib import Path

ALGORITHM_VERSION = "git-ls-tree-sha256-v1"

RUNTIME_PATHS = (
    "app",
    "creator_app",
    "services",
    "gateway",
    "orchestration",
    "idea_engine",
    "migrations",
    "deploy",
    "observability",
    "Dockerfile",
    "docker-compose.prod.yml",
    "main.py",
    "pyproject.toml",
    "uv.lock",
)

APPLICATION_PATHS = (
    "creator_app",
    "services",
    "tests",
    "scripts",
    "main.py",
    "pyproject.toml",
    "uv.lock",
)

PATH_SCOPES: dict[str, tuple[str, ...]] = {
    "runtime": RUNTIME_PATHS,
    "application": APPLICATION_PATHS,
}


@dataclass(frozen=True, slots=True)
class ReleaseSubject:
    scope: str
    ref: str
    commit_sha: str
    tree_sha: str
    subject_sha256: str
    entry_count: int
    pathspecs: tuple[str, ...]
    algorithm: str
    calculator_sha256: str

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["pathspecs"] = list(self.pathspecs)
        return result


def _git(root: Path, args: Sequence[str]) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
    )
    if process.returncode:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        command = " ".join(args)
        raise RuntimeError(f"git {command} failed: {detail or process.returncode}")
    return process.stdout


def calculate_release_subject(
    ref: str = "HEAD",
    scope: str = "runtime",
    repo: str | Path | None = None,
) -> ReleaseSubject:
    """Calculate a subject for a committed Git tree and a named path scope."""
    if scope not in PATH_SCOPES:
        raise ValueError(f"unknown scope {scope!r}; choose one of {', '.join(PATH_SCOPES)}")

    start = Path(repo or Path.cwd()).resolve()
    root_text = _git(start, ("rev-parse", "--show-toplevel")).decode("utf-8").strip()
    root = Path(root_text)

    commit = _git(
        root,
        ("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"),
    ).decode("ascii").strip()
    tree = _git(root, ("rev-parse", f"{commit}^{{tree}}")).decode("ascii").strip()

    listing = _git(root, ("ls-tree", "-r", commit, "--", *PATH_SCOPES[scope]))
    script_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    return ReleaseSubject(
        scope=scope,
        ref=ref,
        commit_sha=commit,
        tree_sha=tree,
        subject_sha256=hashlib.sha256(listing).hexdigest(),
        entry_count=listing.count(b"\n"),
        pathspecs=PATH_SCOPES[scope],
        algorithm=ALGORITHM_VERSION,
        calculator_sha256=script_digest,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calculate the canonical CK-NEXUS Git-tree release subject."
    )
    parser.add_argument("--scope", choices=tuple(PATH_SCOPES), default="runtime")
    parser.add_argument("--ref", default="HEAD", help="commit, tag, or branch (default: HEAD)")
    parser.add_argument("--repo", type=Path, help="Git repository to inspect (default: cwd)")
    parser.add_argument("--json", action="store_true", help="emit full provenance JSON")
    parser.add_argument(
        "--expected-subject",
        help="compare with a frozen SHA-256; never changes the expected value",
    )
    args = parser.parse_args(argv)

    try:
        result = calculate_release_subject(ref=args.ref, scope=args.scope, repo=args.repo)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"release subject calculation failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.as_dict(), sort_keys=True, indent=2))
    else:
        print(result.subject_sha256)

    if args.expected_subject and result.subject_sha256 != args.expected_subject.lower():
        print(
            "release subject mismatch: "
            f"expected={args.expected_subject.lower()} actual={result.subject_sha256}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
