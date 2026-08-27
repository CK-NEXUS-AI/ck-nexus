#!/usr/bin/env python3
"""Fail-closed validator for CK-NEXUS Master Capability & Evidence Registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
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


def _digest_records(records: list[dict[str, Any]]) -> str:
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def load_registry(index_path: Path) -> dict[str, Any]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for fragment in index.get("fragments", []):
        path = Path(fragment["path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != fragment["sha256"]:
            raise ValueError(f"fragment digest mismatch: {path}")
        items = json.loads(raw)
        if len(items) != fragment["count"]:
            raise ValueError(f"fragment count mismatch: {path}")
        records.extend(items)
    data = dict(index)
    data["records"] = records
    return data


def _has(record: dict[str, Any], kind: str, status: str) -> bool:
    return any(
        e.get("kind") == kind and e.get("status") == status
        for e in record.get("evidence", [])
    )


def _has_measurement(record: dict[str, Any]) -> bool:
    return any(
        e.get("status") == "SUCCESS"
        and e.get("kind") in {"GITHUB_ACTIONS", "LIVE_RUNTIME", "BENCHMARK", "TEST_RUN"}
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
    if not SHA1_RE.fullmatch(str(baseline.get("sha", ""))):
        errors.append("baseline sha must be exact lowercase Git SHA")
    if not SHA1_RE.fullmatch(str(baseline.get("tree", ""))):
        errors.append("baseline tree must be exact lowercase Git SHA")

    records = data.get("records", [])
    if data.get("record_count") != len(records):
        errors.append("record_count mismatch")
    if data.get("records_digest_sha256") != _digest_records(records):
        errors.append("records_digest_sha256 mismatch")

    seen: set[str] = set()
    for i, r in enumerate(records):
        rid = str(r.get("id", ""))
        p = f"records[{i}] {rid or '<missing>'}:"
        if not rid:
            errors.append(f"{p} id required")
            continue
        if rid in seen:
            errors.append(f"{p} duplicate id")
        seen.add(rid)

        maturity = r.get("maturity")
        if maturity not in MATURITY_ORDER:
            errors.append(f"{p} invalid maturity")
            continue

        sha = r.get("sha")
        if sha is not None and not SHA1_RE.fullmatch(str(sha)):
            errors.append(f"{p} sha must be exact lowercase Git SHA")

        adopted = bool(r.get("adopted", False))
        production = bool(r.get("production", False))
        source = r.get("source")

        if source in {"DEV_PR", "RESEARCH_PR", "CHAT_CONTEXT"} and adopted:
            errors.append(f"{p} noncanonical source cannot claim adoption")
        if source == "CHAT_CONTEXT":
            if MATURITY_ORDER[maturity] > 1:
                errors.append(f"{p} chat context cannot exceed M1")
            if production:
                errors.append(f"{p} chat context cannot establish Production")
        if source == "RESEARCH_PR" and MATURITY_ORDER[maturity] > 1:
            errors.append(f"{p} research candidate cannot exceed M1")

        if maturity == "M3_MEASURED":
            if r.get("verification") != "MEASURED_NOT_VERIFIED":
                errors.append(f"{p} M3 must remain MEASURED_NOT_VERIFIED")
            if not _has_measurement(r):
                errors.append(f"{p} M3 requires successful measurement evidence")

        if maturity == "M4_INDEPENDENTLY_VERIFIED":
            if r.get("verification") != "INDEPENDENTLY_VERIFIED":
                errors.append(f"{p} M4 requires INDEPENDENTLY_VERIFIED")
            if not _has(r, "INDEPENDENT_VERIFIER", "SUCCESS"):
                errors.append(f"{p} M4 requires independent-verifier evidence")

        if maturity == "M5_ADOPTED_CANONICAL" and not adopted:
            errors.append(f"{p} M5 requires adopted=true")

        if r.get("truth") == "VERIFIED":
            if MATURITY_ORDER[maturity] < 4:
                errors.append(f"{p} VERIFIED requires M4+")
            if not _has(r, "INDEPENDENT_VERIFIER", "SUCCESS"):
                errors.append(f"{p} VERIFIED requires independent-verifier evidence")

        if production or maturity == "M6_PRODUCTION_QUALIFIED":
            if maturity != "M6_PRODUCTION_QUALIFIED":
                errors.append(f"{p} production=true requires M6")
            if not adopted:
                errors.append(f"{p} Production requires canonical adoption")
            if r.get("verification") != "INDEPENDENTLY_VERIFIED":
                errors.append(f"{p} Production requires independent verification")
            if not _has(r, "INDEPENDENT_VERIFIER", "SUCCESS"):
                errors.append(f"{p} Production requires independent-verifier evidence")
            if not _has(r, "PRODUCTION_GATE", "SUCCESS"):
                errors.append(f"{p} Production requires production-gate evidence")
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
