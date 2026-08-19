#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

EXPECTED_SHA = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
EXPECTED_TREE = "0525195934f703a8becf8a39f6397b2411e0bb2e"
EXPECTED_SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(data: dict, key: str, expected: object | None = None) -> object:
    if key not in data:
        raise ValueError(f"missing required field: {key}")
    value = data[key]
    if expected is not None and value != expected:
        raise ValueError(f"{key} mismatch: {value!r} != {expected!r}")
    return value


def verify_timestamp(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("completion timestamp is empty")
    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("completion timestamp must include timezone")
    return text


def normalize(manifest: dict, report: Path) -> dict:
    scan_id = str(require(manifest, "codex_security_scan_id")).strip()
    if not scan_id:
        raise ValueError("codex_security_scan_id is empty")
    require(manifest, "codex_security_target_sha", EXPECTED_SHA)
    require(manifest, "codex_security_target_tree_sha", EXPECTED_TREE)
    require(
        manifest,
        "codex_security_release_subject_manifest_sha256",
        EXPECTED_SUBJECT,
    )
    require(manifest, "codex_security_deep_scan", "PASS")
    completed_at = verify_timestamp(require(manifest, "codex_security_completed_at"))
    report_digest = sha256_file(report)
    claimed_digest = str(require(manifest, "codex_security_report_sha256")).lower()
    if report_digest != claimed_digest:
        raise ValueError("report SHA-256 mismatch")
    return {
        "schema_version": 2,
        "gate": "Q10",
        "gate_result": "PASS",
        "codex_security_deep_scan": "PASS",
        "production_promotion_allowed": True,
        "codex_security_scan_id": scan_id,
        "codex_security_report_sha256": report_digest,
        "codex_security_completed_at": completed_at,
        "codex_security_target_sha": EXPECTED_SHA,
        "codex_security_target_tree_sha": EXPECTED_TREE,
        "codex_security_release_subject_manifest_sha256": EXPECTED_SUBJECT,
        "source_classification": "NATIVE_CODEX_SECURITY_SEALED_EVIDENCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and normalize genuine sealed Codex Security Q10 evidence"
    )
    parser.add_argument("--scan-manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = {"result": "BLOCKED", "errors": []}
    try:
        if not args.scan_manifest.is_file():
            raise ValueError("scan manifest not found")
        if not args.report.is_file():
            raise ValueError("report.md not found")
        result = normalize(load_json(args.scan_manifest), args.report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"result": "BLOCKED", "production_promotion_allowed": False, "errors": [str(exc)]}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("gate_result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
