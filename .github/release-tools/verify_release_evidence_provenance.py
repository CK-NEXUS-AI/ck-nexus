from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote

EVIDENCE_FILES = (
    "Q10_DEPENDENCY_AUDIT.json",
    "Q11_OPENAI_LIVE.json",
    "Q12_CGROUP_V2.json",
    "Q13_POSTGRES_DR.json",
    "Q14_OBSERVABILITY_ALERT.json",
    "Q15_CLEAN_MACHINE.json",
    "Q16_PRODUCTION_IMAGE.json",
    "Q16_RUNTIME_LICENSE_SUMMARY.json",
)

EXPECTED_BRANCHES = {
    "Q10": {"release/q10-q16-closure", "verify/q10-dependency-audit"},
    "Q11": {"verify/q11-final-subject"},
    "Q12": {"verify/q12-final-subject"},
    "Q13": {"release/q10-q16-closure"},
    "Q14": {"verify/q14-final-subject"},
    "Q15": {"release/q10-q16-closure"},
    "Q16_PRODUCTION_IMAGE": {"release/q10-q16-closure"},
    "Q16_RUNTIME_LICENSES": {"release/q10-q16-closure"},
}


def _api_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ck-nexus-release-evidence-verifier",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def verify(
    *,
    repository: str,
    token: str,
    expected_subject: str,
    evidence_dir: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []

    for filename in EVIDENCE_FILES:
        path = evidence_dir / filename
        try:
            evidence = _load(path)
        except Exception as exc:  # fail closed while preserving a useful report
            failures.append(f"{filename}: cannot load evidence ({type(exc).__name__})")
            continue

        gate = str(evidence.get("gate") or filename)
        subject = evidence.get("release_subject_manifest_sha256")
        artifact_id = evidence.get("artifact_id")
        artifact_digest = evidence.get("artifact_digest")
        run_id = evidence.get("github_run_id")
        source_sha = evidence.get("source_sha")
        source_tree = evidence.get("source_tree")
        row: dict[str, Any] = {
            "file": filename,
            "gate": gate,
            "artifact_id": artifact_id,
            "github_run_id": run_id,
            "provenance": "FAIL",
        }

        if subject != expected_subject:
            failures.append(f"{filename}: stale release subject")
            rows.append(row)
            continue
        if not isinstance(artifact_id, int) or not isinstance(run_id, int):
            failures.append(f"{filename}: artifact_id/github_run_id missing")
            rows.append(row)
            continue
        if not isinstance(artifact_digest, str) or not artifact_digest.startswith("sha256:"):
            failures.append(f"{filename}: artifact_digest missing or invalid")
            rows.append(row)
            continue
        if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
            failures.append(f"{filename}: source_sha missing or invalid")
            rows.append(row)
            continue
        if not isinstance(source_tree, str) or not re.fullmatch(r"[0-9a-f]{40}", source_tree):
            failures.append(f"{filename}: source_tree missing or invalid")
            rows.append(row)
            continue

        try:
            artifact = _api_json(
                f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}",
                token,
            )
            run = _api_json(
                f"https://api.github.com/repos/{repository}/actions/runs/{run_id}",
                token,
            )
            source_commit = _api_json(
                f"https://api.github.com/repos/{repository}/commits/{quote(source_sha, safe='')}",
                token,
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            failures.append(f"{filename}: GitHub provenance lookup failed ({type(exc).__name__})")
            rows.append(row)
            continue

        workflow_run = artifact.get("workflow_run") or {}
        actual_branch = workflow_run.get("head_branch")
        allowed_branches = EXPECTED_BRANCHES.get(gate)

        checks = {
            "artifact_not_expired": artifact.get("expired") is False,
            "artifact_digest_match": artifact.get("digest") == artifact_digest,
            "artifact_run_match": workflow_run.get("id") == run_id,
            "run_repository_match": (run.get("repository") or {}).get("full_name") == repository,
            "branch_allowed": allowed_branches is None or actual_branch in allowed_branches,
            "run_head_sha_matches_evidence": run.get("head_sha") == source_sha,
            "artifact_head_sha_matches_run": workflow_run.get("head_sha") == run.get("head_sha"),
            "run_branch_matches_artifact": run.get("head_branch") == actual_branch,
            "source_tree_matches_github_commit": (
                (source_commit.get("commit") or {}).get("tree", {}).get("sha")
                == source_tree
            ),
        }
        for check, passed in checks.items():
            if not passed:
                failures.append(f"{filename}: {check} failed")

        claimed_pass = evidence.get("result") in {"PASS", "PASS_CANDIDATE"}
        claimed_pass = claimed_pass or evidence.get("component_result") == "PASS"
        claimed_pass = claimed_pass or evidence.get("status") == "PASS"
        if claimed_pass and run.get("conclusion") != "success":
            failures.append(f"{filename}: PASS evidence came from non-success run")
            checks["successful_run_for_pass_evidence"] = False
        else:
            checks["successful_run_for_pass_evidence"] = True

        if gate == "Q10" and evidence.get("gate_result") == "PASS":
            scan_fields = (
                "security_scan_run_id",
                "security_report_sha256",
                "security_scan_completed_at",
            )
            missing = [field for field in scan_fields if not evidence.get(field)]
            if evidence.get("open_source_security_scan") != "PASS" or missing:
                failures.append(
                    "Q10_DEPENDENCY_AUDIT.json: Q10 PASS lacks complete "
                    "open-source security-scan provenance"
                )
                checks["q10_open_source_scan_provenance"] = False
            else:
                checks["q10_open_source_scan_provenance"] = True

        row.update(
            {
                "artifact_digest": artifact_digest,
                "artifact_name": artifact.get("name"),
                "artifact_head_branch": actual_branch,
                "artifact_head_sha": workflow_run.get("head_sha"),
                "evidence_source_sha": source_sha,
                "evidence_source_tree": source_tree,
                "verified_commit_tree": (
                    (source_commit.get("commit") or {}).get("tree", {}).get("sha")
                ),
                "workflow_name": run.get("name"),
                "workflow_conclusion": run.get("conclusion"),
                "checks": checks,
                "provenance": "PASS" if all(checks.values()) else "FAIL",
            }
        )
        rows.append(row)

    report = {
        "schema_version": 1,
        "repository": repository,
        "expected_release_subject": expected_subject,
        "evidence_files_checked": len(EVIDENCE_FILES),
        "provenance_failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "evidence": rows,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--expected-subject", required=True)
    parser.add_argument("--evidence-dir", default="evidence")
    parser.add_argument("--output", default="release-evidence-provenance.json")
    args = parser.parse_args()

    if not args.repository:
        parser.error("--repository or GITHUB_REPOSITORY is required")
    if not args.token:
        parser.error("--token or GITHUB_TOKEN is required")

    report = verify(
        repository=args.repository,
        token=args.token,
        expected_subject=args.expected_subject,
        evidence_dir=Path(args.evidence_dir),
    )
    Path(args.output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
