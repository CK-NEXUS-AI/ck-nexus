from scripts.validate_claim_registry import (
    publication_status,
    validate_append_only,
    validate_claim,
)


def _target_claim() -> dict:
    return {
        "claim_id": "CLAIM-MOBILE-001",
        "claim_text_th": "AGNES รันได้บน Android/Termux ที่มี RAM 4GB",
        "category": "mobile-first",
        "state": "TARGET",
        "created_by": "creator-a",
        "subject": {
            "commit": "a" * 40,
            "component": "AGNES",
            "environment": "Android/Termux RAM 4GB",
        },
        "benchmark": {
            "protocol_ref": "PR #151",
            "harness_commit": "b" * 40,
            "layers_completed": [],
            "runs": 0,
            "aggregation": None,
            "measurement_method": None,
            "measurement_limitations": None,
        },
        "evidence": None,
        "verifier": None,
        "state_history": [
            {
                "from_state": None,
                "to_state": "TARGET",
                "at": "2026-08-23T04:09:00Z",
                "reason": "Initial target",
            }
        ],
        "created_at": "2026-08-23T04:09:00Z",
    }


def test_target_claim_is_valid() -> None:
    assert validate_claim(_target_claim()) == []


def test_target_cannot_jump_directly_to_verified() -> None:
    claim = _target_claim()
    claim["state"] = "VERIFIED"
    claim["state_history"].append(
        {
            "from_state": "TARGET",
            "to_state": "VERIFIED",
            "at": "2026-08-23T05:00:00Z",
            "reason": "Invalid jump",
        }
    )
    errors = validate_claim(claim)
    assert any("forbidden transition" in error for error in errors)


def test_verified_claim_rejects_self_certification() -> None:
    claim = _target_claim()
    claim["state"] = "VERIFIED"
    claim["benchmark"].update(
        {
            "runs": 3,
            "aggregation": "median",
            "measurement_method": "ps RSS aggregation",
            "measurement_limitations": "Android process visibility can be restricted.",
        }
    )
    claim["evidence"] = {
        "evidence_path": "evidence/mobile.json",
        "evidence_sha256": "c" * 64,
        "exit_code": 0,
        "output_digest": "digest",
        "timestamp": "2026-08-23T05:00:00Z",
    }
    claim["verifier"] = {
        "verified_by": "creator-a",
        "verified_at": "2026-08-23T05:10:00Z",
        "verdict_reason": "Reviewed",
    }
    claim["state_history"].extend(
        [
            {
                "from_state": "TARGET",
                "to_state": "MEASURED_NOT_VERIFIED",
                "at": "2026-08-23T05:00:00Z",
                "reason": "Measured",
            },
            {
                "from_state": "MEASURED_NOT_VERIFIED",
                "to_state": "VERIFIED",
                "at": "2026-08-23T05:10:00Z",
                "reason": "Verified",
            },
        ]
    )
    errors = validate_claim(claim)
    assert "self-certification is not allowed" in errors


def test_append_only_history_rejects_rewrite() -> None:
    previous = _target_claim()
    current = _target_claim()
    current["state_history"][0]["reason"] = "Rewritten"
    errors = validate_append_only(current, previous)
    assert "existing state_history entries cannot be modified" in errors


def test_verified_claim_becomes_stale_on_subject_drift() -> None:
    claim = _target_claim()
    claim["state"] = "VERIFIED"
    assert publication_status(claim, "d" * 40) == "STALE"
