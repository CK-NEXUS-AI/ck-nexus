from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def _junit_summary(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise ValueError("junit.xml does not contain a testsuite")
    return {
        "tests": int(suite.attrib.get("tests", 0)),
        "failures": int(suite.attrib.get("failures", 0)),
        "errors": int(suite.attrib.get("errors", 0)),
        "skipped": int(suite.attrib.get("skipped", 0)),
    }


def _coverage_percent(path: Path) -> float:
    root = ET.parse(path).getroot()
    return round(float(root.attrib.get("line-rate", 0.0)) * 100.0, 2)


def main() -> None:
    junit = Path("junit.xml")
    coverage = Path("coverage.xml")
    if not junit.exists() or not coverage.exists():
        raise SystemExit("required test evidence inputs are missing")

    summary = _junit_summary(junit)
    coverage_percent = _coverage_percent(coverage)
    passed = summary["failures"] == 0 and summary["errors"] == 0 and coverage_percent >= 80.0
    report = {
        "schema_version": 1,
        "suite": "CK-NEXUS Test Standards V1",
        "result": "PASS" if passed else "FAIL",
        "provider_mode": "mock",
        "coverage_scope": "post-p0 governed contracts",
        "coverage_percent": coverage_percent,
        "coverage_gate_percent": 80.0,
        "tests": summary,
        "generated_unix": int(time.time()),
        "production_evidence": False,
    }
    Path("test_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not passed:
        raise SystemExit("test evidence report failed policy")


if __name__ == "__main__":
    main()
