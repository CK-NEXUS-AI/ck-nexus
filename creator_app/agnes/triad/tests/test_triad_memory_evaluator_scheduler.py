import pytest

from creator_app.agnes.triad.artifacts import CandidateArtifact, ClaimState
from creator_app.agnes.triad.evaluator import EvidenceEvaluator
from creator_app.agnes.triad.events import TriadRole
from creator_app.agnes.triad.memory import MemoryLayer, TriadMemoryEntry, TriadMemoryStore
from creator_app.agnes.triad.pulse import PulsePhase
from creator_app.agnes.triad.scheduler import TriadParallelScheduler, WorkMode


def test_memory_requires_evidence_before_measured() -> None:
    entry = TriadMemoryEntry.create(cycle_id="c1", producer_id="builder", content={"claim": "x"})
    entry.promote(MemoryLayer.DIALOGUE)
    entry.promote(MemoryLayer.CANDIDATE)
    with pytest.raises(ValueError):
        entry.promote(MemoryLayer.MEASURED)
    entry.promote(MemoryLayer.MEASURED, evidence_refs=["ev-1"])
    assert entry.layer is MemoryLayer.MEASURED


def test_memory_forbids_self_verification() -> None:
    entry = TriadMemoryEntry.create(cycle_id="c1", producer_id="builder", content={"claim": "x"}, layer=MemoryLayer.CANDIDATE)
    entry.promote(MemoryLayer.MEASURED, evidence_refs=["ev-1"])
    with pytest.raises(ValueError):
        entry.attach_independent_verification("builder", "verify-1")
    entry.attach_independent_verification("independent", "verify-1")
    assert entry.layer is MemoryLayer.VERIFIED


def test_failure_memory_is_terminal() -> None:
    entry = TriadMemoryEntry.create(cycle_id="c1", producer_id="builder", content={"claim": "x"})
    entry.reject("failure-ev")
    with pytest.raises(ValueError):
        entry.promote(MemoryLayer.CANDIDATE)


def test_memory_store_filters_by_layer() -> None:
    store = TriadMemoryStore()
    a = TriadMemoryEntry.create(cycle_id="c1", producer_id="a", content={"n": 1})
    b = TriadMemoryEntry.create(cycle_id="c1", producer_id="b", content={"n": 2}, layer=MemoryLayer.DISCOVERED)
    store.put(a)
    store.put(b)
    assert store.by_layer(MemoryLayer.DISCOVERED) == (b,)


def test_evaluator_only_measures_not_verifies() -> None:
    candidate = CandidateArtifact("cand-1", "c1", "builder", "claim", {"design": 1})
    result = EvidenceEvaluator("evaluator").evaluate(candidate, ["ev-a", "ev-b"])
    assert result.state is ClaimState.MEASURED_NOT_VERIFIED
    assert candidate.state is ClaimState.MEASURED_NOT_VERIFIED
    assert candidate.verifier_id is None


def test_producer_cannot_evaluate_own_candidate() -> None:
    candidate = CandidateArtifact("cand-1", "c1", "builder", "claim", {})
    with pytest.raises(ValueError):
        EvidenceEvaluator("builder").evaluate(candidate, ["ev-a"])


def test_parallel_scheduler_runs_builder_and_critic_concurrently() -> None:
    plan = TriadParallelScheduler().plan(PulsePhase.ACTIVE_PARALLEL, candidate_available=False)
    assert plan[0].role is TriadRole.BUILDER and plan[0].mode is WorkMode.PARALLEL
    assert plan[1].role is TriadRole.CRITIC and plan[1].mode is WorkMode.PARALLEL
    assert plan[2].role is TriadRole.EVALUATOR and plan[2].mode is WorkMode.IDLE


def test_evaluator_becomes_event_driven_when_candidate_exists() -> None:
    plan = TriadParallelScheduler().plan(PulsePhase.ACTIVE_PARALLEL, candidate_available=True)
    evaluator = next(item for item in plan if item.role is TriadRole.EVALUATOR)
    assert evaluator.mode is WorkMode.EVENT_DRIVEN


def test_checkpoint_is_governor_only() -> None:
    plan = TriadParallelScheduler().plan(PulsePhase.CHECKPOINT, candidate_available=True)
    assert len(plan) == 1
    assert plan[0].role is TriadRole.GOVERNOR
    assert plan[0].mode is WorkMode.CHECKPOINT
