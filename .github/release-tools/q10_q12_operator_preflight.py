from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = "spinlnw10-art/ck-nexus"
CLOSURE_SHA = "a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53"
CLOSURE_TREE = "19038af4121b61667789bc7e83705e9dbf4cd141"
RUNTIME_SOURCE_SHA = "ad2fac7aa0752117dde065c7ad9b0b8d41136aa2"
RUNTIME_SOURCE_TREE = "eb2074176319072ca3f31d5c8c990752ba849b0a"
RUNTIME_SUBJECT = "772662ac4ed60e785f30370c0c66bfdf8f798ea5f67fe13063404b20f2f74200"

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def load(path: str) -> dict[str, object]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must be a JSON object")
    return data


def main() -> int:
    failures: list[str] = []
    checks: dict[str, object] = {}

    try:
        closure_tree = git("show", "-s", "--format=%T", CLOSURE_SHA)
        checks["closure_tree"] = closure_tree
        if closure_tree != CLOSURE_TREE:
            failures.append("closure_tree_mismatch")
    except Exception as exc:
        failures.append(f"closure_commit_unavailable:{type(exc).__name__}")

    try:
        runtime_tree = git("show", "-s", "--format=%T", RUNTIME_SOURCE_SHA)
        checks["runtime_source_tree"] = runtime_tree
        if runtime_tree != RUNTIME_SOURCE_TREE:
            failures.append("runtime_source_tree_mismatch")
    except Exception as exc:
        failures.append(f"runtime_source_unavailable:{type(exc).__name__}")

    try:
        repository_root = Path(__file__).resolve().parents[2]
        calculator = repository_root / "scripts" / "release_subject.py"
        subject = subprocess.check_output(
            [
                sys.executable,
                str(calculator),
                "--scope",
                "runtime",
                "--ref",
                RUNTIME_SOURCE_SHA,
            ],
            cwd=repository_root,
            text=True,
        ).strip()
        checks["runtime_subject"] = subject
        if subject != RUNTIME_SUBJECT:
            failures.append("runtime_subject_mismatch")
    except Exception as exc:
        failures.append(f"runtime_subject_unavailable:{type(exc).__name__}")

    try:
        q10 = load("evidence/Q10_DEPENDENCY_AUDIT.json")
        checks["q10_component_result"] = q10.get("component_result")
        checks["q10_gate_result"] = q10.get("gate_result")
        checks["q10_open_source_security_scan"] = q10.get("open_source_security_scan")
        if q10.get("release_subject_manifest_sha256") != RUNTIME_SUBJECT:
            failures.append("q10_stale_subject")
        if q10.get("component_result") != "PASS":
            failures.append("q10_dependency_component_not_pass")
    except Exception as exc:
        failures.append(f"q10_evidence_unavailable:{type(exc).__name__}")

    try:
        q11 = load("evidence/Q11_OPENAI_LIVE.json")
        checks["q11_result"] = q11.get("result")
        if q11.get("release_subject_manifest_sha256") != RUNTIME_SUBJECT:
            failures.append("q11_stale_subject")
    except Exception as exc:
        failures.append(f"q11_evidence_unavailable:{type(exc).__name__}")

    try:
        q12 = load("evidence/Q12_CGROUP_V2.json")
        checks["q12_result"] = q12.get("result")
        if q12.get("release_subject_manifest_sha256") != RUNTIME_SUBJECT:
            failures.append("q12_stale_subject")
    except Exception as exc:
        failures.append(f"q12_evidence_unavailable:{type(exc).__name__}")

    report = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "closure_sha": CLOSURE_SHA,
        "runtime_source_sha": RUNTIME_SOURCE_SHA,
        "expected_runtime_subject": RUNTIME_SUBJECT,
        "checks": checks,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "production_ready": False,
        "note": (
            "This preflight validates operator inputs only; it never promotes Q10/Q11/Q12 to PASS."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
