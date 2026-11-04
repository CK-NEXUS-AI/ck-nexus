#!/usr/bin/env python3
"""Fail-closed validator for CK-NEXUS Master Capability & Evidence Registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
MATURITY_ORDER = {
    "M0_MISSING": 0,
    "M1_CANDIDATE": 1,
    "M2_IMPLEMENTED_PARTIAL": 2,
    "M3_MEASURED": 3,
    "M4_INDEPENDENTLY_VERIFIED": 4,
    "M5_ADOPTED_CANONICAL": 5,
    "M6_PRODUCTION_QUALIFIED": 6,
}
MEASUREMENT_KINDS = {"GITHUB_ACTIONS", "LIVE_RUNTIME", "BENCHMARK", "TEST_RUN"}


def _digest_records(records: list[dict[str, Any]]) -> str:
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def load_registry(index_path: Path) -> dict[str, Any]:
    index_path = index_path.resolve()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    repo_root = index_path.parent.parent.resolve()
    fragments = index.get("fragments", [])
    if not isinstance(fragments, list) or not fragments:
        raise ValueError("fragments must be a non-empty list")

    records: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for fragment in fragments:
        raw_path = str(fragment.get("path", ""))
        logical_path = PurePosixPath(raw_path)
        if not raw_path or logical_path.is_absolute() or ".." in logical_path.parts:
            raise ValueError(f"unsafe fragment path: {raw_path}")
        if raw_path in seen_paths:
            raise ValueError(f"duplicate fragment path: {raw_path}")
        seen_paths.add(raw_path)

        candidate = repo_root.joinpath(*logical_path.parts)
        resolved = candidate.resolve()
        if not resolved.is_relative_to(repo_root):
            raise ValueError(f"fragment escapes repository root: {raw_path}")
        if candidate.is_symlink():
            raise ValueError(f"fragment symlink is not allowed: {raw_path}")

        raw = candidate.read_bytes()
        if hashlib.sha256(raw).hexdigest() != fragment.get("sha256"):
            raise ValueError(f"fragment digest mismatch: {raw_path}")
        items = json.loads(raw)
        if not isinstance(items, list):
            raise ValueError(f"fragment must contain a JSON list: {raw_path}")
        if len(items) != fragment.get("count"):
            raise ValueError(f"fragment count mismatch: {raw_path}")
        records.extend(items)

    data = dict(index)
    data["records"] = records
    return data


def _has(record: dict[str, Any], kind: str, status: str) -> bool:
    return any(
        e.get("kind") == kind and e.get("status") == status
        for e in record.get("evidence", [])
    )


def _has_subject_evidence(record: dict[str, Any], kind: str, status: str) -> bool:
    subject_sha = record.get("sha")
    if not isinstance(subject_sha, str) or not SHA1_RE.fullmatch(subject_sha):
        return False
    return any(
        e.get("kind") == kind
        and e.get("status") == status
        and e.get("subject_sha") == subject_sha
        for e in record.get("evidence", [])
    )


def _has_measurement(record: dict[str, Any]) -> bool:
    subject_sha = record.get("sha")
    for evidence in record.get("evidence", []):
        if (
            evidence.get("status") != "SUCCESS"
            or evidence.get("kind") not in MEASUREMENT_KINDS
        ):
            continue
        if evidence.get("kind") == "GITHUB_ACTIONS":
            # Exact GitHub head binding is revalidated online by the dedicated CI checker.
            return True
        if evidence.get("subject_sha") == subject_sha:
            return True
    return False


def _has_legacy_canonical_presence(record: dict[str, Any]) -> bool:
    accepted = {
        ("CANONICAL_MAIN", "PRESENT"),
        ("SOURCE", "PRESENT"),
        ("MERGED_PR", "MERGED"),
    }
    return any(
        (e.get("kind"), e.get("status")) in accepted
        for e in record.get("evidence", [])
    )


def validate_registry(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("kind") != "NON_AUTHORITATIVE_RECONCILIATION_PROJECTION":
        errors.append("registry kind must remain non-authoritative")

    authority = data.get("authority", {})
    if authority.get("registry_can_issue_verified") is not False:
        errors.append("registry must not issue VERIFIED")
    if authority.get("registry_can_mutate_production") is not False:
        errors.append("registry must not mutate Production")
    if authority.get("chat_is_authority") is not False:
        errors.append("chat must not be authority")

    baseline = data.get("baseline", {})
    baseline_sha = str(baseline.get("sha", ""))
    if not SHA1_RE.fullmatch(baseline_sha):
        errors.append("baseline sha must be exact lowercase Git SHA")
    if not SHA1_RE.fullmatch(str(baseline.get("tree", ""))):
        errors.append("baseline tree must be exact lowercase Git SHA")

    records = data.get("records", [])
    if data.get("record_count") != len(records):
        errors.append("record_count mismatch")
    if data.get("records_digest_sha256") != _digest_records(records):
        errors.append("records_digest_sha256 mismatch")

    seen: set[str] = set()
    for i, record in enumerate(records):
        rid = str(record.get("id", ""))
        prefix = f"records[{i}] {rid or '<missing>'}:"
        if not rid:
            errors.append(f"{prefix} id required")
            continue
        if rid in seen:
            errors.append(f"{prefix} duplicate id")
        seen.add(rid)

        maturity = record.get("maturity")
        if maturity not in MATURITY_ORDER:
            errors.append(f"{prefix} invalid maturity")
            continue

        sha = record.get("sha")
        if sha is not None and not SHA1_RE.fullmatch(str(sha)):
            errors.append(f"{prefix} sha must be exact lowercase Git SHA")

        adopted = bool(record.get("adopted", False))
        production = bool(record.get("production", False))
        source = record.get("source")

        if source in {"DEV_PR", "RESEARCH_PR", "CHAT_CONTEXT"} and adopted:
            errors.append(f"{prefix} noncanonical source cannot claim adoption")
        if source == "CHAT_CONTEXT":
            if MATURITY_ORDER[maturity] > 1:
                errors.append(f"{prefix} chat context cannot exceed M1")
            if production:
                errors.append(f"{prefix} chat context cannot establish Production")
        if source == "RESEARCH_PR" and MATURITY_ORDER[maturity] > 1:
            errors.append(f"{prefix} research candidate cannot exceed M1")

        if maturity == "M3_MEASURED":
            if record.get("verification") != "MEASURED_NOT_VERIFIED":
                errors.append(f"{prefix} M3 must remain MEASURED_NOT_VERIFIED")
            if not isinstance(sha, str) or not SHA1_RE.fullmatch(sha):
                errors.append(f"{prefix} M3 requires an exact subject sha")
            if not _has_measurement(record):
                errors.append(f"{prefix} M3 requires successful measurement evidence")

        if maturity == "M4_INDEPENDENTLY_VERIFIED":
            if record.get("verification") != "INDEPENDENTLY_VERIFIED":
                errors.append(f"{prefix} M4 requires INDEPENDENTLY_VERIFIED")
            if not isinstance(sha, str) or not SHA1_RE.fullmatch(sha):
                errors.append(f"{prefix} M4 requires an exact subject sha")
            if not _has_subject_evidence(record, "INDEPENDENT_VERIFIER", "SUCCESS"):
                errors.append(
                    f"{prefix} M4 requires independent-verifier evidence "
                    "bound to exact subject"
                )

        if maturity == "M5_ADOPTED_CANONICAL":
            if not adopted:
                errors.append(f"{prefix} M5 requires adopted=true")
            legacy_baseline = (
                source == "CANONICAL_MAIN"
                and record.get("verification") == "CANONICAL_PRESENT"
                and (sha is None or sha == baseline_sha)
                and _has_legacy_canonical_presence(record)
            )
            if not legacy_baseline:
                if record.get("verification") != "INDEPENDENTLY_VERIFIED":
                    errors.append(
                        f"{prefix} non-baseline M5 requires independent verification "
                        "before adoption"
                    )
                if not isinstance(sha, str) or not SHA1_RE.fullmatch(sha):
                    errors.append(
                        f"{prefix} non-baseline M5 requires an exact subject sha"
                    )
                if not _has_subject_evidence(
                    record, "INDEPENDENT_VERIFIER", "SUCCESS"
                ):
                    errors.append(
                        f"{prefix} non-baseline M5 requires exact-subject "
                        "independent-verifier evidence"
                    )

        if record.get("truth") == "VERIFIED":
            if MATURITY_ORDER[maturity] < 4:
                errors.append(f"{prefix} VERIFIED requires M4+")
            if not _has_subject_evidence(record, "INDEPENDENT_VERIFIER", "SUCCESS"):
                errors.append(
                    f"{prefix} VERIFIED requires independent-verifier evidence "
                    "bound to exact subject"
                )

        if production or maturity == "M6_PRODUCTION_QUALIFIED":
            if maturity != "M6_PRODUCTION_QUALIFIED":
                errors.append(f"{prefix} production=true requires M6")
            if not adopted:
                errors.append(f"{prefix} Production requires canonical adoption")
            if record.get("verification") != "INDEPENDENTLY_VERIFIED":
                errors.append(f"{prefix} Production requires independent verification")
            if not isinstance(sha, str) or not SHA1_RE.fullmatch(sha):
                errors.append(f"{prefix} Production requires an exact subject sha")
            if not _has_subject_evidence(record, "INDEPENDENT_VERIFIER", "SUCCESS"):
                errors.append(
                    f"{prefix} Production requires exact-subject "
                    "independent-verifier evidence"
                )
            if not _has_subject_evidence(record, "PRODUCTION_GATE", "SUCCESS"):
                errors.append(
                    f"{prefix} Production requires exact-subject "
                    "production-gate evidence"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "index",
        nargs="?",
        type=Path,
        default=Path("config/master_capability_evidence_registry.v1.json"),
    )
    args = parser.parse_args()
    try:
        data = load_registry(args.index)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    errors = validate_registry(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(data['records'])} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
