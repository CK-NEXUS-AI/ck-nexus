import pytest

from creator_app.agnes.cognitive import (
    BlackboardEntryType,
    CognitiveBlackboard,
    ExecutionPrimitive,
    FeedbackController,
    FeedbackObservation,
    FeedbackSignal,
    IntelligenceNeed,
    MetaReasoner,
    ProgressIntelligence,
    ProgressState,
    TaskProfile,
    default_capability_registry,
)


def test_registry_contains_all_40_capability_families() -> None:
    registry = default_capability_registry()
    assert len(registry.all()) == 40
    assert all(item.requires_governor for item in registry.all())


def test_blackboard_is_append_only_and_digest_backed() -> None:
    blackboard = CognitiveBlackboard()
    first = blackboard.append(
        entry_type=BlackboardEntryType.CLAIM,
        author="research-agent",
        content="A testable claim",
        correlation_id="run-1",
    )
    second = blackboard.append(
        entry_type=BlackboardEntryType.EVIDENCE,
        author="verifier",
        content="Evidence for the claim",
        correlation_id="run-1",
        causation_id=first.entry_id,
        evidence_refs=("evd-1",),
    )

    snapshot = blackboard.snapshot()
    assert snapshot == (first, second)
    assert len(first.content_digest) == 64
    assert blackboard.latest(BlackboardEntryType.EVIDENCE) == second


def test_progress_requires_verification_before_success() -> None:
    progress = ProgressIntelligence()
    progress.transition(ProgressState.UNDERSTANDING, "goal parsed")
    progress.transition(ProgressState.PLANNING, "bounded plan created")
    progress.transition(ProgressState.EXECUTING, "execution started")

    with pytest.raises(ValueError, match="invalid progress transition"):
        progress.transition(ProgressState.SUCCESS, "agent claims success")

    progress.transition(ProgressState.VERIFYING, "independent verification started")
    progress.transition(ProgressState.SUCCESS, "verification passed")
    assert progress.terminal is True


def test_meta_reasoner_prefers_bounded_workflow_over_agent() -> None:
    reasoner = MetaReasoner(default_capability_registry())
    plan = reasoner.compose(
        TaskProfile(
            goal="Reconcile deterministic evidence records",
            needs=frozenset({IntelligenceNeed.DETERMINISTIC}),
            deterministic_path_available=True,
        )
    )
    assert plan.primitive is ExecutionPrimitive.WORKFLOW
    assert plan.requires_human_approval is False


def test_meta_reasoner_escalates_high_risk_external_action() -> None:
    reasoner = MetaReasoner(default_capability_registry())
    plan = reasoner.compose(
        TaskProfile(
            goal="Change a production control",
            needs=frozenset({IntelligenceNeed.HIGH_RISK, IntelligenceNeed.OPEN_ENDED}),
            requires_external_action=True,
        )
    )
    assert plan.primitive is ExecutionPrimitive.HUMAN
    assert plan.requires_governor is True
    assert plan.requires_human_approval is True
    assert plan.requires_verification is True


def test_feedback_controller_requests_human_for_high_risk_deviation() -> None:
    controller = FeedbackController()
    decision = controller.evaluate(
        FeedbackObservation(
            goal_metric=100.0,
            observed_metric=70.0,
            tolerance=5.0,
            risk="critical",
        )
    )
    assert decision.signal is FeedbackSignal.ASK_HUMAN
    assert decision.error == 30.0
