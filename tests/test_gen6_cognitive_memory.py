from datetime import datetime, timedelta, timezone

from creator_app.core.dream_consolidation import (
    DreamConsolidationEngine,
    MemoryFragment,
)
from creator_app.core.experience_skill import (
    ExperienceRecord,
    ExperienceSkillEngine,
    PromotionDecision,
)
from creator_app.core.memory_decay import MemoryDecayEngine, MemoryDecayInput
from creator_app.core.memory_regression import (
    BenchmarkStatus,
    MemoryBenchmarkCase,
    MemoryRegressionBenchmark,
)


def test_memory_decay_is_deterministic_with_explicit_clock() -> None:
    now = datetime(2026, 8, 21, 10, tzinfo=timezone.utc)
    memory = MemoryDecayInput(
        created_at=now - timedelta(days=10),
        last_accessed_at=now - timedelta(days=2),
        access_count=3,
        importance=0.7,
    )
    engine = MemoryDecayEngine()

    first = engine.evaluate(memory, now=now)
    second = engine.evaluate(memory, now=now)

    assert first == second
    assert 0 <= first.retention_score <= 1


def test_protected_memory_does_not_decay() -> None:
    now = datetime(2026, 8, 21, 10, tzinfo=timezone.utc)
    memory = MemoryDecayInput(
        created_at=now - timedelta(days=500),
        last_accessed_at=now - timedelta(days=300),
        protected=True,
    )

    result = MemoryDecayEngine().evaluate(memory, now=now)

    assert result.retention_score == 1.0
    assert result.expired is False


def test_dream_consolidation_requires_evidence() -> None:
    fragments = [
        MemoryFragment(
            memory_id="m1",
            topic="routing",
            content_ref="ref:1",
            evidence_ids=["evd:1"],
        ),
        MemoryFragment(
            memory_id="m2",
            topic="routing",
            content_ref="ref:2",
            evidence_ids=[],
        ),
    ]

    assert DreamConsolidationEngine().consolidate(fragments) == []


def test_dream_consolidation_is_stably_sorted() -> None:
    fragments = [
        MemoryFragment(
            memory_id="m2",
            topic="Routing",
            content_ref="ref:2",
            evidence_ids=["evd:2"],
        ),
        MemoryFragment(
            memory_id="m1",
            topic="routing",
            content_ref="ref:1",
            evidence_ids=["evd:1"],
        ),
    ]

    result = DreamConsolidationEngine().consolidate(fragments)

    assert len(result) == 1
    assert result[0].source_memory_ids == ["m1", "m2"]
    assert result[0].evidence_ids == ["evd:1", "evd:2"]


def test_experience_promotes_only_verified_repetition() -> None:
    records = [
        ExperienceRecord(
            experience_id=f"exp:{index}",
            skill_key="search.plan",
            success=True,
            quality_score=0.9,
            evidence_ids=[f"evd:{index}"],
        )
        for index in range(1, 4)
    ]

    result = ExperienceSkillEngine().evaluate(records, skill_key="search.plan")

    assert result.decision == PromotionDecision.PROMOTE
    assert result.sample_count == 3


def test_experience_rejects_success_without_evidence() -> None:
    records = [
        ExperienceRecord(
            experience_id="exp:1",
            skill_key="search.plan",
            success=True,
            quality_score=1.0,
            evidence_ids=[],
        )
    ]

    result = ExperienceSkillEngine().evaluate(records, skill_key="search.plan")

    assert result.decision == PromotionDecision.REJECT


def test_memory_regression_passes_exact_recall() -> None:
    cases = [
        MemoryBenchmarkCase(
            case_id="case:1",
            expected_ids={"m1", "m2"},
            recalled_ids={"m1", "m2"},
        )
    ]

    result = MemoryRegressionBenchmark().evaluate(cases)

    assert result.status == BenchmarkStatus.PASS
    assert result.recall == 1.0
    assert result.precision == 1.0


def test_memory_regression_fails_missing_expected_memory() -> None:
    cases = [
        MemoryBenchmarkCase(
            case_id="case:1",
            expected_ids={"m1", "m2"},
            recalled_ids={"m1"},
        )
    ]

    result = MemoryRegressionBenchmark().evaluate(cases)

    assert result.status == BenchmarkStatus.FAIL
    assert result.failed_case_ids == ["case:1"]
