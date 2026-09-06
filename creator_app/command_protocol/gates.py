"""Fail-closed pre-execution and completion gates for the universal protocol."""

from __future__ import annotations

from .models import (
    CompletionState,
    IntensityLevel,
    PreExecutionState,
    ProtocolGateResult,
    ProtocolPlan,
    ProtocolStep,
    ReuseDecision,
    TruthState,
)


def evaluate_pre_execution(
    plan: ProtocolPlan,
    state: PreExecutionState,
) -> ProtocolGateResult:
    required = set(plan.pre_execution_steps)
    missing = sorted(required - set(state.completed_steps), key=int)
    reasons: list[str] = []

    if state.reuse_decision is None and ProtocolStep.REUSE_DEDUP_DECISION in required:
        reasons.append("reuse_dedup_decision_missing")
        if ProtocolStep.REUSE_DEDUP_DECISION not in missing:
            missing.append(ProtocolStep.REUSE_DEDUP_DECISION)

    if (
        state.reuse_decision is ReuseDecision.NEW_IMPLEMENTATION_REQUIRED
        and ProtocolStep.SEARCH_EXISTING_IMPLEMENTATION not in state.completed_steps
    ):
        reasons.append("new_implementation_without_existing_search")
        if ProtocolStep.SEARCH_EXISTING_IMPLEMENTATION not in missing:
            missing.append(ProtocolStep.SEARCH_EXISTING_IMPLEMENTATION)

    if plan.alternatives_required and state.alternatives_count < 3:
        reasons.append("fewer_than_three_alternatives")
        if ProtocolStep.GENERATE_ALTERNATIVES not in missing:
            missing.append(ProtocolStep.GENERATE_ALTERNATIVES)

    if plan.baseline_required and ProtocolStep.BASELINE_MEASUREMENT not in state.completed_steps:
        reasons.append("baseline_missing")

    if plan.rollback_required and not state.rollback_ready:
        reasons.append("rollback_not_ready")
        if ProtocolStep.ROLLBACK_PLAN not in missing:
            missing.append(ProtocolStep.ROLLBACK_PLAN)

    if plan.isolation_required and not state.isolation_ready:
        reasons.append("isolation_not_ready")
        if ProtocolStep.ISOLATION_PLAN not in missing:
            missing.append(ProtocolStep.ISOLATION_PLAN)

    if plan.intensity >= IntensityLevel.L2_COMPLEX and not state.evidence_plan_ready:
        reasons.append("evidence_plan_not_ready")
        if ProtocolStep.EVIDENCE_PLAN not in missing:
            missing.append(ProtocolStep.EVIDENCE_PLAN)

    if plan.authority.human_approval_required and not state.human_approval_granted:
        reasons.append("human_approval_required")

    missing = sorted(set(missing), key=int)
    allowed = not missing and not reasons

    if not allowed:
        return ProtocolGateResult(
            allowed=False,
            code="PRE_EXECUTION_BLOCKED",
            missing_steps=tuple(missing),
            reasons=tuple(reasons),
            truth_state=TruthState.BLOCKED,
        )

    return ProtocolGateResult(
        allowed=True,
        code="PRE_EXECUTION_READY",
        truth_state=TruthState.PLANNED,
    )


def evaluate_completion(
    plan: ProtocolPlan,
    state: CompletionState,
) -> ProtocolGateResult:
    if state.failed:
        return ProtocolGateResult(
            allowed=False,
            code="EXECUTION_FAILED",
            truth_state=TruthState.FAILED,
        )
    if state.blocked:
        return ProtocolGateResult(
            allowed=False,
            code="EXECUTION_BLOCKED",
            truth_state=TruthState.BLOCKED,
        )

    required = set(plan.post_execution_steps)
    missing = sorted(required - set(state.completed_steps), key=int)
    reasons: list[str] = []

    if plan.independent_review_required:
        if not state.independent_reviewer_id:
            reasons.append("independent_reviewer_missing")
        elif state.independent_reviewer_id == state.worker_id:
            reasons.append("worker_cannot_approve_itself")

    if plan.human_review_required and not state.human_reviewer_id:
        reasons.append("human_review_missing")

    if ProtocolStep.EVIDENCE_BINDING in required and not state.exact_evidence_bound:
        reasons.append("exact_evidence_binding_missing")

    if missing or reasons:
        return ProtocolGateResult(
            allowed=False,
            code="COMPLETION_REVIEW_REQUIRED",
            missing_steps=tuple(missing),
            reasons=tuple(reasons),
            truth_state=TruthState.REVIEW_REQUIRED,
        )

    if state.external_verification_confirmed:
        return ProtocolGateResult(
            allowed=True,
            code="COMPLETION_VERIFIED",
            truth_state=TruthState.VERIFIED,
        )

    if plan.intensity >= IntensityLevel.L2_COMPLEX:
        return ProtocolGateResult(
            allowed=True,
            code="COMPLETION_MEASURED_NOT_VERIFIED",
            reasons=("external_verification_not_confirmed",),
            truth_state=TruthState.MEASURED_NOT_VERIFIED,
        )

    return ProtocolGateResult(
        allowed=True,
        code="COMPLETION_MEASURED",
        truth_state=TruthState.MEASURED,
    )
