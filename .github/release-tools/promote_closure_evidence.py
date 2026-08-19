#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

EXPECTED_SOURCE = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
EXPECTED_TREE = "0525195934f703a8becf8a39f6397b2411e0bb2e"
EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
CLOSURE_BRANCH = "release/q10-q16-closure"
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


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, timeout=90
    )
    return proc.stdout.strip()


def runtime_subject() -> str:
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "HEAD", "--", *RUNTIME_PATHS],
        check=True,
        capture_output=True,
        timeout=60,
    )
    import hashlib

    return hashlib.sha256(proc.stdout).hexdigest()


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote verified Q10/Q11/Q12 evidence onto the closure branch without runtime drift"
    )
    parser.add_argument("--q10", required=True, type=Path)
    parser.add_argument("--q11", required=True, type=Path)
    parser.add_argument("--q12", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    args = parser.parse_args()

    q10, q11, q12, provenance = map(load, (args.q10, args.q11, args.q12, args.provenance))
    if q10.get("gate_result") != "PASS" or q10.get("codex_security_deep_scan") != "PASS":
        raise SystemExit("Q10 is not verified PASS")
    if q11.get("result") != "PASS" or q11.get("production_promotion_allowed") is not True:
        raise SystemExit("Q11 is not verified PASS")
    if q12.get("result") != "PASS" or q12.get("actual_kernel_enforcement") is not True:
        raise SystemExit("Q12 is not verified PASS")
    if provenance.get("result") != "PASS" or provenance.get("evidence_files_checked") != 8:
        raise SystemExit("provenance is not 8/8 PASS")
    if provenance.get("provenance_failures"):
        raise SystemExit("provenance contains failures")

    git("fetch", "origin", f"refs/heads/{CLOSURE_BRANCH}")
    git("checkout", "-B", "closure-evidence-promotion", "FETCH_HEAD")
    if git("show", "-s", "--format=%T", EXPECTED_SOURCE) != EXPECTED_TREE:
        raise SystemExit("frozen runtime source tree mismatch")
    if runtime_subject() != EXPECTED_SUBJECT:
        raise SystemExit("closure branch runtime subject drift detected")

    destinations = {
        args.q10: Path("evidence/Q10_DEPENDENCY_AUDIT.json"),
        args.q11: Path("evidence/Q11_OPENAI_LIVE.json"),
        args.q12: Path("evidence/Q12_CGROUP_V2.json"),
    }
    for source, destination in destinations.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    provenance_destination = Path("evidence/closure/RELEASE_EVIDENCE_PROVENANCE_LATEST.json")
    provenance_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.provenance, provenance_destination)

    if runtime_subject() != EXPECTED_SUBJECT:
        raise SystemExit("evidence promotion unexpectedly changed runtime subject")
    git("config", "user.name", "ck-nexus-closure-bot")
    git("config", "user.email", "ck-nexus-closure-bot@users.noreply.github.com")
    git(
        "add",
        "evidence/Q10_DEPENDENCY_AUDIT.json",
        "evidence/Q11_OPENAI_LIVE.json",
        "evidence/Q12_CGROUP_V2.json",
        str(provenance_destination),
    )
    staged = git("diff", "--cached", "--name-only").splitlines()
    allowed = {
        "evidence/Q10_DEPENDENCY_AUDIT.json",
        "evidence/Q11_OPENAI_LIVE.json",
        "evidence/Q12_CGROUP_V2.json",
        str(provenance_destination),
    }
    if not staged or set(staged) - allowed:
        raise SystemExit(f"unexpected staged paths: {staged}")
    git("commit", "-m", "release: promote verified Q10-Q12 closure evidence")
    commit_sha = git("rev-parse", "HEAD")
    if runtime_subject() != EXPECTED_SUBJECT:
        raise SystemExit("runtime subject changed after evidence commit")
    git("push", "origin", f"{commit_sha}:refs/heads/{CLOSURE_BRANCH}")
    print(
        json.dumps(
            {
                "result": "PASS",
                "closure_branch": CLOSURE_BRANCH,
                "commit_sha": commit_sha,
                "runtime_subject": EXPECTED_SUBJECT,
                "production_ready_claim": False,
                "pr14_merge_performed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
