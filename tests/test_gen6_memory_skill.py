from datetime import UTC, datetime, timedelta

import pytest

from creator_app.core.cognitive_memory_module import (
    CognitiveMemoryModuleGate,
    MemoryModuleActivationInput,
    MemoryModuleState,
)
from creator_app.core.dream_consolidator import (
    ConsolidationAction,
    DreamConsolidator,
    MemoryCandidate,
)
from creator_app.core.experience_skill import ExperienceRecord, ExperienceSkillLearner
from creator_app.core.memory_benchmarks import (
    BenchmarkStatus,
    MemoryBenchmarkCase,
    MemoryRegressionBenchmark,
)
from creator_app.core.memory_decay import MemoryDecayPolicy, MemoryKind, MemoryRecord


def test_memory_decay_reinforces_recently_used_memory() -> None:
    now = datetime.now(UTC)
    memory = MemoryRecord(
        memory_id="m1",
        kind=MemoryKind.SEMANTIC,
        content_digest="sha256:abc",
        created_at=now - timedelta(days=60),
        last_retrieved_at=now - timedelta(days=1),
        retrieval_count=3,
    )
    assert MemoryDecayPolicy().score_at(memory, now=now) > 0.5


def test_memory_decay_reproducible_clock_rejects_naive_time() -> None:
    now = datetime.now(UTC)
    memory = MemoryRecord(
        memory_id="m1",
        kind=MemoryKind.SEMANTIC,
        content_digest="sha256:abc",
        created_at=now,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        MemoryDecayPolicy().score_at(memory, now=datetime(2026, 8, 21, 10))


def test_superseded_memory_keeps_history_but_ranks_lower() -> None:
    now = datetime.now(UTC)
    base = MemoryRecord(
        memory_id="m1",
        kind=MemoryKind.EPISODIC,
        content_digest="sha256:abc",
        created_at=now,
    )
    superseded = base.model_copy(update={"superseded_by": "m2"})
    policy = MemoryDecayPolicy()
    assert policy.score_at(superseded, now=now) < policy.score_at(base, now=now)


def test_dream_duplicate_merge_requires_evidence() -> None:
    consolidator = DreamConsolidator()
    left = MemoryCandidate(memory_id="a", content_digest="sha256:x")
    right = MemoryCandidate(memory_id="b", content_digest="sha256:x")
    blocked = consolidator.decide_duplicate(left, right, evidence_ids=[])
    assert blocked.action == ConsolidationAction.BLOCK
    merged = consolidator.decide_duplicate(left, right, evidence_ids=["evd-1"])
    assert merged.action == ConsolidationAction.MERGE
    assert merged.promotable


def test_skill_candidate_requires_repeated_success_quality_and_evidence() -> None:
    learner = ExperienceSkillLearner()
    experiences = [
        ExperienceRecord(
            experience_id=f"e{i}",
            workflow_fingerprint="wf:stable",
            success=True,
            quality_score=0.9,
            evidence_ids=[f"evd-{i}"],
        )
        for i in range(3)
    ]
    candidate = learner.propose(skill_id="skill.demo", experiences=experiences)
    assert candidate.occurrences == 3
    assert candidate.average_quality == pytest.approx(0.9)
    assert not candidate.production_activation_allowed


def test_skill_candidate_rejects_insufficient_history() -> None:
    learner = ExperienceSkillLearner()
    with pytest.raises(ValueError, match="insufficient"):
        learner.propose(
            skill_id="skill.demo",
            experiences=[
                ExperienceRecord(
                    experience_id="e1",
                    workflow_fingerprint="wf:stable",
                    success=True,
                    evidence_ids=["evd-1"],
                )
            ],
        )


def test_skill_candidate_rejects_low_quality_history() -> None:
    learner = ExperienceSkillLearner()
    experiences = [
        ExperienceRecord(
            experience_id=f"e{i}",
            workflow_fingerprint="wf:stable",
            success=True,
            quality_score=0.4,
            evidence_ids=[f"evd-{i}"],
        )
        for i in range(3)
    ]
    with pytest.raises(ValueError, match="quality"):
        learner.propose(skill_id="skill.demo", experiences=experiences)


def test_memory_module_install_and_enable_are_fail_closed() -> None:
    gate = CognitiveMemoryModuleGate()
    verified = MemoryModuleActivationInput(
        runtime_contract="gen6.2",
        exact_subject="sha256:subject",
        evidence_ids=("evd-module",),
        ci_verified=True,
        independent_verification=True,
    )
    install = gate.check_install(verified)
    assert install.state == MemoryModuleState.INSTALLED_DISABLED
    assert not install.production_activation_allowed

    blocked_enable = gate.check_enable(verified)
    assert blocked_enable.state == MemoryModuleState.BLOCKED

    enabled = gate.check_enable(verified.model_copy(update={"governor_approved": True}))
    assert enabled.state == MemoryModuleState.ENABLED
    assert not enabled.production_activation_allowed


def test_memory_benchmark_fails_cross_tenant_retrieval() -> None:
    benchmark = MemoryRegressionBenchmark()
    case = MemoryBenchmarkCase(
        case_id="tenant-isolation",
        tenant_id="tenant-a",
        expected_memory_ids={"m1"},
        forbidden_memory_ids={"m-secret"},
    )
    result = benchmark.evaluate(
        case,
        retrieved_memory_ids=["m1", "m-secret"],
        retrieved_tenant_ids=["tenant-a", "tenant-b"],
        evidence_ids=["evd-1"],
    )
    assert result.status == BenchmarkStatus.FAIL
    assert not result.tenant_isolation_ok


def test_memory_benchmark_blocks_without_evidence() -> None:
    benchmark = MemoryRegressionBenchmark()
    case = MemoryBenchmarkCase(case_id="no-evidence", tenant_id="tenant-a")
    result = benchmark.evaluate(
        case,
        retrieved_memory_ids=[],
        retrieved_tenant_ids=[],
        evidence_ids=[],
    )
    assert result.status == BenchmarkStatus.BLOCKED
