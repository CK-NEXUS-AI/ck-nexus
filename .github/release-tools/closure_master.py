#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXPECTED = {
    "repository": "spinlnw10-art/ck-nexus",
    "closure_head": "a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53",
    "runtime_source": "39f5c1adb9d761ab418cf088ff1f051b1ca731d1",
    "runtime_source_tree": "0525195934f703a8becf8a39f6397b2411e0bb2e",
    "runtime_subject": "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52",
}


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require(obj: dict, key: str, expected=None) -> None:
    if key not in obj:
        raise ValueError(f"missing required field: {key}")
    if expected is not None and obj[key] != expected:
        raise ValueError(f"{key} mismatch: {obj[key]!r} != {expected!r}")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_q10(path: str, report: str | None) -> dict:
    e = load(path)
    for k in ("codex_security_scan_id", "codex_security_report_sha256", "codex_security_completed_at"):
        require(e, k)
        if not str(e[k]).strip():
            raise ValueError(f"empty Q10 field: {k}")
    require(e, "codex_security_target_sha", EXPECTED["runtime_source"])
    require(e, "codex_security_target_tree_sha", EXPECTED["runtime_source_tree"])
    require(e, "codex_security_release_subject_manifest_sha256", EXPECTED["runtime_subject"])
    require(e, "gate_result", "PASS")
    require(e, "codex_security_deep_scan", "PASS")
    if report:
        actual = sha256_file(report)
        if actual != e["codex_security_report_sha256"]:
            raise ValueError("Q10 report SHA-256 mismatch")
    return {"gate": "Q10", "result": "PASS"}


def verify_q11(path: str) -> dict:
    e = load(path)
    require(e, "result", "PASS")
    require(e, "credential_configured", True)
    require(e, "credential_exposed", False)
    require(e, "sentinel_observed", True)
    require(e, "release_subject", EXPECTED["runtime_subject"])
    for k in ("workflow_run_id", "artifact_id", "artifact_digest"):
        require(e, k)
    return {"gate": "Q11", "result": "PASS"}


def verify_q12(path: str) -> dict:
    e = load(path)
    require(e, "result", "PASS")
    require(e, "release_subject", EXPECTED["runtime_subject"])
    require(e, "non_root", True)
    require(e, "delegated", True)
    require(e, "cpu_max", "20000 100000")
    require(e, "memory_max", "67108864")
    require(e, "pids_max", "16")
    require(e, "escape_attempt_blocked", True)
    for k in ("workflow_run_id", "artifact_id", "artifact_digest"):
        require(e, k)
    return {"gate": "Q12", "result": "PASS"}


def main() -> int:
    p = argparse.ArgumentParser(description="CK-NEXUS fail-closed production closure verifier")
    p.add_argument("--q10")
    p.add_argument("--q10-report")
    p.add_argument("--q11")
    p.add_argument("--q12")
    p.add_argument("--provenance")
    p.add_argument("--package")
    p.add_argument("--output", required=True)
    a = p.parse_args()

    result = {"status": "NO-GO", "expected": EXPECTED, "checks": [], "errors": []}
    try:
        if not (a.q10 and a.q11 and a.q12 and a.provenance):
            raise ValueError("Q10, Q11, Q12 and provenance evidence are all mandatory")
        result["checks"].append(verify_q10(a.q10, a.q10_report))
        result["checks"].append(verify_q11(a.q11))
        result["checks"].append(verify_q12(a.q12))
        prov = load(a.provenance)
        require(prov, "result", "PASS")
        require(prov, "expected_subject", EXPECTED["runtime_subject"])
        if int(prov.get("records_reconciled", 0)) < 8:
            raise ValueError("provenance requires at least 8 reconciled records")
        result["checks"].append({"gate": "PROVENANCE", "result": "PASS"})
        if a.package:
            if not Path(a.package).is_file():
                raise ValueError("production package missing")
            result["package_sha256"] = sha256_file(a.package)
            result["checks"].append({"gate": "FINAL_PACKAGE", "result": "PASS"})
            result["status"] = "ELIGIBLE_FOR_REVIEW_NOT_MERGED"
        else:
            result["status"] = "GATES_PASS_PACKAGE_NOT_PROVIDED"
    except Exception as exc:
        result["errors"].append(str(exc))

    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != "NO-GO" else 2


if __name__ == "__main__":
    sys.exit(main())
