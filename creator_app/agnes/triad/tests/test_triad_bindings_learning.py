import pytest

from creator_app.agnes.runtime import DurableRun
from creator_app.agnes.runtime.progress_guard import NoProgressGuard, ProgressDecision
from creator_app.agnes.triad import (
    LearningCandidate,
    LearningConsolidator,
    LearningKind,
    LearningState,
    TriadCheckpointBinding,
    TriadProgressBinding,
)


def test_triad_progress_binding_reuses_runtime_guard() -> None:
    binding = TriadProgressBinding(NoProgressGuard(warn_after=2, break_after=3, history_limit=4))
    state = {"candidate": "v1"}
    action = {"type": "revise"}
    assert binding.observe(step_index=1, state=state, action=action) is ProgressDecision.CONTINUE
    assert binding.observe(step_index=2, state=state, action=action) is ProgressDecision.WARN
    assert binding.observe(step_index=3, state=state, action=action) is ProgressDecision.CIRCUIT_BREAK


def test_triad_checkpoint_round_trip() -> None:
    binding = TriadCheckpointBinding(DurableRun("triad-run"))
    checkpoint = binding.checkpoint(cycle_id="cycle-1", state={"candidate": "v2", "risk": 2})
    binding.checkpoint(cycle_id="cycle-2", state={"candidate": "v3", "risk": 1})
    restored = binding.restore(checkpoint)
    assert restored == {"candidate": "v2", "risk": 2}


def test_learning_requires_quarantine_test_measure_before_verify() -> None:
    candidate = LearningCandidate.create(
        kind=LearningKind.CAPABILITY,
        summary="new parser candidate",
        source_refs=["src-1"],
        producer_id="agnes-a",
    )
    with pytest.raises(ValueError):
        candidate.mark_tested()
    candidate.quarantine()
    candidate.mark_tested()
    candidate.attach_measurement(["evidence-1"])
    assert candidate.state is LearningState.MEASURED_NOT_VERIFIED
    with pytest.raises(ValueError):
        candidate.attach_independent_verification("agnes-a")
    candidate.attach_independent_verification("independent-verifier")
    assert candidate.state is LearningState.VERIFIED


def test_learning_consolidator_deduplicates() -> None:
    consolidator = LearningConsolidator()
    candidate = LearningCandidate.create(kind=LearningKind.KNOWLEDGE, summary="same fact")
    assert consolidator.add(candidate)
    assert not consolidator.add(candidate)
    assert len(consolidator.pending()) == 1
