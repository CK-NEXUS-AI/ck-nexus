from creator_app.command_protocol import (
    CommandRequest,
    CompletionState,
    IntensityLevel,
    PreExecutionState,
    ProtocolStep,
    ReuseDecision,
    RiskLevel,
    TaskType,
    TruthState,
    build_protocol_plan,
    evaluate_completion,
    evaluate_pre_execution,
)


def test_simple_read_only_question_uses_l0() -> None:
    plan = build_protocol_plan(CommandRequest(text="what is this file name?"))

    assert plan.task_type is TaskType.QUESTION
    assert plan.risk is RiskLevel.R0_READ_ONLY
    assert plan.intensity is IntensityLevel.L0_MINIMAL
    assert plan.search_required is False
    assert ProtocolStep.INTENT_UNDERSTANDING in plan.required_steps
    assert ProtocolStep.GENERATE_ALTERNATIVES not in plan.required_steps


def test_complex_bug_fix_requires_search_reuse_and_reversible_controls() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="fix this CI failure and check the latest upstream issue",
            mutates_state=True,
        )
    )

    assert plan.task_type is TaskType.BUG_FIX
    assert plan.risk is RiskLevel.R2_MUTABLE_REVERSIBLE
    assert plan.intensity is IntensityLevel.L2_COMPLEX
    assert plan.search_required is True
    assert plan.alternatives_required is True
    assert plan.rollback_required is True
    assert plan.isolation_required is True
    assert plan.independent_review_required is True
    assert ProtocolStep.RECALL_PREVIOUS_WORK in plan.required_steps
    assert ProtocolStep.SEARCH_OFFICIAL_SOURCES in plan.required_steps
    assert ProtocolStep.GENERATE_ALTERNATIVES in plan.required_steps
    assert ProtocolStep.EVIDENCE_PLAN in plan.required_steps


def test_production_deployment_is_l3_and_requires_human_approval() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="deploy this release to production",
            environment="production",
            external_action=True,
            mutates_state=True,
            affects_production=True,
        )
    )

    assert plan.risk is RiskLevel.R4_CRITICAL
    assert plan.intensity is IntensityLevel.L3_HIGH_IMPACT
    assert plan.authority.automated_execution_allowed is False
    assert plan.authority.human_approval_required is True
    assert plan.human_review_required is True
    assert ProtocolStep.HUMAN_REVIEW in plan.required_steps


def test_explicit_risk_cannot_lower_inferred_risk() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="production change",
            environment="production",
            explicit_risk=RiskLevel.R0_READ_ONLY,
        )
    )

    assert plan.risk is RiskLevel.R4_CRITICAL


def test_pre_execution_blocks_new_implementation_without_search() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="implement a new code path",
            explicit_task_type=TaskType.CODE_CHANGE,
            mutates_state=True,
            current_information_required=True,
        )
    )
    completed = set(plan.pre_execution_steps)
    completed.discard(ProtocolStep.SEARCH_EXISTING_IMPLEMENTATION)

    result = evaluate_pre_execution(
        plan,
        PreExecutionState(
            completed_steps=frozenset(completed),
            reuse_decision=ReuseDecision.NEW_IMPLEMENTATION_REQUIRED,
            alternatives_count=3,
            rollback_ready=True,
            isolation_ready=True,
            evidence_plan_ready=True,
        ),
    )

    assert result.allowed is False
    assert result.truth_state is TruthState.BLOCKED
    assert ProtocolStep.SEARCH_EXISTING_IMPLEMENTATION in result.missing_steps
    assert "new_implementation_without_existing_search" in result.reasons


def test_pre_execution_requires_three_alternatives_for_l2() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="fix code regression",
            explicit_task_type=TaskType.BUG_FIX,
            mutates_state=True,
        )
    )

    result = evaluate_pre_execution(
        plan,
        PreExecutionState(
            completed_steps=frozenset(plan.pre_execution_steps),
            reuse_decision=ReuseDecision.REPAIR,
            alternatives_count=2,
            rollback_ready=True,
            isolation_ready=True,
            evidence_plan_ready=True,
        ),
    )

    assert result.allowed is False
    assert "fewer_than_three_alternatives" in result.reasons


def test_completion_rejects_worker_self_review() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="fix complex code bug",
            explicit_task_type=TaskType.BUG_FIX,
            mutates_state=True,
        )
    )

    result = evaluate_completion(
        plan,
        CompletionState(
            completed_steps=frozenset(plan.post_execution_steps),
            worker_id="agent-a",
            independent_reviewer_id="agent-a",
            exact_evidence_bound=True,
        ),
    )

    assert result.allowed is False
    assert result.truth_state is TruthState.REVIEW_REQUIRED
    assert "worker_cannot_approve_itself" in result.reasons


def test_l2_completion_stays_measured_not_verified_without_external_verification() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="fix complex code bug",
            explicit_task_type=TaskType.BUG_FIX,
            mutates_state=True,
        )
    )

    result = evaluate_completion(
        plan,
        CompletionState(
            completed_steps=frozenset(plan.post_execution_steps),
            worker_id="implementer",
            independent_reviewer_id="critic",
            exact_evidence_bound=True,
            external_verification_confirmed=False,
        ),
    )

    assert result.allowed is True
    assert result.truth_state is TruthState.MEASURED_NOT_VERIFIED


def test_l3_completion_requires_human_reviewer() -> None:
    plan = build_protocol_plan(
        CommandRequest(
            text="deploy production",
            environment="production",
            affects_production=True,
            mutates_state=True,
        )
    )

    result = evaluate_completion(
        plan,
        CompletionState(
            completed_steps=frozenset(plan.post_execution_steps),
            worker_id="implementer",
            independent_reviewer_id="critic",
            exact_evidence_bound=True,
            external_verification_confirmed=True,
        ),
    )

    assert result.allowed is False
    assert "human_review_missing" in result.reasons
