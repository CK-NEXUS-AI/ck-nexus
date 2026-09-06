"""Deterministic planning for the Universal Command Intake & Execution Protocol."""

from __future__ import annotations

import re

from .models import (
    AuthorityDecision,
    CommandRequest,
    IntensityLevel,
    ProtocolPlan,
    ProtocolStep,
    RiskLevel,
    TaskType,
)

_TOKEN = re.compile(r"[a-z0-9_+#.-]+|[\u0E00-\u0E7F]+", re.I)

_TASK_KEYWORDS: tuple[tuple[TaskType, frozenset[str]], ...] = (
    (
        TaskType.PURCHASE,
        frozenset({"buy", "purchase", "payment", "pay", "ซื้อ", "จ่ายเงิน"}),
    ),
    (TaskType.DEPLOYMENT, frozenset({"deploy", "deployment", "release", "ขึ้นระบบ"})),
    (TaskType.PRODUCTION, frozenset({"production", "prod", "โปรดักชัน"})),
    (
        TaskType.SECURITY,
        frozenset({"security", "vulnerability", "secret", "credential", "ความปลอดภัย"}),
    ),
    (TaskType.BUG_FIX, frozenset({"bug", "fix", "error", "failure", "แก้บั๊ก", "แก้ปัญหา"})),
    (TaskType.CODE_CHANGE, frozenset({"code", "patch", "refactor", "implement", "โค้ด", "พัฒนา"})),
    (TaskType.ARCHITECTURE, frozenset({"architecture", "design", "สถาปัตยกรรม", "ออกแบบระบบ"})),
    (
        TaskType.RESEARCH,
        frozenset({"research", "search", "compare", "ค้นหา", "วิจัย", "เปรียบเทียบ"}),
    ),
    (TaskType.FILE_MANAGEMENT, frozenset({"file", "folder", "archive", "ไฟล์", "โฟลเดอร์"})),
    (
        TaskType.INFRASTRUCTURE,
        frozenset({"vps", "docker", "server", "infra", "infrastructure", "เซิร์ฟเวอร์"}),
    ),
    (TaskType.DATA_CHANGE, frozenset({"database", "data", "migration", "ข้อมูล", "ฐานข้อมูล"})),
    (TaskType.EVIDENCE, frozenset({"evidence", "audit", "หลักฐาน", "ตรวจสอบ"})),
    (TaskType.LEGAL_FINANCIAL, frozenset({"legal", "financial", "finance", "กฎหมาย", "การเงิน"})),
)

_CURRENT_INFO_HINTS = frozenset(
    {
        "latest",
        "current",
        "today",
        "release",
        "version",
        "upstream",
        "ล่าสุด",
        "ปัจจุบัน",
        "วันนี้",
        "เวอร์ชัน",
    }
)


def build_protocol_plan(request: CommandRequest) -> ProtocolPlan:
    task_type = _classify_task(request)
    risk = _classify_risk(request, task_type)
    intensity = _select_intensity(task_type, risk)
    authority = _authority_decision(request, risk)
    search_required = _search_required(request, task_type, intensity)
    alternatives_required = intensity >= IntensityLevel.L2_COMPLEX
    mutable = request.mutates_state or task_type in {
        TaskType.CODE_CHANGE,
        TaskType.BUG_FIX,
        TaskType.FILE_MANAGEMENT,
        TaskType.DATA_CHANGE,
        TaskType.INFRASTRUCTURE,
        TaskType.DEPLOYMENT,
        TaskType.PRODUCTION,
    }
    baseline_required = intensity >= IntensityLevel.L2_COMPLEX or mutable
    rollback_required = risk >= RiskLevel.R2_MUTABLE_REVERSIBLE or mutable
    isolation_required = task_type in {
        TaskType.CODE_CHANGE,
        TaskType.BUG_FIX,
        TaskType.INFRASTRUCTURE,
        TaskType.DEPLOYMENT,
        TaskType.PRODUCTION,
        TaskType.DATA_CHANGE,
    }
    independent_review_required = intensity >= IntensityLevel.L2_COMPLEX
    human_review_required = (
        authority.human_approval_required
        or intensity >= IntensityLevel.L3_HIGH_IMPACT
    )

    required_steps = _required_steps(
        intensity=intensity,
        search_required=search_required,
        alternatives_required=alternatives_required,
        baseline_required=baseline_required,
        rollback_required=rollback_required,
        isolation_required=isolation_required,
        independent_review_required=independent_review_required,
        human_review_required=human_review_required,
    )

    return ProtocolPlan(
        task_type=task_type,
        risk=risk,
        intensity=intensity,
        authority=authority,
        required_steps=required_steps,
        search_required=search_required,
        alternatives_required=alternatives_required,
        baseline_required=baseline_required,
        rollback_required=rollback_required,
        isolation_required=isolation_required,
        independent_review_required=independent_review_required,
        human_review_required=human_review_required,
    )


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(text)}


def _classify_task(request: CommandRequest) -> TaskType:
    if request.explicit_task_type is not None:
        return request.explicit_task_type

    tokens = _tokens(request.text)
    for task_type, keywords in _TASK_KEYWORDS:
        if tokens & keywords:
            return task_type

    if request.external_action:
        return TaskType.EXTERNAL_ACTION
    return TaskType.QUESTION


def _classify_risk(request: CommandRequest, task_type: TaskType) -> RiskLevel:
    inferred = RiskLevel.R0_READ_ONLY

    if task_type in {TaskType.ARCHITECTURE, TaskType.RESEARCH, TaskType.EVIDENCE}:
        inferred = max(inferred, RiskLevel.R1_SAFE_REVERSIBLE)

    if task_type in {
        TaskType.CODE_CHANGE,
        TaskType.BUG_FIX,
        TaskType.FILE_MANAGEMENT,
        TaskType.DATA_CHANGE,
    }:
        inferred = max(inferred, RiskLevel.R2_MUTABLE_REVERSIBLE)

    if task_type in {TaskType.SECURITY, TaskType.INFRASTRUCTURE, TaskType.EXTERNAL_ACTION}:
        inferred = max(inferred, RiskLevel.R3_HIGH_IMPACT)

    if task_type in {
        TaskType.DEPLOYMENT,
        TaskType.PRODUCTION,
        TaskType.PURCHASE,
        TaskType.LEGAL_FINANCIAL,
    }:
        inferred = RiskLevel.R4_CRITICAL

    if request.mutates_state:
        inferred = max(inferred, RiskLevel.R2_MUTABLE_REVERSIBLE)
    if request.external_action:
        inferred = max(inferred, RiskLevel.R3_HIGH_IMPACT)
    if (
        request.destructive
        or request.touches_credentials
        or request.money_or_purchase
        or request.affects_production
        or request.affects_security_authority
        or request.affects_q_gates
        or request.environment == "production"
    ):
        inferred = RiskLevel.R4_CRITICAL

    if request.explicit_risk is not None:
        inferred = max(inferred, request.explicit_risk)

    return inferred


def _select_intensity(task_type: TaskType, risk: RiskLevel) -> IntensityLevel:
    if risk >= RiskLevel.R3_HIGH_IMPACT:
        return IntensityLevel.L3_HIGH_IMPACT
    if task_type is TaskType.QUESTION and risk is RiskLevel.R0_READ_ONLY:
        return IntensityLevel.L0_MINIMAL
    if task_type in {
        TaskType.RESEARCH,
        TaskType.CODE_CHANGE,
        TaskType.BUG_FIX,
        TaskType.ARCHITECTURE,
        TaskType.SECURITY,
        TaskType.INFRASTRUCTURE,
        TaskType.EVIDENCE,
    }:
        return IntensityLevel.L2_COMPLEX
    return IntensityLevel.L1_STANDARD


def _authority_decision(request: CommandRequest, risk: RiskLevel) -> AuthorityDecision:
    reasons: list[str] = []
    human_required = risk >= RiskLevel.R4_CRITICAL

    if request.environment == "production":
        reasons.append("production_environment")
        human_required = True
    if request.touches_credentials:
        reasons.append("credential_scope")
        human_required = True
    if request.money_or_purchase:
        reasons.append("money_or_purchase")
        human_required = True
    if request.affects_security_authority:
        reasons.append("security_authority")
        human_required = True
    if request.affects_q_gates:
        reasons.append("q_gate_effect")
        human_required = True
    if request.destructive:
        reasons.append("destructive_action")
        human_required = True

    return AuthorityDecision(
        automated_execution_allowed=risk <= RiskLevel.R2_MUTABLE_REVERSIBLE,
        human_approval_required=human_required,
        production_effect=request.affects_production or request.environment == "production",
        q_gate_effect=request.affects_q_gates,
        reasons=tuple(reasons),
    )


def _search_required(
    request: CommandRequest,
    task_type: TaskType,
    intensity: IntensityLevel,
) -> bool:
    if request.current_information_required is not None:
        return request.current_information_required
    if _tokens(request.text) & _CURRENT_INFO_HINTS:
        return True
    return intensity >= IntensityLevel.L2_COMPLEX and task_type is not TaskType.QUESTION


def _required_steps(
    *,
    intensity: IntensityLevel,
    search_required: bool,
    alternatives_required: bool,
    baseline_required: bool,
    rollback_required: bool,
    isolation_required: bool,
    independent_review_required: bool,
    human_review_required: bool,
) -> tuple[ProtocolStep, ...]:
    required: set[ProtocolStep] = {
        ProtocolStep.INTENT_UNDERSTANDING,
        ProtocolStep.TASK_CLASSIFICATION,
        ProtocolStep.RISK_CLASSIFICATION,
        ProtocolStep.AUTHORITY_CHECK,
        ProtocolStep.COMPLETION_CHECK,
        ProtocolStep.REPORT_DELTA,
    }

    if intensity >= IntensityLevel.L1_STANDARD:
        required.update(
            {
                ProtocolStep.RECALL_PREVIOUS_WORK,
                ProtocolStep.SEARCH_EXISTING_IMPLEMENTATION,
                ProtocolStep.SEARCH_ISSUES_PRS_BRANCHES,
                ProtocolStep.REUSE_DEDUP_DECISION,
                ProtocolStep.EXECUTION_PLAN,
                ProtocolStep.SUCCESS_CRITERIA,
                ProtocolStep.TOOL_SELECTION,
                ProtocolStep.ASSISTANT_ROUTING,
                ProtocolStep.SMALLEST_REVERSIBLE_CHANGE,
                ProtocolStep.OBSERVE_EVERY_STEP,
                ProtocolStep.FUNCTIONAL_TEST,
                ProtocolStep.TRUTHFUL_STATUS,
                ProtocolStep.UPDATE_QUEUE,
            }
        )

    if search_required:
        required.update(
            {
                ProtocolStep.FRESHNESS_CHECK,
                ProtocolStep.SEARCH_OFFICIAL_SOURCES,
                ProtocolStep.MULTI_QUERY_EXPANSION,
                ProtocolStep.MULTI_LANGUAGE_SEARCH,
                ProtocolStep.KNOWLEDGE_GAP_DETECTION,
                ProtocolStep.COVERAGE_CHECK,
                ProtocolStep.EVIDENCE_INDEPENDENCE_CHECK,
                ProtocolStep.CONTRADICTION_DETECTION,
            }
        )

    if alternatives_required:
        required.update(
            {
                ProtocolStep.GENERATE_ALTERNATIVES,
                ProtocolStep.INDEPENDENT_SPECIALIST_THINKING,
                ProtocolStep.COMPARE_ALTERNATIVES,
                ProtocolStep.STUCK_DETECTOR,
                ProtocolStep.RESEARCH_AGAIN_ON_STUCK,
                ProtocolStep.REGRESSION_TEST,
                ProtocolStep.SECURITY_REVIEW,
                ProtocolStep.PERFORMANCE_RESOURCE_CHECK,
                ProtocolStep.EVIDENCE_BINDING,
                ProtocolStep.SAVE_PROBLEM_RECORD,
                ProtocolStep.SAVE_ATTEMPTS,
                ProtocolStep.SAVE_SOLUTION,
                ProtocolStep.SAVE_NEW_KNOWLEDGE,
                ProtocolStep.UPDATE_TOOL_KNOWLEDGE,
            }
        )

    if baseline_required:
        required.add(ProtocolStep.BASELINE_MEASUREMENT)

    if intensity >= IntensityLevel.L2_COMPLEX:
        required.add(ProtocolStep.EVIDENCE_PLAN)

    if rollback_required:
        required.add(ProtocolStep.ROLLBACK_PLAN)

    if isolation_required:
        required.add(ProtocolStep.ISOLATION_PLAN)

    if independent_review_required:
        required.add(ProtocolStep.INDEPENDENT_CRITIC)

    if human_review_required:
        required.add(ProtocolStep.HUMAN_REVIEW)

    return tuple(sorted(required, key=int))
