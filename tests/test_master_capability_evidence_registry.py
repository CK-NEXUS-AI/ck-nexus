from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from scripts.validate_master_capability_evidence_registry import load_registry, validate_registry

INDEX = Path("config/master_capability_evidence_registry.v1.json")


def _load() -> dict:
    return load_registry(INDEX)


def _record(data: dict, record_id: str) -> dict:
    return next(record for record in data["records"] if record["id"] == record_id)


def _redigest(data: dict) -> None:
    raw = json.dumps(
        data["records"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    data["record_count"] = len(data["records"])
    data["records_digest_sha256"] = hashlib.sha256(raw.encode()).hexdigest()


def test_registry_is_semantically_valid() -> None:
    assert validate_registry(_load()) == []


def test_measured_subject_cannot_self_promote_to_verified() -> None:
    data = copy.deepcopy(_load())
    record = _record(data, "cap.verifier.subject_gap")
    record["maturity"] = "M4_INDEPENDENTLY_VERIFIED"
    record["verification"] = "INDEPENDENTLY_VERIFIED"
    record["truth"] = "VERIFIED"
    _redigest(data)
    errors = validate_registry(data)
    assert any("independent-verifier evidence" in error for error in errors)


def test_production_requires_adoption_verifier_and_gates() -> None:
    data = copy.deepcopy(_load())
    record = _record(data, "cap.runtime.durable_execution")
    record["maturity"] = "M6_PRODUCTION_QUALIFIED"
    record["verification"] = "INDEPENDENTLY_VERIFIED"
    record["truth"] = "VERIFIED"
    record["production"] = True
    _redigest(data)
    errors = validate_registry(data)
    assert any("canonical adoption" in error for error in errors)
    assert any("independent-verifier evidence" in error for error in errors)
    assert any("production-gate evidence" in error for error in errors)


def test_chat_context_cannot_be_promoted() -> None:
    data = copy.deepcopy(_load())
    record = _record(data, "cap.verifier.ui_prototype")
    record["maturity"] = "M3_MEASURED"
    record["verification"] = "MEASURED_NOT_VERIFIED"
    _redigest(data)
    errors = validate_registry(data)
    assert any("chat context cannot exceed M1" in error for error in errors)


def test_duplicate_ids_are_rejected() -> None:
    data = copy.deepcopy(_load())
    data["records"].append(copy.deepcopy(data["records"][0]))
    _redigest(data)
    errors = validate_registry(data)
    assert any("duplicate id" in error for error in errors)


def test_unsealed_record_edit_is_detected() -> None:
    data = copy.deepcopy(_load())
    _record(data, "cap.verifier.shadow_ledger")["name"] = "tampered"
    errors = validate_registry(data)
    assert "records_digest_sha256 mismatch" in errors
