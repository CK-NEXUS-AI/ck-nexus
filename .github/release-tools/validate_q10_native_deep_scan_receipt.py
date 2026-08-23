from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "q10_native_deep_scan_contract_v2.json"
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _require_digest(value: object, field: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be a SHA-256 digest")


def _require_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")


def validate_receipt(receipt: dict[str, Any], contract: dict[str, Any]) -> None:
    expected = {
        "gate": "Q10",
        "repository": contract["repository"],
        "source_sha": contract["source_sha"],
        "source_tree": contract["source_tree"],
        "release_subject_manifest_sha256": contract["release_subject_manifest_sha256"],
        "scan_mode": "deep",
    }
    for field, expected_value in expected.items():
        if receipt.get(field) != expected_value:
            raise ValueError(f"{field} mismatch")

    scan_id = receipt.get("codex_security_scan_id")
    if not isinstance(scan_id, str) or not scan_id.strip():
        raise ValueError("codex_security_scan_id is required")

    for field in (
        "codex_security_report_sha256",
        "codex_security_manifest_sha256",
        "codex_security_findings_sha256",
        "codex_security_coverage_sha256",
    ):
        _require_digest(receipt.get(field), field)
    _require_timestamp(receipt.get("codex_security_completed_at"), "codex_security_completed_at")

    for field, expected_value in contract["pass_invariants"].items():
        if receipt.get(field) != expected_value:
            raise ValueError(f"Q10 pass invariant failed: {field}")


def _self_test(contract: dict[str, Any]) -> None:
    digest = "sha256:" + "a" * 64
    receipt: dict[str, Any] = {
        "gate": "Q10",
        "repository": contract["repository"],
        "source_sha": contract["source_sha"],
        "source_tree": contract["source_tree"],
        "release_subject_manifest_sha256": contract["release_subject_manifest_sha256"],
        "scan_mode": "deep",
        "codex_security_scan_id": "scan-self-test",
        "codex_security_report_sha256": digest,
        "codex_security_manifest_sha256": digest,
        "codex_security_findings_sha256": digest,
        "codex_security_coverage_sha256": digest,
        "codex_security_completed_at": "2026-08-23T00:00:00Z",
        **contract["pass_invariants"],
    }
    validate_receipt(receipt, contract)
    broken = dict(receipt)
    broken["subject_changed"] = True
    try:
        validate_receipt(broken, contract)
    except ValueError:
        return
    raise AssertionError("self-test failed to reject changed subject")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CK-NEXUS Q10 native deep-scan receipt")
    parser.add_argument("receipt", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    contract = _load(CONTRACT_PATH)
    if args.self_test:
        _self_test(contract)
        print("Q10_NATIVE_DEEP_SCAN_RECEIPT_VALIDATOR=PASS")
        return 0
    if args.receipt is None:
        parser.error("receipt path is required unless --self-test is used")
    validate_receipt(_load(args.receipt), contract)
    print("Q10_NATIVE_DEEP_SCAN_RECEIPT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
