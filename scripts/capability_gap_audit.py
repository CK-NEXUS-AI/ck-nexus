from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def any_path(patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        hits.extend(
            str(path.relative_to(ROOT))
            for path in ROOT.glob(pattern)
            if path.is_file()
        )
    return sorted(set(hits))


def file_contains(path: str, needles: list[str]) -> list[str]:
    candidate = ROOT / path
    if not candidate.exists() or not candidate.is_file():
        return []
    text = candidate.read_text(encoding="utf-8", errors="ignore").lower()
    return [needle for needle in needles if needle.lower() in text]


def record(
    capability: str,
    category: str,
    evidence: list[str],
    notes: str,
) -> dict[str, object]:
    return {
        "capability": capability,
        "category": category,
        "status": "FOUND" if evidence else "MISSING",
        "evidence": evidence,
        "notes": notes,
    }


def main() -> int:
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")

    checks: list[dict[str, object]] = []

    coverage = file_contains(
        "pyproject.toml",
        ["pytest-cov", "coverage.py", "[tool.coverage"],
    )
    coverage += any_path([".coveragerc", "coverage.xml", "htmlcov/index.html"])
    checks.append(
        record(
            "coverage_gate",
            "quality",
            coverage,
            "Automated test coverage measurement and gating.",
        )
    )

    e2e = any_path(["tests/e2e/**/*", "e2e/**/*", "playwright.config.*"])
    e2e += file_contains("pyproject.toml", ["playwright"])
    checks.append(
        record(
            "browser_e2e",
            "quality",
            e2e,
            "Browser-level end-to-end validation.",
        )
    )

    sbom = any_path(
        ["**/*sbom*", "**/*cyclonedx*", "**/*.spdx", "**/*.spdx.json"]
    )
    sbom += file_contains("pyproject.toml", ["cyclonedx", "sbom", "syft"])
    checks.append(
        record(
            "sbom_generation",
            "supply_chain",
            sbom,
            "Machine-readable software bill of materials.",
        )
    )

    perf = any_path(
        [
            "tests/performance/**/*",
            "tests/load/**/*",
            "benchmarks/**/*",
            "loadtests/**/*",
        ]
    )
    perf += file_contains("pyproject.toml", ["locust", "k6", "pytest-benchmark"])
    checks.append(
        record(
            "load_stress_soak",
            "quality",
            perf,
            "Performance, load, stress and soak harness.",
        )
    )

    agent_web = any_path(
        [
            "llms.txt",
            "**/llms.txt",
            "agents.json",
            "**/agents.json",
            "**/*agent-card*.json",
        ]
    )
    checks.append(
        record(
            "agent_readable_web_metadata",
            "interoperability",
            agent_web,
            "Agent-readable public metadata such as llms.txt or agent cards.",
        )
    )

    legal = any_path(
        [
            "PRIVACY*.md",
            "TERMS*.md",
            "AUP*.md",
            "docs/**/*PRIVACY*",
            "docs/**/*TERMS*",
            "docs/**/*AUP*",
        ]
    )
    checks.append(
        record(
            "commercial_legal_docs",
            "commercial",
            legal,
            "Privacy Policy, Terms and Acceptable Use policy artifacts.",
        )
    )

    incident = any_path(
        [
            "docs/**/*INCIDENT*",
            "docs/**/*DISASTER*",
            "docs/**/*DR*",
            "docs/**/*RUNBOOK*",
        ]
    )
    checks.append(
        record(
            "incident_dr_runbooks",
            "operations",
            incident,
            "Incident response and disaster recovery operator documentation.",
        )
    )

    missing = [
        item["capability"] for item in checks if item["status"] == "MISSING"
    ]
    report = {
        "schema_version": 1,
        "classification": "POST_P0_DEVELOPMENT_EVIDENCE_ONLY",
        "head_sha": head,
        "tree_sha": tree,
        "production_promotion_allowed": False,
        "q10_q11_q12_substitution_allowed": False,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "found": len(checks) - len(missing),
            "missing": len(missing),
            "missing_capabilities": missing,
        },
    }

    out = ROOT / "capability-gap-report.json"
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
