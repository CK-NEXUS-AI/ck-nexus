from __future__ import annotations

import json
from pathlib import Path

EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
FILES = {
    "Q10": "Q10_DEPENDENCY_AUDIT.json",
    "Q11": "Q11_OPENAI_LIVE.json",
    "Q12": "Q12_CGROUP_V2.json",
    "Q13": "Q13_POSTGRES_DR.json",
    "Q14": "Q14_OBSERVABILITY_ALERT.json",
    "Q15": "Q15_CLEAN_MACHINE.json",
    "Q16_IMAGE": "Q16_PRODUCTION_IMAGE.json",
    "Q16_LICENSES": "Q16_RUNTIME_LICENSE_SUMMARY.json",
}


def load(name: str) -> dict[str, object]:
    data = json.loads(Path("evidence", name).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(name)
    return data


def main() -> int:
    rows: dict[str, dict[str, object]] = {}
    failures: list[str] = []
    for gate, filename in FILES.items():
        try:
            row = load(filename)
            rows[gate] = row
        except Exception as exc:
            failures.append(f"{gate}: evidence unreadable ({type(exc).__name__})")
            continue
        if row.get("release_subject_manifest_sha256") != EXPECTED_SUBJECT:
            failures.append(f"{gate}: stale subject")

    q10 = rows.get("Q10", {})
    if not (
        q10.get("gate_result") == "PASS"
        and q10.get("codex_security_deep_scan") == "PASS"
        and q10.get("production_promotion_allowed") is True
        and q10.get("codex_security_scan_id")
        and q10.get("codex_security_report_sha256")
        and q10.get("codex_security_completed_at")
    ):
        failures.append("Q10: native deep-scan whole gate not PASS")

    q11 = rows.get("Q11", {})
    if not (
        q11.get("result") == "PASS"
        and q11.get("sentinel_observed") is True
        and q11.get("production_promotion_allowed") is True
        and q11.get("credential_exposed") is False
    ):
        failures.append("Q11: live provider not PASS")

    q12 = rows.get("Q12", {})
    if not (
        q12.get("result") == "PASS"
        and q12.get("actual_kernel_enforcement") is True
        and q12.get("production_promotion_allowed") is True
    ):
        failures.append("Q12: delegated cgroup v2 enforcement not PASS")

    q13 = rows.get("Q13", {})
    if q13.get("status") != "PASS" or q13.get("sentinel_round_trip") != "PASS":
        failures.append("Q13: PostgreSQL DR not PASS")

    q14 = rows.get("Q14", {})
    if q14.get("result") != "PASS" or q14.get("production_promotion_allowed") is not True:
        failures.append("Q14: observability not PASS")

    q15 = rows.get("Q15", {})
    if q15.get("result") not in {"PASS", "PASS_CANDIDATE"}:
        failures.append("Q15: clean-machine evidence unacceptable")

    q16_image = rows.get("Q16_IMAGE", {})
    if q16_image.get("result") != "PASS_CANDIDATE" or q16_image.get("production_promotion_allowed") is not True:
        failures.append("Q16 image: not PASS_CANDIDATE")

    q16_licenses = rows.get("Q16_LICENSES", {})
    if q16_licenses.get("result") != "PASS" or q16_licenses.get("unresolved_license_evidence"):
        failures.append("Q16 licenses: not PASS")

    report = {
        "schema_version": 1,
        "expected_release_subject": EXPECTED_SUBJECT,
        "result": "PASS" if not failures else "BLOCKED",
        "production_eligible_for_provenance": not failures,
        "failures": failures,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
