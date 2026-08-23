import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".github/release-tools/validate_q10_native_deep_scan_receipt.py"
CONTRACT = ROOT / ".github/release-tools/q10_native_deep_scan_contract_v2.json"

spec = importlib.util.spec_from_file_location("q10_receipt_validator", TOOL)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def valid_receipt() -> dict[str, object]:
    cfg = contract()
    digest = "sha256:" + "a" * 64
    return {
        "gate": "Q10",
        "repository": cfg["repository"],
        "source_sha": cfg["source_sha"],
        "source_tree": cfg["source_tree"],
        "release_subject_manifest_sha256": cfg["release_subject_manifest_sha256"],
        "scan_mode": "deep",
        "codex_security_scan_id": "scan-001",
        "codex_security_report_sha256": digest,
        "codex_security_manifest_sha256": digest,
        "codex_security_findings_sha256": digest,
        "codex_security_coverage_sha256": digest,
        "codex_security_completed_at": "2026-08-23T10:00:00Z",
        **cfg["pass_invariants"],
    }


def test_q10_receipt_accepts_exact_complete_native_scan() -> None:
    validator.validate_receipt(valid_receipt(), contract())


def test_q10_receipt_rejects_subject_drift() -> None:
    receipt = valid_receipt()
    receipt["subject_changed"] = True
    with pytest.raises(ValueError, match="subject_changed"):
        validator.validate_receipt(receipt, contract())


def test_q10_receipt_rejects_wrong_source() -> None:
    receipt = valid_receipt()
    receipt["source_sha"] = "0" * 40
    with pytest.raises(ValueError, match="source_sha mismatch"):
        validator.validate_receipt(receipt, contract())


def test_q10_receipt_rejects_partial_coverage() -> None:
    receipt = valid_receipt()
    receipt["coverage_complete"] = False
    with pytest.raises(ValueError, match="coverage_complete"):
        validator.validate_receipt(receipt, contract())


def test_q10_receipt_rejects_invalid_report_digest() -> None:
    receipt = valid_receipt()
    receipt["codex_security_report_sha256"] = "not-a-digest"
    with pytest.raises(ValueError, match="codex_security_report_sha256"):
        validator.validate_receipt(receipt, contract())
