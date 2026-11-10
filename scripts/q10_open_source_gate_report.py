from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPORT_FILES = {
    "pip_audit": "q10-pip-audit.json",
    "bandit": "q10-bandit.json",
    "semgrep": "q10-semgrep.json",
    "gitleaks": "q10-gitleaks.json",
    "trivy": "q10-trivy.json",
    "attack_regression": "security-attack-regression.json",
    "secret_scan": "q10-secret-scan.txt",
    "tool_versions": "q10-tool-versions.json",
    "semgrep_ruleset": "q10-semgrep-ruleset.json",
    "issue_state": "q10-issue-state.json",
}
EXPECTED_SEMGREP_RULES_REPO = "https://github.com/semgrep/semgrep-rules"
EXPECTED_SEMGREP_RULES_COMMIT = "16b9e6d45f10649f6a531ec4838ed9924372c3bc"
EXPECTED_SEMGREP_RULE_DIRECTORIES = [
    "python",
    "javascript",
    "typescript",
    "generic",
    "dockerfile",
    "yaml",
    "bash",
    "json",
]
EXPECTED_TOOL_VERSIONS = {
    "semgrep": "1.183.0",
    "uv": "0.13.7",
    "gitleaks": "8.30.1",
    "trivy": "0.76.1",
}

EXIT_ENV = {
    "pip_audit": "Q10_PIP_AUDIT_RC",
    "bandit": "Q10_BANDIT_RC",
    "semgrep": "Q10_SEMGREP_RC",
    "gitleaks": "Q10_GITLEAKS_RC",
    "trivy": "Q10_TRIVY_RC",
    "attack_regression": "Q10_ATTACK_RC",
    "secret_scan": "Q10_SECRET_SCAN_RC",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exit_code(name: str) -> int:
    try:
        return int(os.environ[EXIT_ENV[name]])
    except (KeyError, ValueError):
        return 127


def severity_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key, "UNKNOWN")).upper() for row in rows))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()

    out = args.output_dir.resolve()
    missing = [name for name in REPORT_FILES.values() if not (out / name).is_file()]
    raw: dict[str, Any] = {}
    parse_errors: list[str] = []
    for name in (
        "pip_audit",
        "bandit",
        "semgrep",
        "gitleaks",
        "trivy",
        "attack_regression",
        "tool_versions",
        "semgrep_ruleset",
        "issue_state",
    ):
        path = out / REPORT_FILES[name]
        if path.is_file():
            try:
                raw[name] = read_json(path)
            except (OSError, json.JSONDecodeError):
                parse_errors.append(name)

    schema_errors: list[str] = []
    schema_validators = {
        "pip_audit": lambda value: (
            isinstance(value, dict)
            and isinstance(value.get("dependencies"), list)
            and all(
                isinstance(row, dict) and isinstance(row.get("vulns", []), list)
                for row in value.get("dependencies", [])
            )
        ),
        "bandit": lambda value: (
            isinstance(value, dict)
            and isinstance(value.get("results"), list)
            and all(isinstance(row, dict) for row in value.get("results", []))
        ),
        "semgrep": lambda value: (
            isinstance(value, dict)
            and isinstance(value.get("results"), list)
            and all(
                isinstance(row, dict) and isinstance(row.get("extra"), dict)
                for row in value.get("results", [])
            )
            and isinstance(value.get("paths"), dict)
            and isinstance(value["paths"].get("scanned"), list)
            and bool(value["paths"].get("scanned"))
            and all(isinstance(path, str) for path in value["paths"]["scanned"])
        ),
        "gitleaks": lambda value: (
            (isinstance(value, list) and all(isinstance(row, dict) for row in value))
            or (
                isinstance(value, dict)
                and isinstance(value.get("findings"), list)
                and all(isinstance(row, dict) for row in value["findings"])
            )
        ),
        "trivy": lambda value: (
            isinstance(value, dict)
            and isinstance(value.get("Results"), list)
            and all(
                isinstance(row, dict)
                and isinstance(row.get("Vulnerabilities", []), list)
                and isinstance(row.get("Misconfigurations", []), list)
                for row in value.get("Results", [])
            )
        ),
        "attack_regression": lambda value: (
            isinstance(value, dict)
            and all(
                isinstance(value.get(key), int)
                for key in ("tests_total", "tests_passed", "tests_failed")
            )
            and isinstance(value.get("issue_references"), list)
            and all(isinstance(row, dict) for row in value["issue_references"])
        ),
        "tool_versions": lambda value: (
            isinstance(value, dict) and all(name in value for name in EXPECTED_TOOL_VERSIONS)
        ),
        "semgrep_ruleset": lambda value: (
            isinstance(value, dict)
            and isinstance(value.get("repository"), str)
            and isinstance(value.get("commit"), str)
            and isinstance(value.get("directories"), list)
        ),
        "issue_state": lambda value: (
            isinstance(value, dict)
            and isinstance(value.get("issues"), list)
            and all(isinstance(row, dict) for row in value["issues"])
        ),
    }
    for name, validator in schema_validators.items():
        if name in raw and not validator(raw[name]):
            schema_errors.append(name)

    pip_data = raw.get("pip_audit", {})
    pip_rows = (
        pip_data.get("dependencies", [])
        if isinstance(pip_data, dict) and isinstance(pip_data.get("dependencies"), list)
        else []
    )
    pip_vulnerabilities = sum(
        len(row.get("vulns", [])) for row in pip_rows if isinstance(row, dict)
    )
    bandit_data = raw.get("bandit", {})
    bandit_rows = (
        bandit_data.get("results", [])
        if isinstance(bandit_data, dict) and isinstance(bandit_data.get("results"), list)
        else []
    )
    bandit_counts = severity_counts(bandit_rows, "issue_severity")
    semgrep_data = raw.get("semgrep", {})
    semgrep_rows = (
        semgrep_data.get("results", [])
        if isinstance(semgrep_data, dict) and isinstance(semgrep_data.get("results"), list)
        else []
    )
    semgrep_counts = severity_counts(
        [
            {"severity": (row.get("extra") or {}).get("severity", "UNKNOWN")}
            for row in semgrep_rows
            if isinstance(row, dict)
        ],
        "severity",
    )
    semgrep_error_rows = [
        row
        for row in semgrep_rows
        if isinstance(row, dict)
        and str((row.get("extra") or {}).get("severity", "UNKNOWN")).upper() == "ERROR"
    ]
    semgrep_nonsecurity_categories = {
        "maintainability",
        "correctness",
        "best-practice",
        "performance",
    }
    semgrep_security_error_rows = [
        row
        for row in semgrep_error_rows
        if str(((row.get("extra") or {}).get("metadata") or {}).get("category", "UNKNOWN")).lower()
        not in semgrep_nonsecurity_categories
    ]
    semgrep_audit_only_suffixes = (
        "dangerous-subprocess-use-audit",
        "dangerous-asyncio-create-exec-audit",
    )
    semgrep_audit_review_rows = [
        row
        for row in semgrep_security_error_rows
        if isinstance(row, dict)
        and str(row.get("check_id", "")).endswith(semgrep_audit_only_suffixes)
    ]
    semgrep_blocking_security_error_rows = list(semgrep_security_error_rows)
    semgrep_nonsecurity_error_rows = [
        row
        for row in semgrep_error_rows
        if str(((row.get("extra") or {}).get("metadata") or {}).get("category", "UNKNOWN")).lower()
        in semgrep_nonsecurity_categories
    ]
    gitleaks_raw = raw.get("gitleaks", [])
    if isinstance(gitleaks_raw, dict):
        gitleaks_rows = gitleaks_raw.get("findings", []) or []
        if not isinstance(gitleaks_rows, list):
            gitleaks_rows = []
    elif isinstance(gitleaks_raw, list):
        gitleaks_rows = gitleaks_raw
    else:
        gitleaks_rows = []
    trivy_data = raw.get("trivy", {})
    trivy_results = (
        trivy_data.get("Results", [])
        if isinstance(trivy_data, dict) and isinstance(trivy_data.get("Results"), list)
        else []
    )
    trivy_counts: Counter[str] = Counter()
    for result in trivy_results or []:
        for row in result.get("Vulnerabilities", []) or []:
            trivy_counts[str(row.get("Severity", "UNKNOWN")).upper()] += 1
        for row in result.get("Misconfigurations", []) or []:
            trivy_counts[str(row.get("Severity", "UNKNOWN")).upper()] += 1
    attack = raw.get("attack_regression", {})
    try:
        attack_failed = int(attack.get("tests_failed", 1)) if isinstance(attack, dict) else 1
        attack_passed = int(attack.get("tests_passed", 0)) if isinstance(attack, dict) else 0
        attack_total = int(attack.get("tests_total", 0)) if isinstance(attack, dict) else 0
    except (TypeError, ValueError):
        attack_failed, attack_passed, attack_total = 1, 0, 0
    attack_counts_complete = attack_total > 0 and attack_passed + attack_failed == attack_total
    issue_state = raw.get("issue_state", {})
    issue_items = (
        issue_state.get("issues", [])
        if isinstance(issue_state, dict) and isinstance(issue_state.get("issues"), list)
        else []
    )
    attack_issue_references = (
        attack.get("issue_references", [])
        if isinstance(attack, dict) and isinstance(attack.get("issue_references"), list)
        else []
    )
    attack_issue_refs = {
        int(item.get("issue")): item.get("title")
        for item in attack_issue_references
        if isinstance(item, dict) and str(item.get("issue", "")).isdigit()
    }
    issue_state_by_number = {
        int(item.get("issue")): item
        for item in issue_items
        if isinstance(item, dict) and str(item.get("issue", "")).isdigit()
    }
    issue_state_complete = (
        set(issue_state_by_number) == set(attack_issue_refs) == {65, 66}
        and all(
            issue_state_by_number[number].get("title") == title
            for number, title in attack_issue_refs.items()
        )
        and all(
            item.get("state") in {"open", "closed"}
            for item in issue_items
            if isinstance(item, dict)
        )
    )
    known_open_findings = [
        item for item in issue_items if isinstance(item, dict) and item.get("state") != "closed"
    ]
    resolved_findings = [
        item for item in issue_items if isinstance(item, dict) and item.get("state") == "closed"
    ]
    secret_output = (
        (out / REPORT_FILES["secret_scan"]).read_text(encoding="utf-8", errors="replace")
        if (out / REPORT_FILES["secret_scan"]).is_file()
        else ""
    )
    tracked_files = len(subprocess.check_output(["git", "ls-files"], text=True).splitlines())
    semgrep_raw = raw.get("semgrep", {})
    semgrep_path_data = semgrep_raw.get("paths", {}) if isinstance(semgrep_raw, dict) else {}
    semgrep_paths = (
        semgrep_path_data.get("scanned", []) if isinstance(semgrep_path_data, dict) else []
    )
    versions = raw.get("tool_versions", {}) if isinstance(raw.get("tool_versions"), dict) else {}
    ruleset = raw.get("semgrep_ruleset", {}) if isinstance(raw.get("semgrep_ruleset"), dict) else {}
    scanner_toolchain_verified = (
        all(
            EXPECTED_TOOL_VERSIONS[name] in str(versions.get(name, ""))
            for name in EXPECTED_TOOL_VERSIONS
        )
        and versions.get("semgrep_rules_repo") == EXPECTED_SEMGREP_RULES_REPO
        and versions.get("semgrep_rules_commit") == EXPECTED_SEMGREP_RULES_COMMIT
        and versions.get("semgrep_rules_directories") == EXPECTED_SEMGREP_RULE_DIRECTORIES
        and ruleset.get("repository") == EXPECTED_SEMGREP_RULES_REPO
        and ruleset.get("commit") == EXPECTED_SEMGREP_RULES_COMMIT
        and ruleset.get("directories") == EXPECTED_SEMGREP_RULE_DIRECTORIES
        and all(
            len(str(versions.get(name + "_binary_sha256", ""))) == 64
            and all(
                char in "0123456789abcdef"
                for char in str(versions.get(name + "_binary_sha256", ""))
            )
            for name in ("gitleaks", "trivy")
        )
        and all(
            versions.get(name) and not str(versions.get(name)).startswith("UNAVAILABLE:")
            for name in ("bandit", "pip_audit", "python3")
        )
    )

    codes = {name: exit_code(name) for name in EXIT_ENV}
    report_paths = {
        name: {
            "file": filename,
            "sha256": sha256(out / filename),
            "bytes": (out / filename).stat().st_size,
        }
        for name, filename in REPORT_FILES.items()
        if (out / filename).is_file()
    }
    execution_complete = (
        not missing
        and not parse_errors
        and not schema_errors
        and tracked_files > 0
        and bool(semgrep_paths)
        and attack_counts_complete
    )
    execution_complete = (
        execution_complete
        and all(
            codes[name] in {0, 1}
            for name in ("pip_audit", "bandit", "gitleaks", "attack_regression", "secret_scan")
        )
        and codes["semgrep"] == 0
        and codes["trivy"] == 0
    )

    blockers: list[str] = []
    if pip_vulnerabilities:
        blockers.append("dependency_vulnerabilities_found")
    if bandit_counts.get("HIGH", 0) or bandit_counts.get("MEDIUM", 0):
        blockers.append("bandit_medium_or_high_findings")
    if semgrep_security_error_rows:
        blockers.append("semgrep_security_error_findings")
    if gitleaks_rows:
        blockers.append("gitleaks_findings")
    if trivy_counts.get("CRITICAL", 0) or trivy_counts.get("HIGH", 0):
        blockers.append("trivy_high_or_critical_findings")
    if attack_failed:
        blockers.append("security_attack_regression_failed")
    if not attack_counts_complete:
        blockers.append("security_attack_regression_counts_incomplete")
    if not issue_state_complete:
        blockers.append("security_issue_state_incomplete")
    if not scanner_toolchain_verified:
        blockers.append("scanner_toolchain_or_ruleset_not_pinned")
    if known_open_findings:
        blockers.append("unresolved_security_issues_open")
    if codes["secret_scan"] != 0:
        blockers.append("repository_secret_scan_failed")
    if any(code not in {0, 1} for code in codes.values()):
        blockers.append("scanner_execution_error")
    if schema_errors:
        blockers.append("evidence_schema_invalid")
    if missing or parse_errors or schema_errors or not execution_complete:
        blockers.append("evidence_completeness_failed")

    review_items = {
        "bandit_low": bandit_counts.get("LOW", 0),
        "semgrep_warning": semgrep_counts.get("WARNING", 0),
        "semgrep_info": semgrep_counts.get("INFO", 0),
        "semgrep_nonsecurity_error": len(semgrep_nonsecurity_error_rows),
        "semgrep_subprocess_audit_review": len(semgrep_audit_review_rows),
        "semgrep_security_error_total": len(semgrep_security_error_rows),
        "semgrep_security_error_blocking": len(semgrep_blocking_security_error_rows),
        "trivy_medium": trivy_counts.get("MEDIUM", 0),
        "trivy_low": trivy_counts.get("LOW", 0),
        "tracked_files": tracked_files,
        "semgrep_scanned_paths": len(semgrep_paths),
    }
    completed_at = datetime.now(UTC).isoformat()
    scan_status = (
        "BLOCKED"
        if not execution_complete
        else ("REJECTED" if blockers else "READY_FOR_HUMAN_REVIEW")
    )
    scanner_pass = execution_complete and not blockers
    report = {
        "schema_version": 2,
        "gate": "Q10_OPEN_SOURCE_LAYERED_SECURITY",
        "source_sha": args.source_sha,
        "source_tree": args.source_tree,
        "release_subject_manifest_sha256": args.subject,
        "github_run_id": args.run_id,
        "completed_at": completed_at,
        "tools": versions,
        "tool_exit_codes": codes,
        "report_artifacts": report_paths,
        "coverage": {
            "tracked_files": tracked_files,
            "semgrep_scanned_paths": len(semgrep_paths),
            "required_reports": len(REPORT_FILES),
            "reports_present": len(report_paths),
            "missing_reports": missing,
            "invalid_reports": parse_errors,
            "invalid_schema_reports": schema_errors,
        },
        "findings": {
            "dependency_vulnerabilities": pip_vulnerabilities,
            "bandit_by_severity": bandit_counts,
            "semgrep_by_severity": semgrep_counts,
            "semgrep_security_error_total": len(semgrep_security_error_rows),
            "semgrep_security_error_blocking": len(semgrep_blocking_security_error_rows),
            "semgrep_subprocess_audit_review": len(semgrep_audit_review_rows),
            "semgrep_nonsecurity_error": len(semgrep_nonsecurity_error_rows),
            "gitleaks_findings": len(gitleaks_rows),
            "trivy_by_severity": dict(trivy_counts),
            "attack_regression_total": attack_total,
            "attack_regression_passed": attack_passed,
            "attack_regression_failed": attack_failed,
            "review_required": review_items,
            "blocking_reasons": blockers,
        },
        "secret_scan_summary": secret_output.strip()[:500],
        "known_open_findings": known_open_findings,
        "resolved_findings": resolved_findings,
        "issue_state_verified": issue_state_complete and not known_open_findings,
        "scanner_toolchain_verified": scanner_toolchain_verified,
        "scanner_execution_status": "PASS" if execution_complete else "BLOCKED",
        "security_assessment_status": scan_status,
        "open_source_security_scan": "PASS"
        if scanner_pass
        else ("FAIL" if execution_complete else "BLOCKED"),
        "security_review_status": "REQUIRED",
        "independent_review_status": "PENDING",
        "owner_approval_status": "PENDING",
        "production_promotion_allowed": False,
    }
    report_path = out / "q10-open-source-security-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_digest = sha256(report_path)
    evidence = {
        "schema_version": 6,
        "gate": "Q10",
        "source_sha": args.source_sha,
        "source_tree": args.source_tree,
        "subject_manifest_sha256": args.subject,
        "release_subject_manifest_sha256": args.subject,
        "github_run_id": args.run_id,
        "auditor": "CK-NEXUS Open-Source Layered Security Gate",
        "dependency_install": "uv sync --all-extras --dev --frozen",
        "vulnerabilities_found": pip_vulnerabilities,
        "component_result": "PASS"
        if codes["pip_audit"] == 0 and pip_vulnerabilities == 0
        else "FAIL",
        "open_source_security_scan": report["open_source_security_scan"],
        "security_scan_run_id": args.run_id,
        "security_report_sha256": report_digest,
        "security_scan_completed_at": completed_at,
        "security_scan_tools": [
            "Semgrep",
            "Bandit",
            "Gitleaks",
            "pip-audit",
            "Trivy",
            "CK-NEXUS security regression",
            "coverage/completeness",
        ],
        "security_scan_tool_versions": versions,
        "security_scan_exit_codes": codes,
        "bandit_findings_by_severity": bandit_counts,
        "semgrep_findings_by_severity": semgrep_counts,
        "semgrep_security_error_total": len(semgrep_security_error_rows),
        "semgrep_security_error_blocking": len(semgrep_blocking_security_error_rows),
        "semgrep_subprocess_audit_review": len(semgrep_audit_review_rows),
        "semgrep_nonsecurity_error": len(semgrep_nonsecurity_error_rows),
        "gitleaks_findings": len(gitleaks_rows),
        "trivy_findings_by_severity": dict(trivy_counts),
        "security_attack_regression_total": attack_total,
        "security_attack_regression_passed": attack_passed,
        "security_attack_regression_failed": attack_failed,
        "known_open_findings": report["known_open_findings"],
        "resolved_findings": report["resolved_findings"],
        "issue_state_verified": report["issue_state_verified"],
        "scanner_toolchain_verified": scanner_toolchain_verified,
        "scanner_execution_status": report["scanner_execution_status"],
        "security_assessment_status": scan_status,
        "security_review_status": "REQUIRED",
        "independent_review_status": "PENDING",
        "owner_approval_status": "PENDING",
        "gate_result": "NOT_VERIFIED",
        "production_promotion_allowed": False,
    }
    evidence_path = out / "Q10_DEPENDENCY_AUDIT.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "scan_status": scan_status,
        "scanner_toolchain_verified": scanner_toolchain_verified,
        "scanner_execution_status": report["scanner_execution_status"],
        "open_source_security_scan": evidence["open_source_security_scan"],
        "report_sha256": report_digest,
        "evidence_sha256": sha256(evidence_path),
        "blocking_reasons": blockers,
        "findings": report["findings"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if scanner_pass else (2 if not execution_complete else 1)


if __name__ == "__main__":
    sys.exit(main())
