#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXPECTED = {
    "repository": "spinlnw10-art/ck-nexus",
    "runtime_source": "39f5c1adb9d761ab418cf088ff1f051b1ca731d1",
    "runtime_source_tree": "0525195934f703a8becf8a39f6397b2411e0bb2e",
    "runtime_subject": "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52",
}
EXPECTED_CGROUP = {
    "cpu.max": "20000 100000",
    "memory.max": "67108864",
    "pids.max": "16",
    "pid_attached": True,
}


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def require(obj: dict, key: str, expected: object | None = None) -> object:
    if key not in obj:
        raise ValueError(f"missing required field: {key}")
    value = obj[key]
    if expected is not None and value != expected:
        raise ValueError(f"{key} mismatch: {value!r} != {expected!r}")
    return value


def require_artifact_provenance(evidence: dict) -> None:
    run_id = require(evidence, "github_run_id")
    artifact_id = require(evidence, "artifact_id")
    digest = require(evidence, "artifact_digest")
    if not isinstance(run_id, int) or not isinstance(artifact_id, int):
        raise ValueError("github_run_id and artifact_id must be integers")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise ValueError("artifact_digest must be a sha256: digest")


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_q10(path: str, report: str | None) -> dict:
    evidence = load(path)
    require(evidence, "gate", "Q10")
    require(evidence, "source_sha", EXPECTED["runtime_source"])
    require(evidence, "source_tree", EXPECTED["runtime_source_tree"])
    require(
        evidence,
        "release_subject_manifest_sha256",
        EXPECTED["runtime_subject"],
    )
    require(evidence, "component_result", "PASS")
    require(evidence, "vulnerabilities_found", 0)
    require(evidence, "gate_result", "PASS")
    require(evidence, "codex_security_deep_scan", "PASS")
    require(evidence, "production_promotion_allowed", True)
    require_artifact_provenance(evidence)
    for key in (
        "codex_security_scan_id",
        "codex_security_report_sha256",
        "codex_security_completed_at",
    ):
        value = str(require(evidence, key)).strip()
        if not value:
            raise ValueError(f"empty Q10 field: {key}")
    require(evidence, "codex_security_target_sha", EXPECTED["runtime_source"])
    require(
        evidence,
        "codex_security_target_tree_sha",
        EXPECTED["runtime_source_tree"],
    )
    require(
        evidence,
        "codex_security_release_subject_manifest_sha256",
        EXPECTED["runtime_subject"],
    )
    if report and sha256_file(report) != evidence["codex_security_report_sha256"]:
        raise ValueError("Q10 report SHA-256 mismatch")
    return {"gate": "Q10", "result": "PASS"}


def verify_q11(path: str) -> dict:
    evidence = load(path)
    require(evidence, "gate", "Q11")
    require(evidence, "source_sha", EXPECTED["runtime_source"])
    require(evidence, "source_tree", EXPECTED["runtime_source_tree"])
    require(
        evidence,
        "release_subject_manifest_sha256",
        EXPECTED["runtime_subject"],
    )
    require(evidence, "result", "PASS")
    require(evidence, "production_promotion_allowed", True)
    require(evidence, "credential_configured", True)
    require(evidence, "credential_exposed", False)
    require(evidence, "sentinel_observed", True)
    require(evidence, "p0_ai_001_exit_code", 0)
    require_artifact_provenance(evidence)
    return {"gate": "Q11", "result": "PASS"}


def verify_q12(path: str) -> dict:
    evidence = load(path)
    require(evidence, "gate", "Q12")
    require(evidence, "source_sha", EXPECTED["runtime_source"])
    require(evidence, "source_tree", EXPECTED["runtime_source_tree"])
    require(
        evidence,
        "release_subject_manifest_sha256",
        EXPECTED["runtime_subject"],
    )
    require(evidence, "result", "PASS")
    require(evidence, "production_promotion_allowed", True)
    require(evidence, "delegation_ready", True)
    require(evidence, "actual_kernel_enforcement", True)
    require(
        evidence,
        "environment_class",
        "self-hosted-linux-delegated-cgroup-v2",
    )
    raw = require(evidence, "raw")
    if not isinstance(raw, dict):
        raise ValueError("Q12 raw evidence must be an object")
    require(raw, "status", "PASS")
    observed = require(raw, "observed")
    if observed != EXPECTED_CGROUP:
        raise ValueError("Q12 observed cgroup enforcement mismatch")
    require_artifact_provenance(evidence)
    return {"gate": "Q12", "result": "PASS"}


def verify_provenance(path: str) -> dict:
    provenance = load(path)
    require(provenance, "result", "PASS")
    require(
        provenance,
        "expected_release_subject",
        EXPECTED["runtime_subject"],
    )
    require(provenance, "evidence_files_checked", 8)
    failures = require(provenance, "provenance_failures", [])
    if failures:
        raise ValueError("provenance report contains failures")
    rows = provenance.get("evidence", [])
    if len(rows) != 8 or any(row.get("provenance") != "PASS" for row in rows):
        raise ValueError("provenance requires 8/8 PASS evidence rows")
    return {"gate": "PROVENANCE", "result": "PASS"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CK-NEXUS fail-closed production closure verifier"
    )
    parser.add_argument("--q10")
    parser.add_argument("--q10-report")
    parser.add_argument("--q11")
    parser.add_argument("--q12")
    parser.add_argument("--provenance")
    parser.add_argument("--package")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = {"status": "NO-GO", "expected": EXPECTED, "checks": [], "errors": []}
    try:
        if not (args.q10 and args.q11 and args.q12 and args.provenance):
            raise ValueError("Q10, Q11, Q12 and provenance evidence are mandatory")
        result["checks"].append(verify_q10(args.q10, args.q10_report))
        result["checks"].append(verify_q11(args.q11))
        result["checks"].append(verify_q12(args.q12))
        result["checks"].append(verify_provenance(args.provenance))
        if args.package:
            if not Path(args.package).is_file():
                raise ValueError("production package missing")
            result["package_sha256"] = sha256_file(args.package)
            result["checks"].append({"gate": "FINAL_PACKAGE", "result": "PASS"})
            result["status"] = "ELIGIBLE_FOR_REVIEW_NOT_MERGED"
        else:
            result["status"] = "GATES_PASS_PACKAGE_NOT_PROVIDED"
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["errors"].append(str(exc))

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != "NO-GO" else 2


if __name__ == "__main__":
    sys.exit(main())
