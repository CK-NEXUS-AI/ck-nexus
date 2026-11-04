from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY = "CK-NEXUS-AI/ck-nexus"
RUNTIME_PATHS = (
    "app", "creator_app", "services", "gateway", "orchestration",
    "idea_engine", "migrations", "deploy", "observability", "Dockerfile",
    "docker-compose.prod.yml", "main.py", "pyproject.toml", "uv.lock",
)
REQUIRED_Q10_TOOLS = {
    "Semgrep", "Bandit", "Gitleaks", "pip-audit", "Trivy",
    "CK-NEXUS security regression", "coverage/completeness",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def load(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must be a JSON object")
    return data


def subject_for(commit: str) -> str:
    listing = git("ls-tree", "-r", commit, "--", *RUNTIME_PATHS)
    return hashlib.sha256((listing + "\n").encode()).hexdigest()


def main() -> int:
    failures: list[str] = []
    checks: dict[str, Any] = {}
    try:
        identity = load("evidence/RELEASE_SUBJECT.json")
        candidate_sha = git("rev-parse", "HEAD")
        candidate_tree = git("rev-parse", "HEAD^{tree}")
        expected_subject = str(identity["runtime_subject_manifest_sha256"])
        if identity.get("candidate_branch") != "release/q10-q16-closure-20261105":
            failures.append("candidate_branch_mismatch")
        if not isinstance(identity.get("release_pr_number"), int) or identity.get("release_pr_number", 0) < 1:
            failures.append("release_pr_number_missing")
        git("fetch", "origin", "main")
        if git("rev-parse", "origin/main") != identity.get("baseline_main_sha"):
            failures.append("main_branch_drift_from_frozen_baseline")
        if git("rev-parse", "origin/main^{tree}") != identity.get("baseline_main_tree"):
            failures.append("main_tree_drift_from_frozen_baseline")
        if git("rev-parse", f"{candidate_sha}^{{tree}}") != candidate_tree:
            failures.append("candidate_tree_mismatch")
        if subject_for(candidate_sha) != expected_subject:
            failures.append("candidate_runtime_subject_mismatch")
        if subject_for("HEAD") != expected_subject:
            failures.append("current_release_line_runtime_subject_mismatch")
        checks.update({
            "candidate_source_sha": candidate_sha,
            "candidate_source_tree": candidate_tree,
            "runtime_subject_manifest_sha256": expected_subject,
        })
    except Exception as exc:
        failures.append(f"release_subject_unavailable:{type(exc).__name__}")
        candidate_sha = candidate_tree = expected_subject = ""

    try:
        request = load("evidence/q10/Q10_SCAN_REQUEST_FINAL_SUBJECT.json")
        required_tools = set(request.get("required_tools", []))
        checks["q10_request_status"] = request.get("status")
        checks["q10_required_tools"] = sorted(required_tools)
        if request.get("target_sha") is not None:
            failures.append("q10_request_must_bind_to_workflow_head_not_a_moving_or_external_sha")
        if request.get("target_sha_binding") != "workflow_run.head_sha":
            failures.append("q10_request_source_binding_invalid")
        if request.get("release_subject_manifest_sha256") != expected_subject:
            failures.append("q10_request_runtime_subject_mismatch")
        if request.get("scan_mode") != "layered" or not REQUIRED_Q10_TOOLS.issubset(required_tools):
            failures.append("q10_request_tool_contract_incomplete")
        if request.get("status") not in {"PREPARED_NOT_EXECUTED", "EXECUTED_PENDING_REVIEW"}:
            failures.append("q10_request_state_invalid")
        if request.get("production_status") != "NO-GO":
            failures.append("q10_request_must_remain_no_go")
    except Exception as exc:
        failures.append(f"q10_request_unavailable:{type(exc).__name__}")

    for filename in ("Q10_DEPENDENCY_AUDIT.json", "Q11_OPENAI_LIVE.json", "Q12_CGROUP_V2.json"):
        try:
            evidence = load(f"evidence/{filename}")
            checks[f"{filename}_gate_result"] = evidence.get("gate_result", evidence.get("result"))
            if evidence.get("source_sha") != candidate_sha or evidence.get("source_tree") != candidate_tree:
                checks[f"{filename}_status"] = "STALE_HISTORICAL_EVIDENCE_IGNORED"
            elif evidence.get("release_subject_manifest_sha256") != expected_subject:
                failures.append(f"{filename}_runtime_subject_mismatch")
        except FileNotFoundError:
            checks[f"{filename}_status"] = "NOT_YET_GENERATED"
        except Exception as exc:
            failures.append(f"{filename}_invalid:{type(exc).__name__}")

    report = {
        "schema_version": 2,
        "repository": REPOSITORY,
        "candidate_source_sha": candidate_sha,
        "candidate_source_tree": candidate_tree,
        "expected_runtime_subject": expected_subject,
        "checks": checks,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "production_ready": False,
        "note": "Operator preflight validates candidate identity and fail-closed inputs only; it never promotes any Q gate or production status.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
