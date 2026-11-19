"""Canonical contracts for the Universal Command Intake & Execution Protocol."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class TaskType(StrEnum):
    QUESTION = "QUESTION"
    RESEARCH = "RESEARCH"
    CODE_CHANGE = "CODE_CHANGE"
    BUG_FIX = "BUG_FIX"
    ARCHITECTURE = "ARCHITECTURE"
    SECURITY = "SECURITY"
    FILE_MANAGEMENT = "FILE_MANAGEMENT"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    DEPLOYMENT = "DEPLOYMENT"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    DATA_CHANGE = "DATA_CHANGE"
    PRODUCTION = "PRODUCTION"
    EVIDENCE = "EVIDENCE"
    PURCHASE = "PURCHASE"
    LEGAL_FINANCIAL = "LEGAL_FINANCIAL"


class RiskLevel(IntEnum):
    R0_READ_ONLY = 0
    R1_SAFE_REVERSIBLE = 1
    R2_MUTABLE_REVERSIBLE = 2
    R3_HIGH_IMPACT = 3
    R4_CRITICAL = 4


class IntensityLevel(IntEnum):
    L0_MINIMAL = 0
    L1_STANDARD = 1
    L2_COMPLEX = 2
    L3_HIGH_IMPACT = 3


class ReuseDecision(StrEnum):
    REUSE = "REUSE"
    EXTEND = "EXTEND"
    REPAIR = "REPAIR"
    REPLACE = "REPLACE"
    MERGE = "MERGE"
    ARCHIVE = "ARCHIVE"
    DO_NOT_USE = "DO_NOT_USE"
    NEW_IMPLEMENTATION_REQUIRED = "NEW_IMPLEMENTATION_REQUIRED"


class TruthState(StrEnum):
    DISCOVERED = "DISCOVERED"
    PLANNED = "PLANNED"
    EXECUTED = "EXECUTED"
    MEASURED = "MEASURED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MEASURED_NOT_VERIFIED = "MEASURED_NOT_VERIFIED"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class ProtocolStep(IntEnum):
    INTENT_UNDERSTANDING = 1
    TASK_CLASSIFICATION = 2
    RISK_CLASSIFICATION = 3
    AUTHORITY_CHECK = 4
    RECALL_PREVIOUS_WORK = 5
    SEARCH_EXISTING_IMPLEMENTATION = 6
    SEARCH_ISSUES_PRS_BRANCHES = 7
    REUSE_DEDUP_DECISION = 8
    FRESHNESS_CHECK = 9
    SEARCH_OFFICIAL_SOURCES = 10
    MULTI_QUERY_EXPANSION = 11
    MULTI_LANGUAGE_SEARCH = 12
    KNOWLEDGE_GAP_DETECTION = 13
    COVERAGE_CHECK = 14
    EVIDENCE_INDEPENDENCE_CHECK = 15
    CONTRADICTION_DETECTION = 16
    GENERATE_ALTERNATIVES = 17
    INDEPENDENT_SPECIALIST_THINKING = 18
    COMPARE_ALTERNATIVES = 19
    EXECUTION_PLAN = 20
    SUCCESS_CRITERIA = 21
    BASELINE_MEASUREMENT = 22
    EVIDENCE_PLAN = 23
    ROLLBACK_PLAN = 24
    ISOLATION_PLAN = 25
    TOOL_SELECTION = 26
    ASSISTANT_ROUTING = 27
    SMALLEST_REVERSIBLE_CHANGE = 28
    OBSERVE_EVERY_STEP = 29
    STUCK_DETECTOR = 30
    RESEARCH_AGAIN_ON_STUCK = 31
    FUNCTIONAL_TEST = 32
    REGRESSION_TEST = 33
    SECURITY_REVIEW = 34
    PERFORMANCE_RESOURCE_CHECK = 35
    INDEPENDENT_CRITIC = 36
    HUMAN_REVIEW = 37
    TRUTHFUL_STATUS = 38
    EVIDENCE_BINDING = 39
    SAVE_PROBLEM_RECORD = 40
    SAVE_ATTEMPTS = 41
    SAVE_SOLUTION = 42
    SAVE_NEW_KNOWLEDGE = 43
    UPDATE_TOOL_KNOWLEDGE = 44
    UPDATE_QUEUE = 45
    COMPLETION_CHECK = 46
    REPORT_DELTA = 47


@dataclass(frozen=True, slots=True)
class CommandRequest:
    text: str
    environment: str = "development"
    explicit_task_type: TaskType | None = None
    explicit_risk: RiskLevel | None = None
    current_information_required: bool | None = None
    mutates_state: bool = False
    external_action: bool = False
    destructive: bool = False
    touches_credentials: bool = False
    money_or_purchase: bool = False
    affects_production: bool = False
    affects_security_authority: bool = False
    affects_q_gates: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("command text is required")
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("unsupported environment")


@dataclass(frozen=True, slots=True)
class AuthorityDecision:
    automated_execution_allowed: bool
    human_approval_required: bool
    production_effect: bool
    q_gate_effect: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProtocolPlan:
    task_type: TaskType
    risk: RiskLevel
    intensity: IntensityLevel
    authority: AuthorityDecision
    required_steps: tuple[ProtocolStep, ...]
    search_required: bool
    alternatives_required: bool
    baseline_required: bool
    rollback_required: bool
    isolation_required: bool
    independent_review_required: bool
    human_review_required: bool

    @property
    def pre_execution_steps(self) -> tuple[ProtocolStep, ...]:
        return tuple(step for step in self.required_steps if step.value <= 27)

    @property
    def post_execution_steps(self) -> tuple[ProtocolStep, ...]:
        return tuple(step for step in self.required_steps if step.value >= 28)


@dataclass(frozen=True, slots=True)
class PreExecutionState:
    completed_steps: frozenset[ProtocolStep]
    reuse_decision: ReuseDecision | None = None
    alternatives_count: int = 0
    rollback_ready: bool = False
    isolation_ready: bool = False
    evidence_plan_ready: bool = False
    human_approval_granted: bool = False


@dataclass(frozen=True, slots=True)
class CompletionState:
    completed_steps: frozenset[ProtocolStep]
    worker_id: str
    independent_reviewer_id: str | None = None
    human_reviewer_id: str | None = None
    exact_evidence_bound: bool = False
    external_verification_confirmed: bool = False
    blocked: bool = False
    failed: bool = False


@dataclass(frozen=True, slots=True)
class ProtocolGateResult:
    allowed: bool
    code: str
    missing_steps: tuple[ProtocolStep, ...] = ()
    reasons: tuple[str, ...] = ()
    truth_state: TruthState = TruthState.PLANNED
