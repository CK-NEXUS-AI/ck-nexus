import pytest

from creator_app.reliability import (
    FailureLedger,
    FailureObservation,
    FailureProtection,
    FailureState,
    fingerprint_failure,
    normalize_failure_signature,
)


def _observation(
    signature: str = "timeout request 123 on worker abcdef123456",
) -> FailureObservation:
    return FailureObservation(
        component="ai_gateway",
        operation="invoke",
        error_type="TimeoutError",
        safe_signature=signature,
        subject_sha="subject-1",
        evidence_digest="evidence-1",
    )


def _protection(subject: str = "subject-2") -> FailureProtection:
    return FailureProtection(
        root_cause="provider timeout lacked bounded retry contract",
        fix_ref="fix/retry-budget",
        regression_test_id="test_timeout_retry_budget",
        verifier_id="independent-verifier",
        verified_subject_sha=subject,
        proof_digest="proof-digest-1",
    )


def test_dynamic_values_normalize_to_same_signature() -> None:
    left = normalize_failure_signature(
        "Timeout 123 id 123e4567-e89b-12d3-a456-426614174000 deadbeefcafebabe"
    )
    right = normalize_failure_signature(
        "timeout 999 id 123e4567-e89b-12d3-a456-426614174001 feedfacecafed00d"
    )
    assert left == right


def test_fingerprint_is_stable_for_same_failure_class() -> None:
    left = fingerprint_failure(
        component="gateway",
        operation="route",
        error_type="ValueError",
        safe_signature="failed request 123 deadbeefcafebabe",
    )
    right = fingerprint_failure(
        component="GATEWAY",
        operation="ROUTE",
        error_type="VALUEERROR",
        safe_signature="failed request 999 feedfacecafed00d",
    )
    assert left == right


def test_new_known_failure_blocks_until_regression_protected() -> None:
    ledger = FailureLedger()
    decision = ledger.observe(_observation())
    assert decision.state is FailureState.BLOCKED_UNPROTECTED
    assert decision.release_blocked is True
    assert decision.occurrence_count == 1


def test_protection_requires_known_failure() -> None:
    ledger = FailureLedger()
    with pytest.raises(ValueError, match="unknown failure"):
        ledger.protect("0" * 64, _protection())


def test_verified_protection_closes_current_occurrence() -> None:
    ledger = FailureLedger()
    fingerprint = ledger.observe(_observation()).fingerprint
    decision = ledger.protect(fingerprint, _protection())
    assert decision.state is FailureState.PROTECTED
    assert decision.release_blocked is False


def test_recurrence_after_protection_reopens_failure() -> None:
    ledger = FailureLedger()
    observation = _observation()
    fingerprint = ledger.observe(observation).fingerprint
    ledger.protect(fingerprint, _protection())

    decision = ledger.observe(
        _observation("timeout request 777 on worker feedfacecafed00d")
    )
    assert decision.fingerprint == fingerprint
    assert decision.state is FailureState.BLOCKED_RECURRENCE
    assert decision.release_blocked is True
    assert decision.occurrence_count == 2
    assert decision.recurrence_count == 1


def test_recurrence_can_only_close_after_new_protection() -> None:
    ledger = FailureLedger()
    observation = _observation()
    fingerprint = ledger.observe(observation).fingerprint
    ledger.protect(fingerprint, _protection("subject-2"))
    ledger.observe(_observation("timeout request 456 on worker feedfacecafed00d"))

    decision = ledger.protect(fingerprint, _protection("subject-3"))
    assert decision.state is FailureState.PROTECTED
    assert decision.release_blocked is False
    assert decision.recurrence_count == 1


def test_jsonl_round_trip_preserves_append_only_state() -> None:
    ledger = FailureLedger()
    fingerprint = ledger.observe(_observation()).fingerprint
    ledger.protect(fingerprint, _protection())

    restored = FailureLedger.from_jsonl(ledger.to_jsonl())
    assert restored.events == ledger.events
    assert restored.decision(fingerprint).state is FailureState.PROTECTED


def test_tampered_sequence_is_rejected() -> None:
    ledger = FailureLedger()
    ledger.observe(_observation())
    content = ledger.to_jsonl().replace('"sequence":1', '"sequence":2')
    with pytest.raises(ValueError, match="sequence"):
        FailureLedger.from_jsonl(content)


def test_obvious_secret_material_is_rejected() -> None:
    with pytest.raises(ValueError, match="secret material"):
        _observation("Authorization: Bearer secret-value")


def test_release_blockers_only_returns_unprotected_or_recurrent_failures() -> None:
    ledger = FailureLedger()
    first = ledger.observe(_observation())
    assert [item.fingerprint for item in ledger.release_blockers()] == [first.fingerprint]

    ledger.protect(first.fingerprint, _protection())
    assert ledger.release_blockers() == ()
