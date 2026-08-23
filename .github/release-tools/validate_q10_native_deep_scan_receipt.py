from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "q10_native_deep_scan_contract_v2.json"
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
_ARTIFACT_FIELDS = {
    "codex_security_report_sha256": "codex_security_report_artifact",
    "codex_security_manifest_sha256": "codex_security_manifest_artifact",
    "codex_security_findings_sha256": "codex_security_findings_artifact",
    "codex_security_coverage_sha256": "codex_security_coverage_artifact",
}


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _normalize_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return value.removeprefix("sha256:")


def _require_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")


def _artifact_path(artifact_root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{field} must be a safe relative path")
    root = artifact_root.resolve()
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"{field} escapes artifact root")
    if not resolved.is_file():
        raise ValueError(f"{field} artifact is missing")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_receipt(
    receipt: dict[str, Any], contract: dict[str, Any], artifact_root: Path
) -> None:
    expected = {
        "gate": "Q10",
        "repository": contract["repository"],
        "source_sha": contract["source_sha"],
        "source_tree": contract["source_tree"],
        "release_subject_manifest_sha256": contract["release_subject_manifest_sha256"],
        "application_subject_manifest_sha256": contract["application_subject_manifest_sha256"],
        "scan_mode": "deep",
    }
    for field, expected_value in expected.items():
        if receipt.get(field) != expected_value:
            raise ValueError(f"{field} mismatch")

    scan_id = receipt.get("codex_security_scan_id")
    if not isinstance(scan_id, str) or not scan_id.strip():
        raise ValueError("codex_security_scan_id is required")

    for digest_field, artifact_field in _ARTIFACT_FIELDS.items():
        expected_digest = _normalize_digest(receipt.get(digest_field), digest_field)
        artifact_path = _artifact_path(artifact_root, receipt.get(artifact_field), artifact_field)
        actual_digest = _sha256_file(artifact_path)
        if actual_digest != expected_digest:
            raise ValueError(f"{digest_field} does not match {artifact_field} bytes")

    _require_timestamp(receipt.get("codex_security_completed_at"), "codex_security_completed_at")

    for field, expected_value in contract["pass_invariants"].items():
        if receipt.get(field) != expected_value:
            raise ValueError(f"Q10 pass invariant failed: {field}")


def _self_test(contract: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        artifact_root = Path(temp_dir)
        artifact_names = {
            "codex_security_report_artifact": "report.md",
            "codex_security_manifest_artifact": "manifest.json",
            "codex_security_findings_artifact": "findings.json",
            "codex_security_coverage_artifact": "coverage.json",
        }
        digests: dict[str, str] = {}
        for index, (artifact_field, name) in enumerate(artifact_names.items(), start=1):
            payload = f"q10-self-test-artifact-{index}\n".encode()
            (artifact_root / name).write_bytes(payload)
            digest_field = next(
                key for key, value in _ARTIFACT_FIELDS.items() if value == artifact_field
            )
            digests[digest_field] = "sha256:" + hashlib.sha256(payload).hexdigest()

        receipt: dict[str, Any] = {
            "gate": "Q10",
            "repository": contract["repository"],
            "source_sha": contract["source_sha"],
            "source_tree": contract["source_tree"],
            "release_subject_manifest_sha256": contract["release_subject_manifest_sha256"],
            "application_subject_manifest_sha256": contract[
                "application_subject_manifest_sha256"
            ],
            "scan_mode": "deep",
            "codex_security_scan_id": "scan-self-test",
            **artifact_names,
            **digests,
            "codex_security_completed_at": "2026-08-23T00:00:00Z",
            **contract["pass_invariants"],
        }
        validate_receipt(receipt, contract, artifact_root)

        tests = []
        changed_subject = dict(receipt)
        changed_subject["subject_changed"] = True
        tests.append((changed_subject, "changed subject"))

        wrong_application_subject = dict(receipt)
        wrong_application_subject["application_subject_manifest_sha256"] = "0" * 64
        tests.append((wrong_application_subject, "application subject mismatch"))

        fabricated_digest = dict(receipt)
        fabricated_digest["codex_security_report_sha256"] = "sha256:" + "a" * 64
        tests.append((fabricated_digest, "fabricated artifact digest"))

        for broken, label in tests:
            try:
                validate_receipt(broken, contract, artifact_root)
            except ValueError:
                continue
            raise AssertionError(f"self-test failed to reject {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CK-NEXUS Q10 native deep-scan receipt")
    parser.add_argument("receipt", nargs="?", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    contract = _load(CONTRACT_PATH)
    if args.self_test:
        _self_test(contract)
        print("Q10_NATIVE_DEEP_SCAN_RECEIPT_VALIDATOR=PASS")
        return 0
    if args.receipt is None:
        parser.error("receipt path is required unless --self-test is used")
    if args.artifact_root is None:
        parser.error("--artifact-root is required for receipt validation")
    validate_receipt(_load(args.receipt), contract, args.artifact_root)
    print("Q10_NATIVE_DEEP_SCAN_RECEIPT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
