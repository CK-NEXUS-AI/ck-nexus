import pytest

from creator_app.agnes.triad import (
    AdaptivePulseController,
    CandidateArtifact,
    ClaimState,
    Objection,
    PulsePhase,
    TriadEvent,
    TriadEventBus,
    TriadEventType,
    TriadRole,
)


def test_event_bus_is_append_only_and_idempotent() -> None:
    bus = TriadEventBus()
    event = TriadEvent.create(
        cycle_id="cycle-1",
        actor=TriadRole.BUILDER,
        event_type=TriadEventType.PROPOSAL_CREATED,
        payload={"candidate": "c1"},
        created_at="2026-08-23T00:00:00+00:00",
    )
    bus.publish(event)
    bus.publish(event)
    assert bus.by_cycle("cycle-1") == (event,)


def test_objection_moves_candidate_to_discussed_without_auto_rejecting() -> None:
    candidate = CandidateArtifact("c1", "cycle-1", "builder-a", "use async cache", {"kind": "cache"})
    objection = Objection.create(claim_id="c1", reason="cache failure path is not measured")
    candidate.add_objection(objection)
    assert candidate.state is ClaimState.DISCUSSED
    assert candidate.objections == [objection]


def test_measurement_does_not_equal_verification() -> None:
    candidate = CandidateArtifact("c1", "cycle-1", "builder-a", "claim", {})
    candidate.attach_measurement(["evd-test-1", "evd-bench-1"])
    assert candidate.state is ClaimState.MEASURED_NOT_VERIFIED
    assert candidate.measurement_digest


def test_candidate_cannot_self_verify() -> None:
    candidate = CandidateArtifact("c1", "cycle-1", "builder-a", "claim", {})
    candidate.attach_measurement(["evd-1"])
    with pytest.raises(ValueError):
        candidate.attach_independent_verification("builder-a", "verify-1")
    candidate.attach_independent_verification("independent-verifier", "verify-1")
    assert candidate.state is ClaimState.VERIFIED


def test_pulse_is_15_active_20_discovery_then_checkpoint() -> None:
    pulse = AdaptivePulseController()
    assert pulse.phase_at(0) is PulsePhase.ACTIVE_PARALLEL
    assert pulse.phase_at(14) is PulsePhase.ACTIVE_PARALLEL
    assert pulse.phase_at(15) is PulsePhase.DISCOVERY_CONSOLIDATION
    assert pulse.phase_at(34) is PulsePhase.DISCOVERY_CONSOLIDATION
    assert pulse.phase_at(35) is PulsePhase.CHECKPOINT


def test_three_empty_cycles_enter_idle_and_progress_resets() -> None:
    pulse = AdaptivePulseController()
    assert pulse.record_cycle(progress_made=False) is PulsePhase.DISCOVERY_CONSOLIDATION
    assert pulse.record_cycle(progress_made=False) is PulsePhase.DISCOVERY_CONSOLIDATION
    assert pulse.record_cycle(progress_made=False) is PulsePhase.IDLE
    assert pulse.record_cycle(progress_made=True) is PulsePhase.ACTIVE_PARALLEL
    assert pulse.empty_cycles == 0
