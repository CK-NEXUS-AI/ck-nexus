from __future__ import annotations

from scripts.propose_claim_transition import build_proposal


def _claim() -> dict:
    return {
        "claim_id": "CLAIM-MOBILE-001",
        "state": "TARGET",
        "subject": {"commit": "a" * 40},
        "benchmark": {"protocol_ref": "PR #151"},
    }


def _summary() -> dict:
    return {
        "schema": "ck-nexus.termux-benchmark.v2",
        "claim_id": "CLAIM-MOBILE-001",
        "claim_status": "MEASURED_NOT_VERIFIED",
        "subject_commit": "a" * 40,
        "rounds": 5,
        "device": {"mem_total_kib": 4_000_000, "model": "test-device"},
        "layers_completed": ["local_api", "integrated_local_provider"],
        "measurement_method": "visible process RSS and curl time_total",
        "limitations": ["process RSS is not Android PSS"],
        "memory": {"combined_rss_kib": 1000},
        "latency_ms": {"ck_nexus_median": 100.0},
    }


def test_proposal_never_auto_verifies() -> None:
    proposal = build_proposal(
        _claim(),
        _summary(),
        evidence_path="evidence/run-1",
        evidence_sha256="b" * 64,
        output_digest="c" * 64,
        captured_at="2026-08-23T04:20:00+00:00",
    )
    assert proposal["to_state"] == "MEASURED_NOT_VERIFIED"
    assert proposal["automatic_promotion_allowed"] is False
    assert proposal["verifier_required_for_verified"] is True


def test_subject_mismatch_is_rejected() -> None:
    summary = _summary()
    summary["subject_commit"] = "d" * 40
    try:
        build_proposal(
            _claim(),
            summary,
            evidence_path="evidence/run-1",
            evidence_sha256="b" * 64,
            output_digest="c" * 64,
            captured_at="2026-08-23T04:20:00+00:00",
        )
    except ValueError as exc:
        assert "subject commit" in str(exc)
    else:
        raise AssertionError("subject mismatch must fail closed")


def test_fewer_than_three_rounds_is_rejected() -> None:
    summary = _summary()
    summary["rounds"] = 2
    try:
        build_proposal(
            _claim(),
            summary,
            evidence_path="evidence/run-1",
            evidence_sha256="b" * 64,
            output_digest="c" * 64,
            captured_at="2026-08-23T04:20:00+00:00",
        )
    except ValueError as exc:
        assert "at least 3" in str(exc)
    else:
        raise AssertionError("insufficient runs must fail closed")
