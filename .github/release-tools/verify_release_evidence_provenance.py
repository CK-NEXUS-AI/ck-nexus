from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creator_app.connector_fabric.transport import UrllibHttpTransport  # noqa: E402

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

EXPECTED_BRANCH = "closure/q10-q16-unification-20261105"
OWNER_GITHUB_LOGIN = "spinlnw10-art"
EXPECTED_BRANCHES = {
    "Q10": {EXPECTED_BRANCH},
    "Q11": {EXPECTED_BRANCH},
    "Q12": {EXPECTED_BRANCH},
    "Q13": {EXPECTED_BRANCH},
    "Q14": {EXPECTED_BRANCH},
    "Q15": {EXPECTED_BRANCH},
    "Q16_PRODUCTION_IMAGE": {EXPECTED_BRANCH},
    "Q16_RUNTIME_LICENSES": {EXPECTED_BRANCH},
}
EXPECTED_ARTIFACT_PREFIXES = {
    "Q10": "q10-open-source-security-",
    "Q11": "q11-final-",
    "Q12": "q12-final-",
    "Q13": "q13-postgres-dr-",
    "Q14": "q14-final-",
    "Q15": "q15-clean-machine-",
    "Q16_PRODUCTION_IMAGE": "q16-production-image-",
    "Q16_RUNTIME_LICENSES": "q16-runtime-licenses-",
}


def _api_payload(url: str, token: str) -> Any:
    response = UrllibHttpTransport(max_response_bytes=2_000_000).request(
        "GET",
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ck-nexus-release-evidence-verifier",
        },
        body=None,
        timeout=20,
    )
    if response.status != 200:
        raise RuntimeError(f"GitHub API returned HTTP {response.status}")
    return json.loads(response.body)


def _api_json(url: str, token: str) -> dict[str, Any]:
    data = _api_payload(url, token)
    if not isinstance(data, dict):
        raise TypeError("expected JSON object from GitHub API")
    return data


def _api_list(url: str, token: str) -> list[dict[str, Any]]:
    data = _api_payload(url, token)
    if not isinstance(data, list):
        raise TypeError("expected JSON array from GitHub API")
    return data


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
    try:
        release_subject = _load(evidence_dir / "RELEASE_SUBJECT.json")
    except Exception as exc:
        release_subject = {}
        failures.append(f"RELEASE_SUBJECT.json: cannot load candidate identity ({type(exc).__name__})")
    if release_subject.get("runtime_subject_manifest_sha256") != expected_subject:
        failures.append("RELEASE_SUBJECT.json: runtime subject mismatch")
    if release_subject.get("candidate_branch") != EXPECTED_BRANCH:
        failures.append("RELEASE_SUBJECT.json: candidate branch mismatch")
    if release_subject.get("owner_github_login") != OWNER_GITHUB_LOGIN:
        failures.append("RELEASE_SUBJECT.json: owner identity does not match pinned repository owner")
    if not isinstance(release_subject.get("release_pr_number"), int) or release_subject.get("release_pr_number", 0) < 1:
        failures.append("RELEASE_SUBJECT.json: release PR number missing or invalid")
    try:
        q10_identity = _load(evidence_dir / "Q10_DEPENDENCY_AUDIT.json")
    except Exception as exc:
        q10_identity = {}
        failures.append(f"Q10_DEPENDENCY_AUDIT.json: cannot load candidate identity ({type(exc).__name__})")
    candidate_sha = q10_identity.get("source_sha")
    candidate_tree = q10_identity.get("source_tree")
    if not isinstance(candidate_sha, str) or len(candidate_sha) != 40:
        failures.append("Q10_DEPENDENCY_AUDIT.json: candidate source SHA missing or invalid")
    if not isinstance(candidate_tree, str) or len(candidate_tree) != 40:
        failures.append("Q10_DEPENDENCY_AUDIT.json: candidate source tree missing or invalid")
    if q10_identity.get("release_subject_manifest_sha256") != expected_subject:
        failures.append("Q10_DEPENDENCY_AUDIT.json: candidate runtime subject mismatch")

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
        if evidence.get("source_sha") != candidate_sha or evidence.get("source_tree") != candidate_tree:
            failures.append(f"{filename}: source SHA/tree does not match RELEASE_SUBJECT.json")
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

        try:
            artifact = _api_json(
                f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}",
                token,
            )
            run = _api_json(
                f"https://api.github.com/repos/{repository}/actions/runs/{run_id}",
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
            "artifact_head_sha_match": workflow_run.get("head_sha") == candidate_sha,
            "run_head_sha_match": run.get("head_sha") == candidate_sha,
            "artifact_name_match": artifact.get("name") == f"{EXPECTED_ARTIFACT_PREFIXES.get(gate, '')}{candidate_sha}",
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

        if gate == "Q10":
            scanner_ok = (
                evidence.get("gate_result") == "NOT_VERIFIED"
                and evidence.get("open_source_security_scan") == "PASS"
                and evidence.get("security_assessment_status") == "READY_FOR_HUMAN_REVIEW"
                and evidence.get("production_promotion_allowed") is False
                and evidence.get("security_scan_run_id") == run_id
                and bool(evidence.get("security_report_sha256"))
                and bool(evidence.get("security_scan_completed_at"))
            )
            approval_checks: dict[str, Any] = {"scanner_evidence_ready": scanner_ok}
            api_review_ok = False
            reviewer_login = owner_login = review_url = owner_url = None
            if scanner_ok:
                try:
                    pr_number = int(release_subject["release_pr_number"])
                    pr = _api_json(
                        f"https://api.github.com/repos/{repository}/pulls/{pr_number}", token
                    )
                    reviews = _api_list(
                        f"https://api.github.com/repos/{repository}/pulls/{pr_number}/reviews?per_page=100", token
                    )
                    comments = _api_list(
                        f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments?per_page=100", token
                    )
                    current_head = (pr.get("head") or {}).get("sha")
                    candidate_ref = str(candidate_sha)
                    report_sha = str(evidence["security_report_sha256"])
                    matching_reviews = [
                        item for item in reviews
                        if item.get("state") == "APPROVED"
                        and item.get("commit_id") == current_head
                        and "CKNEXUS-Q10-REVIEW-APPROVED" in (item.get("body") or "")
                        and "COVERAGE-REVIEWED" in (item.get("body") or "")
                        and "FINDINGS-REVIEWED" in (item.get("body") or "")
                        and "NON-EQUIVALENCE-ACKNOWLEDGED" in (item.get("body") or "")
                        and candidate_ref in (item.get("body") or "")
                        and report_sha in (item.get("body") or "")
                    ]
                    matching_reviews.sort(key=lambda item: item.get("submitted_at", ""))
                    expected_owner = OWNER_GITHUB_LOGIN
                    reviewer_association = None
                    owner_association = None
                    for review in matching_reviews:
                        review_user = review.get("user") or {}
                        candidate_reviewer = review_user.get("login")
                        association = str(review.get("author_association", "")).upper()
                        if (
                            not candidate_reviewer
                            or candidate_reviewer == expected_owner
                            or review_user.get("type") != "User"
                            or association not in {"COLLABORATOR", "MEMBER"}
                        ):
                            continue
                        reviewer_login = candidate_reviewer
                        review_url = review.get("html_url")
                        reviewer_association = association
                        review_time = _time(review["submitted_at"])
                        break
                    matching_comments = [
                        item for item in comments
                        if (item.get("user") or {}).get("login") == expected_owner
                        and str(item.get("author_association", "")).upper() in {"MEMBER", "OWNER"}
                        and "CKNEXUS-Q10-OWNER-APPROVED" in (item.get("body") or "")
                        and candidate_ref in (item.get("body") or "")
                        and report_sha in (item.get("body") or "")
                    ]
                    matching_comments.sort(key=lambda item: item.get("created_at", ""))
                    if reviewer_login and review_url:
                        for comment in matching_comments:
                            if _time(comment["created_at"]) >= review_time:
                                owner_login = expected_owner
                                owner_url = comment.get("html_url")
                                owner_association = str(comment.get("author_association", "")).upper()
                                owner_time = _time(comment["created_at"])
                                break
                    scan_time = _time(str(evidence["security_scan_completed_at"]))
                    pr_ok = (
                        pr.get("state") == "closed"
                        and pr.get("merged") is True
                        and (pr.get("base") or {}).get("ref") == "main"
                        and (pr.get("head") or {}).get("ref") == EXPECTED_BRANCH
                    )
                    api_review_ok = bool(
                        pr_ok and reviewer_login and owner_login
                        and reviewer_association in {"COLLABORATOR", "MEMBER"}
                        and owner_association in {"MEMBER", "OWNER"}
                        and reviewer_login != owner_login
                        and review_time >= scan_time
                        and owner_time >= review_time
                    )
                    approval_checks.update({
                        "release_pr_merged_to_main": pr_ok,
                        "independent_approved_review_exists": bool(reviewer_login),
                        "reviewer_author_association": reviewer_association,
                        "reviewer_is_repository_collaborator_or_member": reviewer_association in {"COLLABORATOR", "MEMBER"},
                        "owner_identity_matches_release_manifest": owner_login == release_subject.get("owner_github_login"),
                        "owner_approval_comment_exists": bool(owner_login and owner_url),
                        "owner_author_association": owner_association,
                        "owner_identity_is_pinned": owner_login == OWNER_GITHUB_LOGIN,
                        "review_after_scan_and_owner_after_review": api_review_ok,
                        "independent_reviewer": reviewer_login,
                        "independent_review_reference": review_url,
                        "owner_approval_actor": owner_login,
                        "owner_approval_reference": owner_url,
                        "reviewed_source_sha": candidate_sha,
                        "reviewed_source_tree": candidate_tree,
                        "reviewed_release_subject_manifest_sha256": expected_subject,
                        "reviewed_report_sha256": report_sha,
                    })
                except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                    approval_checks["github_review_attestation_lookup"] = f"ERROR:{type(exc).__name__}"
            if not scanner_ok or not api_review_ok:
                failures.append(
                    "Q10: scanner evidence, independent APPROVED PR review, or final repository Owner approval is missing/invalid"
                )
            checks["q10_human_approval"] = {"approved": api_review_ok, **approval_checks}

        row.update(
            {
                "artifact_digest": artifact_digest,
                "artifact_name": artifact.get("name"),
                "artifact_head_branch": actual_branch,
                "artifact_head_sha": workflow_run.get("head_sha"),
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
        "candidate_source_sha": candidate_sha,
        "candidate_source_tree": candidate_tree,
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
