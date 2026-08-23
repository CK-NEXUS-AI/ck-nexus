from pathlib import Path

import pytest

from creator_app.agnes.runtime import (
    DurableRun,
    DurableRunState,
    GovernedRecoveryCoordinator,
    JsonFileCheckpointStore,
    NoProgressGuard,
    ProgressDecision,
    VerificationState,
)


def test_checkpoint_survives_new_process_like_restore(tmp_path: Path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    run = DurableRun("run-crash")
    run.start()
    run.stage_write("external:1", {"status": "pending"})
    checkpoint = run.advance({"phase": "before-crash", "value": 7})
    store.save(checkpoint)

    restarted = DurableRun("run-crash")
    coordinator = GovernedRecoveryCoordinator(store, NoProgressGuard())
    assert coordinator.restore_latest(restarted)
    assert restarted.state is DurableRunState.PAUSED
    assert restarted.logical_state == {"phase": "before-crash", "value": 7}
    assert restarted.pending_writes == {"external:1": {"status": "pending"}}


def test_persisted_checkpoint_tampering_is_rejected(tmp_path: Path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    run = DurableRun("run-tamper")
    run.start()
    checkpoint = run.advance({"value": 1})
    store.save(checkpoint)

    path = store._path("run-tamper")
    raw = path.read_text(encoding="utf-8").replace('"value":1', '"value":2')
    path.write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError):
        store.load("run-tamper")


def test_no_progress_circuit_break_pauses_run_and_emits_measured_receipt(tmp_path: Path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    coordinator = GovernedRecoveryCoordinator(
        store,
        NoProgressGuard(warn_after=2, break_after=3, history_limit=4),
    )
    run = DurableRun("run-loop")
    run.start()
    action = {"tool": "read", "args": {"path": "same"}}

    first = coordinator.observe(run, action)
    second = coordinator.observe(run, action)
    third = coordinator.observe(run, action)

    assert first.decision is ProgressDecision.CONTINUE
    assert second.decision is ProgressDecision.WARN
    assert third.decision is ProgressDecision.CIRCUIT_BREAK
    assert run.state is DurableRunState.PAUSED

    receipt = coordinator.measured_receipt(
        third,
        subject="development-subject",
        producer_id="runtime-controller",
    )
    assert receipt.verification_state is VerificationState.MEASURED_NOT_VERIFIED
    assert receipt.evidence_digest == third.evidence_digest


def test_recovery_receipt_still_requires_independent_verifier(tmp_path: Path) -> None:
    coordinator = GovernedRecoveryCoordinator(
        JsonFileCheckpointStore(tmp_path),
        NoProgressGuard(warn_after=1, break_after=2, history_limit=2),
    )
    run = DurableRun("run-verify")
    run.start()
    observation = coordinator.observe(run, {"tool": "noop"})
    receipt = coordinator.measured_receipt(
        observation,
        subject="subject-x",
        producer_id="producer-x",
    )

    with pytest.raises(ValueError):
        receipt.attach_independent_verification("producer-x", "verification-digest")

    receipt.attach_independent_verification("verifier-y", "verification-digest")
    assert receipt.verification_state is VerificationState.VERIFIED
