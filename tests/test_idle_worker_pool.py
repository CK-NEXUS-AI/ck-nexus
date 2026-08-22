from __future__ import annotations

from creator_app.ai_team.idle_worker_pool import (
    IdleWorkPolicy,
    NotificationEvent,
    NotificationFilter,
    TruthClass,
    WorkerProfile,
    WorkItem,
    WorkPriority,
    WorkState,
)


def _item(**overrides: object) -> WorkItem:
    values: dict[str, object] = {
        "work_id": "work-001",
        "subject_sha": "a" * 40,
        "category": "runtime_bug",
        "priority": WorkPriority.P1,
        "required_capabilities": frozenset({"runtime", "python"}),
        "objective": "Inspect and prepare a bounded development fix.",
    }
    values.update(overrides)
    return WorkItem(**values)


def test_priority_prefers_security_before_research_with_same_priority() -> None:
    research = _item(work_id="research", category="research")
    security = _item(work_id="security", category="security_governance")

    selected = IdleWorkPolicy.select_next((research, security))

    assert selected is security


def test_p0_always_precedes_lower_priority_category() -> None:
    docs = _item(
        work_id="docs",
        category="documentation_drift",
        priority=WorkPriority.P0,
    )
    security = _item(
        work_id="security",
        category="security_governance",
        priority=WorkPriority.P1,
    )

    assert IdleWorkPolicy.select_next((security, docs)) is docs


def test_dispatch_routes_to_idle_capability_match() -> None:
    workers = (
        WorkerProfile("chat-b", frozenset({"ui", "windows"})),
        WorkerProfile("chat-a", frozenset({"runtime", "python", "api"})),
    )

    decision = IdleWorkPolicy.dispatch(_item(), workers)

    assert decision.accepted is True
    assert decision.worker_id == "chat-a"


def test_dispatch_rejects_busy_or_incapable_workers() -> None:
    workers = (
        WorkerProfile("chat-a", frozenset({"runtime", "python"}), idle=False),
        WorkerProfile("chat-b", frozenset({"ui", "windows"})),
    )

    decision = IdleWorkPolicy.dispatch(_item(), workers)

    assert decision.accepted is False
    assert decision.reasons == ("no_idle_capability_match",)


def test_worker_pool_cannot_delegate_production_mutation() -> None:
    item = _item(production_mutation=True)
    worker = WorkerProfile("chat-a", frozenset({"runtime", "python"}))

    decision = IdleWorkPolicy.dispatch(item, (worker,))

    assert decision.accepted is False
    assert "production_mutation_not_delegable" in decision.reasons


def test_worker_pool_cannot_delegate_credential_access() -> None:
    item = _item(credential_access=True)
    worker = WorkerProfile("chat-a", frozenset({"runtime", "python"}))

    decision = IdleWorkPolicy.dispatch(item, (worker,))

    assert decision.accepted is False
    assert "credential_access_not_delegable" in decision.reasons


def test_worker_with_authority_flags_is_not_eligible() -> None:
    workers = (
        WorkerProfile(
            "unsafe",
            frozenset({"runtime", "python"}),
            production_authority=True,
        ),
    )

    decision = IdleWorkPolicy.dispatch(_item(), workers)

    assert decision.accepted is False
    assert decision.reasons == ("no_idle_capability_match",)


def test_stale_subject_never_completes() -> None:
    decision = IdleWorkPolicy.reconcile_completion(
        _item(),
        worker_id="chat-a",
        current_subject_sha="b" * 40,
        evidence=("run:123",),
        independent_verified=True,
    )

    assert decision.accepted is False
    assert decision.state is WorkState.BLOCKED
    assert decision.truth_class is TruthClass.STALE
    assert decision.reasons == ("stale_subject",)


def test_missing_evidence_keeps_work_in_verification() -> None:
    decision = IdleWorkPolicy.reconcile_completion(
        _item(),
        worker_id="chat-a",
        current_subject_sha="a" * 40,
        evidence=(),
        independent_verified=True,
    )

    assert decision.accepted is False
    assert decision.state is WorkState.VERIFYING
    assert decision.truth_class is TruthClass.NOT_VERIFIED


def test_worker_cannot_self_promote_without_independent_verification() -> None:
    decision = IdleWorkPolicy.reconcile_completion(
        _item(),
        worker_id="chat-a",
        current_subject_sha="a" * 40,
        evidence=("run:123",),
        independent_verified=False,
    )

    assert decision.accepted is False
    assert decision.state is WorkState.VERIFYING
    assert decision.reasons == ("independent_verification_required",)


def test_verified_evidence_can_complete_development_work() -> None:
    decision = IdleWorkPolicy.reconcile_completion(
        _item(),
        worker_id="chat-a",
        current_subject_sha="a" * 40,
        evidence=("run:123", "security:456"),
        independent_verified=True,
    )

    assert decision.accepted is True
    assert decision.state is WorkState.COMPLETE
    assert decision.truth_class is TruthClass.VERIFIED


def test_notification_filter_suppresses_low_value_chatter() -> None:
    event = NotificationEvent(
        priority=WorkPriority.P3,
        event_type="HEARTBEAT",
        state_changed=False,
    )

    assert NotificationFilter.should_notify(event) is False


def test_notification_filter_surfaces_security_and_human_approval() -> None:
    security = NotificationEvent(
        priority=WorkPriority.P3,
        event_type="SECURITY_FINDING",
        security_finding=True,
    )
    approval = NotificationEvent(
        priority=WorkPriority.P2,
        event_type="BLOCKER",
        human_approval_required=True,
    )

    assert NotificationFilter.should_notify(security) is True
    assert NotificationFilter.should_notify(approval) is True
