#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_METRICS = [
    "alert_status",
    "reliability_rating",
    "security_rating",
    "sqale_rating",
    "coverage",
    "duplicated_lines_density",
    "bugs",
    "vulnerabilities",
    "code_smells",
    "security_hotspots",
    "new_reliability_rating",
    "new_security_rating",
    "new_maintainability_rating",
    "new_coverage",
    "new_duplicated_lines_density",
]

SEVERITY_ORDER = {"BLOCKER": 0, "CRITICAL": 1, "MAJOR": 2, "MINOR": 3, "INFO": 4}


def request_json(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "ck-nexus-sonar-reporter/1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def api(base: str, path: str, params: dict[str, str], token: str) -> dict:
    return request_json(
        f"{base.rstrip('/')}{path}?{urllib.parse.urlencode(params)}",
        token,
    )


def measure_map(payload: dict) -> dict[str, str]:
    component = payload.get("component") or {}
    result: dict[str, str] = {}
    for item in component.get("measures") or []:
        metric = item.get("metric")
        if not metric:
            continue
        if "value" in item:
            result[metric] = str(item["value"])
        periods = item.get("periods") or []
        if periods:
            result[f"{metric}:period"] = str(periods[0].get("value", ""))
    return result


def issue_priority(issue: dict) -> tuple[int, str]:
    severity = str(issue.get("severity", "INFO")).upper()
    issue_type = str(issue.get("type", "")).upper()
    if issue_type in {"VULNERABILITY", "SECURITY_HOTSPOT"} and severity == "BLOCKER":
        label = "P0_SECURITY_BLOCKER"
    elif issue_type in {"VULNERABILITY", "SECURITY_HOTSPOT"} and severity == "CRITICAL":
        label = "P0_SECURITY_CRITICAL"
    elif severity in {"BLOCKER", "CRITICAL"}:
        label = "P1_RELIABILITY_CRITICAL"
    elif severity == "MAJOR":
        label = "P2_MAJOR"
    else:
        label = "P3_NORMAL"
    return SEVERITY_ORDER.get(severity, 99), label


def evaluate(measures: dict[str, str], issues: list[dict]) -> dict:
    def f(name: str) -> float | None:
        raw = measures.get(name)
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    severe = Counter(str(i.get("severity", "UNKNOWN")).upper() for i in issues)
    checks = {
        "overall_security_rating_B_or_better": (f("security_rating") or 99) <= 2,
        "overall_reliability_rating_B_or_better": (f("reliability_rating") or 99) <= 2,
        "overall_maintainability_rating_B_or_better": (f("sqale_rating") or 99) <= 2,
        "no_blocker_issues": severe["BLOCKER"] == 0,
        "no_critical_issues": severe["CRITICAL"] == 0,
    }
    if f("new_security_rating") is not None:
        checks["new_security_rating_A"] = f("new_security_rating") <= 1
    if f("new_reliability_rating") is not None:
        checks["new_reliability_rating_A"] = f("new_reliability_rating") <= 1
    if f("new_maintainability_rating") is not None:
        checks["new_maintainability_rating_A"] = f("new_maintainability_rating") <= 1
    if f("new_coverage") is not None:
        checks["new_coverage_80_percent"] = f("new_coverage") >= 80
    if f("new_duplicated_lines_density") is not None:
        checks["new_duplication_3_percent_max"] = f("new_duplicated_lines_density") <= 3
    return {
        "internal_policy_result": "PASS" if checks and all(checks.values()) else "FAIL",
        "checks": checks,
    }


def md_table(rows: list[tuple[str, str]]) -> str:
    lines = ["| Metric | Value |", "|---|---:|"]
    lines.extend(f"| {k} | {v} |" for k, v in rows)
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project-key", required=True)
    p.add_argument("--host-url", default="https://sonarcloud.io")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--commit", default=os.getenv("GITHUB_SHA", "unknown"))
    args = p.parse_args()

    token = os.getenv("SONAR_TOKEN")
    if not token:
        print("SONAR_TOKEN is required via environment only", file=sys.stderr)
        return 10

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()

    gate = api(
        args.host_url,
        "/api/qualitygates/project_status",
        {"projectKey": args.project_key},
        token,
    )
    measures_payload = api(
        args.host_url,
        "/api/measures/component",
        {"component": args.project_key, "metricKeys": ",".join(DEFAULT_METRICS)},
        token,
    )
    issues_payload = api(
        args.host_url,
        "/api/issues/search",
        {"componentKeys": args.project_key, "ps": "500", "resolved": "false"},
        token,
    )

    measures = measure_map(measures_payload)
    issues = issues_payload.get("issues") or []
    ordered = sorted(issues, key=issue_priority)
    severity_counts = Counter(str(i.get("severity", "UNKNOWN")).upper() for i in issues)
    type_counts = Counter(str(i.get("type", "UNKNOWN")).upper() for i in issues)
    policy = evaluate(measures, issues)

    raw = {
        "schema_version": 1,
        "project_key": args.project_key,
        "commit": args.commit,
        "observed_at": now,
        "sonar_quality_gate": (gate.get("projectStatus") or {}).get("status", "UNKNOWN"),
        "measures": measures,
        "severity_counts": dict(severity_counts),
        "type_counts": dict(type_counts),
        "internal_policy": policy,
        "issues": ordered,
        "claims_boundary": (
            "Automated SonarQube Cloud analysis evidence only; "
            "not independent audit or certification."
        ),
    }
    (out / "sonar-analysis.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    metric_rows = sorted(measures.items())
    top_issues = ordered[:30]
    dev_lines = [
        "# CK-NEXUS Sonar Developer Report",
        "",
        f"- Project: `{args.project_key}`",
        f"- Commit: `{args.commit}`",
        f"- Observed: {now}",
        f"- Sonar Quality Gate: **{raw['sonar_quality_gate']}**",
        f"- CK-NEXUS internal policy: **{policy['internal_policy_result']}**",
        "",
        "## Measures",
        "",
        md_table(metric_rows),
        "",
        "## Priority findings",
        "",
    ]
    if not top_issues:
        dev_lines.append("No open issues returned by the queried endpoint.")
    for issue in top_issues:
        _, priority = issue_priority(issue)
        component = str(issue.get("component", ""))
        line = issue.get("line")
        where = f"{component}:{line}" if line else component
        dev_lines.append(
            f"- **{priority} / {issue.get('severity','UNKNOWN')} / "
            f"{issue.get('type','UNKNOWN')}** — {issue.get('message','')} "
            f"(`{where}`, rule `{issue.get('rule','')}`)"
        )
    dev_lines += [
        "",
        "## Boundary",
        "",
        "This report is automated tool evidence. It does not constitute an ISO/CISQ "
        "certificate, an independent security assessment, Q10 verification, or Production approval.",
    ]
    (out / "DEVELOPER_REPORT.md").write_text("\n".join(dev_lines) + "\n", encoding="utf-8")

    exec_lines = [
        "# CK-NEXUS Sonar Executive / Buyer Summary",
        "",
        f"Project: **{args.project_key}**  ",
        f"Commit: `{args.commit}`  ",
        f"Sonar Quality Gate: **{raw['sonar_quality_gate']}**  ",
        f"Internal quality policy: **{policy['internal_policy_result']}**",
        "",
        "## Current issue profile",
        "",
        f"- Blocker: {severity_counts['BLOCKER']}",
        f"- Critical: {severity_counts['CRITICAL']}",
        f"- Major: {severity_counts['MAJOR']}",
        f"- Security vulnerabilities: {type_counts['VULNERABILITY']}",
        f"- Reliability bugs: {type_counts['BUG']}",
        f"- Maintainability code smells: {type_counts['CODE_SMELL']}",
        "",
        "## Interpretation",
        "",
        "This is an automated SonarQube Cloud code-quality/security analysis. "
        "It is suitable as engineering and due-diligence evidence, but it does not replace "
        "an independent professional audit, formal certification, Q10 closure, or owner approval.",
    ]
    (out / "EXECUTIVE_BUYER_SUMMARY.md").write_text(
        "\n".join(exec_lines) + "\n",
        encoding="utf-8",
    )

    return 0 if (
        raw["sonar_quality_gate"] == "OK"
        and policy["internal_policy_result"] == "PASS"
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
