from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_master_capability_evidence_registry import (
    load_registry,
    validate_registry,
)
from scripts.verify_master_registry_github_evidence import validate_exact_head_runs

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
    assert any(
        "independent-verifier evidence bound to exact subject" in error
        for error in errors
    )


def test_wrong_subject_verifier_evidence_is_rejected() -> None:
    data = copy.deepcopy(_load())
    record = _record(data, "cap.verifier.subject_gap")
    record["maturity"] = "M4_INDEPENDENTLY_VERIFIED"
    record["verification"] = "INDEPENDENTLY_VERIFIED"
    record["truth"] = "VERIFIED"
    record.setdefault("evidence", []).append(
        {
            "kind": "INDEPENDENT_VERIFIER",
            "status": "SUCCESS",
            "subject_sha": "0" * 40,
            "ref": "forged-wrong-subject-receipt",
        }
    )
    _redigest(data)
    errors = validate_registry(data)
    assert any("bound to exact subject" in error for error in errors)


def test_nonbaseline_m5_cannot_skip_independent_verification() -> None:
    data = copy.deepcopy(_load())
    record = _record(data, "cap.runtime.durable_execution")
    record["maturity"] = "M5_ADOPTED_CANONICAL"
    record["source"] = "CANONICAL_MAIN"
    record["verification"] = "CANONICAL_PRESENT"
    record["adopted"] = True
    _redigest(data)
    errors = validate_registry(data)
    assert any(
        "non-baseline M5 requires independent verification" in error
        for error in errors
    )


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


def test_fragment_path_traversal_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    config = repo / "config"
    config.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    index = config / "registry.json"
    index.write_text(
        json.dumps(
            {
                "fragments": [
                    {
                        "path": "../outside.json",
                        "count": 0,
                        "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsafe fragment path"):
        load_registry(index)


def test_stale_success_run_cannot_satisfy_m3_exact_subject() -> None:
    data = _load()
    record = copy.deepcopy(_record(data, "cap.verifier.subject_gap"))
    stale_sha = "1" * 40

    def runs_for_sha(_sha: str) -> list[dict]:
        return [{"id": 99999999, "head_sha": stale_sha, "conclusion": "success"}]

    errors = validate_exact_head_runs({"records": [record]}, runs_for_sha)
    assert any(
        "no successful GitHub Actions run bound to exact subject" in error
        for error in errors
    )


def test_listed_run_id_must_belong_to_exact_subject() -> None:
    data = _load()
    record = copy.deepcopy(_record(data, "cap.verifier.subject_gap"))
    record["evidence"] = [
        {
            "kind": "GITHUB_ACTIONS",
            "status": "SUCCESS",
            "ref": "CK-NEXUS CI 12345678",
        }
    ]

    def runs_for_sha(sha: str) -> list[dict]:
        return [{"id": 87654321, "head_sha": sha, "conclusion": "success"}]

    errors = validate_exact_head_runs({"records": [record]}, runs_for_sha)
    assert any("listed successful run id(s) not bound" in error for error in errors)
