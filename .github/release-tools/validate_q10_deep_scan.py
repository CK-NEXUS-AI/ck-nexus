from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_REPOSITORY = "spinlnw10-art/ck-nexus"
EXPECTED_SOURCE_SHA = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
EXPECTED_SOURCE_TREE = "0525195934f703a8becf8a39f6397b2411e0bb2e"
EXPECTED_RELEASE_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
EXPECTED_APPLICATION_SUBJECT = "dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec"
REQUIRED_PHASES = (
    "preflight",
    "repeated_discovery",
    "canonical_validation",
    "attack_path_analysis",
    "canonical_draft",
    "completion_with_generated_report",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate completed native Codex Security Deep Scan evidence for CK-NEXUS Q10"
    )
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", default="q10-deep-scan-validated.json", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    try:
        meta = load_json(args.metadata)
    except Exception as exc:
        print(f"Q10 validation failed: metadata unreadable ({type(exc).__name__})", file=sys.stderr)
        return 2

    if not args.report.is_file():
        failures.append("generated_report_missing")
        report_sha = None
    else:
        report_sha = sha256_file(args.report)

    required_exact = {
        "repository": EXPECTED_REPOSITORY,
        "target_sha": EXPECTED_SOURCE_SHA,
        "target_tree_sha": EXPECTED_SOURCE_TREE,
        "release_subject_manifest_sha256": EXPECTED_RELEASE_SUBJECT,
        "application_subject_manifest_sha256": EXPECTED_APPLICATION_SUBJECT,
        "target_scope": ".",
        "scan_mode": "deep",
        "codex_security_deep_scan": "PASS",
        "gate_result": "PASS",
        "production_promotion_allowed": True,
    }
    for key, expected in required_exact.items():
        if meta.get(key) != expected:
            failures.append(f"{key}_mismatch")

    for key in ("codex_security_scan_id", "codex_security_completed_at"):
        value = meta.get(key)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{key}_missing")

    declared_sha = meta.get("codex_security_report_sha256")
    if not isinstance(declared_sha, str) or len(declared_sha) != 64:
        failures.append("codex_security_report_sha256_invalid")
    elif report_sha is not None and declared_sha.lower() != report_sha:
        failures.append("codex_security_report_sha256_mismatch")

    terminal = meta.get("terminal_phases")
    if not isinstance(terminal, dict):
        failures.append("terminal_phases_missing")
    else:
        for phase in REQUIRED_PHASES:
            if terminal.get(phase) != "PASS":
                failures.append(f"terminal_phase_not_pass:{phase}")

    coverage = meta.get("coverage")
    if coverage not in {"complete", "partial"}:
        failures.append("coverage_missing")
    if coverage == "partial" and meta.get("production_promotion_allowed") is True:
        failures.append("partial_coverage_cannot_promote")

    validated = {
        "schema_version": 1,
        "gate": "Q10",
        "validator": "validate_q10_deep_scan.py",
        "source_sha": EXPECTED_SOURCE_SHA,
        "source_tree": EXPECTED_SOURCE_TREE,
        "release_subject_manifest_sha256": EXPECTED_RELEASE_SUBJECT,
        "report_sha256_observed": report_sha,
        "scan_id": meta.get("codex_security_scan_id"),
        "completed_at": meta.get("codex_security_completed_at"),
        "coverage": coverage,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "production_promotion_allowed": not failures,
    }
    args.output.write_text(json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(validated, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
