from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import q10_open_source_gate_report as gate_report

ISSUE_65_TITLE = "Security: prevent DNS-rebinding/TOCTOU SSRF in dynamic connector transport"
ISSUE_66_TITLE = "Security hardening: validate attachment content/magic before parser sandbox"


def _write_reports(output: Path, *, bandit_severity: str = "LOW") -> None:
    payloads = {
        "q10-pip-audit.json": {"dependencies": []},
        "q10-bandit.json": {"results": [{"issue_severity": bandit_severity}]},
        "q10-semgrep.json": {"results": [], "paths": {"scanned": ["scripts/example.py"]}},
        "q10-gitleaks.json": [],
        "q10-trivy.json": {"Results": []},
        "security-attack-regression.json": {
            "tests_total": 5,
            "tests_passed": 5,
            "tests_failed": 0,
            "issue_references": [
                {
                    "issue": 65,
                    "title": ISSUE_65_TITLE,
                },
                {
                    "issue": 66,
                    "title": ISSUE_66_TITLE,
                },
            ],
        },
        "q10-issue-state.json": {
            "issues": [
                {
                    "issue": 65,
                    "title": ISSUE_65_TITLE,
                    "state": "closed",
                },
                {
                    "issue": 66,
                    "title": ISSUE_66_TITLE,
                    "state": "closed",
                },
            ]
        },
        "q10-tool-versions.json": {
            "python3": "Python 3.12.10",
            "uv": "uv 0.13.7",
            "semgrep": "1.183.0",
            "gitleaks": "8.30.1",
            "trivy": "Version: 0.76.1",
            "bandit": "bandit 1.8.6",
            "pip_audit": "pip-audit 2.9.0",
            "semgrep_rules_repo": "https://github.com/semgrep/semgrep-rules",
            "semgrep_rules_commit": "16b9e6d45f10649f6a531ec4838ed9924372c3bc",
            "semgrep_rules_directories": [
                "python",
                "javascript",
                "typescript",
                "generic",
                "dockerfile",
                "yaml",
                "bash",
                "json",
            ],
            "gitleaks_binary_sha256": "a" * 64,
            "trivy_binary_sha256": "b" * 64,
        },
        "q10-semgrep-ruleset.json": {
            "repository": "https://github.com/semgrep/semgrep-rules",
            "commit": "16b9e6d45f10649f6a531ec4838ed9924372c3bc",
            "directories": [
                "python",
                "javascript",
                "typescript",
                "generic",
                "dockerfile",
                "yaml",
                "bash",
                "json",
            ],
        },
    }
    for name, value in payloads.items():
        (output / name).write_text(json.dumps(value), encoding="utf-8")
    (output / "q10-secret-scan.txt").write_text("SECRET SCAN: PASS\n", encoding="utf-8")


def _set_exit_codes(monkeypatch) -> None:
    for name in gate_report.EXIT_ENV.values():
        monkeypatch.setenv(name, "0")
    monkeypatch.setenv("Q10_BANDIT_RC", "1")


def test_report_keeps_q10_unverified_until_independent_review(tmp_path, monkeypatch) -> None:
    _write_reports(tmp_path)
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir",
            str(tmp_path),
            "--source-sha",
            "a" * 40,
            "--source-tree",
            "b" * 40,
            "--subject",
            "c" * 64,
            "--run-id",
            "12345",
        ],
    )

    assert gate_report.main() == 0
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    evidence = json.loads((tmp_path / "Q10_DEPENDENCY_AUDIT.json").read_text())
    assert report["security_assessment_status"] == "READY_FOR_HUMAN_REVIEW"
    assert evidence["open_source_security_scan"] == "PASS"
    assert evidence["scanner_toolchain_verified"] is True
    assert evidence["security_attack_regression_total"] == 5
    assert evidence["gate_result"] == "NOT_VERIFIED"
    assert evidence["independent_review_status"] == "PENDING"
    assert evidence["owner_approval_status"] == "PENDING"
    assert evidence["production_promotion_allowed"] is False


def test_report_rejects_medium_bandit_finding(tmp_path, monkeypatch) -> None:
    _write_reports(tmp_path, bandit_severity="MEDIUM")
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir",
            str(tmp_path),
            "--source-sha",
            "a" * 40,
            "--source-tree",
            "b" * 40,
            "--subject",
            "c" * 64,
            "--run-id",
            "12345",
        ],
    )

    assert gate_report.main() == 1
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    assert report["security_assessment_status"] == "REJECTED"
    assert "bandit_medium_or_high_findings" in report["findings"]["blocking_reasons"]


def test_report_rejects_open_security_issue_state(tmp_path, monkeypatch) -> None:
    _write_reports(tmp_path)
    issue_state = {
        "issues": [
            {
                "issue": 65,
                "title": ISSUE_65_TITLE,
                "state": "closed",
            },
            {
                "issue": 66,
                "title": ISSUE_66_TITLE,
                "state": "open",
            },
        ]
    }
    (tmp_path / "q10-issue-state.json").write_text(json.dumps(issue_state), encoding="utf-8")
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir",
            str(tmp_path),
            "--source-sha",
            "a" * 40,
            "--source-tree",
            "b" * 40,
            "--subject",
            "c" * 64,
            "--run-id",
            "12345",
        ],
    )

    assert gate_report.main() == 1
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    assert report["issue_state_verified"] is False
    assert report["known_open_findings"] == [
        {
            "issue": 66,
            "title": ISSUE_66_TITLE,
            "state": "open",
        }
    ]
    assert "unresolved_security_issues_open" in report["findings"]["blocking_reasons"]


def test_report_keeps_nonsecurity_semgrep_errors_in_review_queue(tmp_path, monkeypatch) -> None:
    _write_reports(tmp_path)
    semgrep = json.loads((tmp_path / "q10-semgrep.json").read_text())
    semgrep["results"] = [
        {
            "check_id": "python.lang.maintainability.useless-inner-function",
            "extra": {"severity": "ERROR", "metadata": {"category": "maintainability"}},
        }
    ]
    (tmp_path / "q10-semgrep.json").write_text(json.dumps(semgrep), encoding="utf-8")
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir",
            str(tmp_path),
            "--source-sha",
            "a" * 40,
            "--source-tree",
            "b" * 40,
            "--subject",
            "c" * 64,
            "--run-id",
            "12345",
        ],
    )

    assert gate_report.main() == 0
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    assert report["security_assessment_status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["findings"]["semgrep_nonsecurity_error"] == 1
    assert report["findings"]["semgrep_security_error_blocking"] == 0
    assert "semgrep_security_error_findings" not in report["findings"]["blocking_reasons"]


def test_report_blocks_unknown_or_security_semgrep_error_categories(tmp_path, monkeypatch) -> None:
    _write_reports(tmp_path)
    semgrep = json.loads((tmp_path / "q10-semgrep.json").read_text())
    semgrep["results"] = [
        {
            "check_id": "python.lang.security.injection.command",
            "extra": {"severity": "ERROR", "metadata": {"category": "security"}},
        },
        {
            "check_id": "python.lang.security.unknown-category",
            "extra": {"severity": "ERROR", "metadata": {}},
        },
    ]
    (tmp_path / "q10-semgrep.json").write_text(json.dumps(semgrep), encoding="utf-8")
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir",
            str(tmp_path),
            "--source-sha",
            "a" * 40,
            "--source-tree",
            "b" * 40,
            "--subject",
            "c" * 64,
            "--run-id",
            "12345",
        ],
    )

    assert gate_report.main() == 1
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    assert report["findings"]["semgrep_security_error_blocking"] == 2
    assert "semgrep_security_error_findings" in report["findings"]["blocking_reasons"]


def test_report_blocks_security_subprocess_audit_errors_until_resolved(
    tmp_path, monkeypatch
) -> None:
    _write_reports(tmp_path)
    semgrep = json.loads((tmp_path / "q10-semgrep.json").read_text())
    semgrep["results"] = [
        {
            "check_id": "python.lang.security.audit.dangerous-subprocess-use-audit",
            "extra": {"severity": "ERROR", "metadata": {"category": "security"}},
        },
        {
            "check_id": "python.lang.security.audit.dangerous-asyncio-create-exec-audit",
            "extra": {"severity": "ERROR", "metadata": {"category": "security"}},
        },
    ]
    (tmp_path / "q10-semgrep.json").write_text(json.dumps(semgrep), encoding="utf-8")
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir",
            str(tmp_path),
            "--source-sha",
            "a" * 40,
            "--source-tree",
            "b" * 40,
            "--subject",
            "c" * 64,
            "--run-id",
            "12345",
        ],
    )

    assert gate_report.main() == 1
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    assert report["security_assessment_status"] == "REJECTED"
    assert report["findings"]["semgrep_subprocess_audit_review"] == 2
    assert report["findings"]["semgrep_security_error_blocking"] == 2
    assert "semgrep_security_error_findings" in report["findings"]["blocking_reasons"]
    assert report["independent_review_status"] == "PENDING"
    assert report["owner_approval_status"] == "PENDING"
    assert report["production_promotion_allowed"] is False


def test_report_rejects_structurally_incomplete_scanner_json(tmp_path, monkeypatch) -> None:
    _write_reports(tmp_path)
    (tmp_path / "q10-semgrep.json").write_text(json.dumps({"results": []}), encoding="utf-8")
    _set_exit_codes(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "q10_open_source_gate_report.py",
            "--output-dir", str(tmp_path),
            "--source-sha", "a" * 40,
            "--source-tree", "b" * 40,
            "--subject", "c" * 64,
            "--run-id", "12345",
        ],
    )
    assert gate_report.main() == 2
    report = json.loads((tmp_path / "q10-open-source-security-report.json").read_text())
    assert report["scanner_execution_status"] == "BLOCKED"
    assert "semgrep" in report["coverage"]["invalid_schema_reports"]
    assert "evidence_schema_invalid" in report["findings"]["blocking_reasons"]
