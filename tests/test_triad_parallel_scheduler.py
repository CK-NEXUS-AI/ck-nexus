from creator_app.cognitive_runtime.triad_scheduler import (
    Priority,
    TriadParallelScheduler,
    TriadRole,
    WorkItem,
)

SUBJECT = "5539491ec5bb9ae3d8c6aff83d4631e3c2ce63e3"


def item(work_id: str, capability: str, priority: Priority = Priority.P2, **kwargs) -> WorkItem:
    return WorkItem(work_id=work_id, capability=capability, priority=priority, **kwargs)


def test_scheduler_prefers_higher_priority_and_unblock_gain() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=2)
    plan = scheduler.plan(
        (
            item("p2", "cap-p2", Priority.P2, unblock_gain=2),
            item("p0-low", "cap-p0-low", Priority.P0),
            item("p0-high", "cap-p0-high", Priority.P0, unblock_gain=4),
        )
    )
    assert [assignment.work_id for assignment in plan.assignments] == ["p0-high", "p0-low"]


def test_scheduler_never_fabricates_to_reach_minimum() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=5, max_streams=9)
    plan = scheduler.plan((item("one", "only-capability"),))
    assert len(plan.assignments) == 1
    assert plan.underfilled is True


def test_scheduler_blocks_secret_paid_external_and_production_work() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=9)
    plan = scheduler.plan(
        (
            item("secret", "secret-cap", secret_required=True),
            item("paid", "paid-cap", paid_or_unknown_cost=True),
            item("write", "write-cap", external_write=True),
            item("prod", "prod-cap", production_mutation=True),
            item("safe", "safe-cap"),
        )
    )
    assert [assignment.work_id for assignment in plan.assignments] == ["safe"]
    assert set(plan.blocked_work_ids) == {"secret", "paid", "write", "prod"}


def test_scheduler_honors_dependencies_and_completed_capabilities() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=9)
    plan = scheduler.plan(
        (
            item("blocked", "cap-b", dependencies=("event-bus",)),
            item("done", "state-projector"),
            item("ready", "cap-c", dependencies=("state-projector",)),
        ),
        completed_capabilities=frozenset({"state-projector"}),
    )
    assert [assignment.work_id for assignment in plan.assignments] == ["ready"]
    assert "blocked" in plan.blocked_work_ids
    assert "done" in plan.deferred_work_ids


def test_best_duplicate_capability_candidate_wins_regardless_of_input_order() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=9)
    plan = scheduler.plan(
        (
            item("lower", "same-cap", Priority.P1),
            item("higher", "same-cap", Priority.P1, evidence_gain=3, unblock_gain=2),
        )
    )
    assert len(plan.assignments) == 1
    assert plan.assignments[0].work_id == "higher"
    assert plan.deferred_work_ids == ("lower",)


def test_active_capability_prevents_duplicate_workstream() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=9)
    plan = scheduler.plan(
        (item("candidate", "already-active"),),
        active_capabilities=frozenset({"already-active"}),
    )
    assert plan.assignments == ()
    assert plan.deferred_work_ids == ("candidate",)


def test_triad_roles_are_separated_and_cannot_self_verify() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=9)
    plan = scheduler.plan((item("triad", "parallel-reasoning"),))
    assignment = plan.assignments[0]
    assert assignment.roles == (
        TriadRole.BUILDER,
        TriadRole.CRITIC,
        TriadRole.EVIDENCE_EVALUATOR,
    )
    assert assignment.verification_ceiling == "MEASURED_NOT_VERIFIED"


def test_plan_digest_is_deterministic() -> None:
    scheduler = TriadParallelScheduler(SUBJECT, min_streams=1, max_streams=9)
    work = (
        item("a", "cap-a", Priority.P1, reliability_gain=2),
        item("b", "cap-b", Priority.P2, evidence_gain=4),
    )
    assert scheduler.plan(work).plan_digest == scheduler.plan(work).plan_digest
