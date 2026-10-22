from creator_app.control_plane.verification import ControlPlaneVerifier


def test_unverified_execution_never_becomes_release_evidence() -> None:
    verifier = ControlPlaneVerifier(max_repairs=2)
    result = verifier.evaluate(
        state="EXECUTED_UNVERIFIED",
        test_ok=True,
        security_ok=True,
        evidence_refs=["evidence://task-1"],
    )
    assert result.state == "VERIFIED"
    assert result.release_evidence is True
    assert result.patch_applied is False


def test_failed_verification_allows_bounded_repair_then_verifies() -> None:
    verifier = ControlPlaneVerifier(max_repairs=2)
    result = verifier.repair_loop(
        verify=lambda attempt: attempt == 2,
        evidence_refs=["evidence://task-2"],
    )
    assert result.state == "VERIFIED"
    assert result.attempts == 2
    assert result.release_evidence is True


def test_repair_limit_blocks_release() -> None:
    verifier = ControlPlaneVerifier(max_repairs=1)
    result = verifier.repair_loop(
        verify=lambda _attempt: False,
        evidence_refs=["evidence://task-3"],
    )
    assert result.state == "FAILED"
    assert result.attempts == 2
    assert result.release_evidence is False


def test_evaluate_rejects_empty_or_blank_evidence_refs() -> None:
    verifier = ControlPlaneVerifier()
    for refs in ([], [""], ["  "]):
        result = verifier.evaluate(
            state="EXECUTED_UNVERIFIED",
            test_ok=True,
            security_ok=True,
            evidence_refs=refs,
        )
        assert result.state == "FAILED"
        assert result.release_evidence is False


def test_repair_loop_fails_closed_when_verifier_raises() -> None:
    verifier = ControlPlaneVerifier(max_repairs=1)
    calls = []

    def verify(attempt: int) -> bool:
        calls.append(attempt)
        raise RuntimeError("verification unavailable")

    result = verifier.repair_loop(verify=verify, evidence_refs=["evidence://task-4"])
    assert result.state == "FAILED"
    assert result.release_evidence is False
    assert result.patch_applied is False
    assert calls == [1, 2]


def test_repair_loop_does_not_release_without_evidence_refs() -> None:
    verifier = ControlPlaneVerifier(max_repairs=0)
    result = verifier.repair_loop(verify=lambda _attempt: True, evidence_refs=[])
    assert result.state == "FAILED"
    assert result.release_evidence is False
