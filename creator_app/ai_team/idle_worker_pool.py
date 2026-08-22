from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class WorkState(str, Enum):
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    WORKING = "WORKING"
    TESTING = "TESTING"
    VERIFYING = "VERIFYING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    SUPERSEDED = "SUPERSEDED"


class TruthClass(str, Enum):
    DISCOVERED = "DISCOVERED"
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    STALE = "STALE"


class WorkPriority(IntEnum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3


@dataclass(frozen=True, slots=True)
class WorkerProfile:
    worker_id: str
    capabilities: frozenset[str]
    idle: bool = True
    production_authority: bool = False
    credential_authority: bool = False
    self_verification_authority: bool = False


@dataclass(frozen=True, slots=True)
class WorkItem:
    work_id: str
    subject_sha: str
    category: str
    priority: WorkPriority
    required_capabilities: frozenset[str]
    objective: str
    state: WorkState = WorkState.QUEUED
    truth_class: TruthClass = TruthClass.DISCOVERED
    evidence: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    requires_independent_verification: bool = True
    production_mutation: bool = False
    credential_access: bool = False


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    accepted: bool
    worker_id: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompletionDecision:
    accepted: bool
    state: WorkState
    truth_class: TruthClass
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    priority: WorkPriority
    event_type: str
    state_changed: bool = False
    security_finding: bool = False
    test_failed: bool = False
    human_approval_required: bool = False
    evidence_ready: bool = False


class IdleWorkPolicy:
    """Deterministic policy for useful idle development work.

    The policy routes only bounded development work and never grants release,
    production, credential, or self-verification authority.
    """

    CATEGORY_ORDER = {
        "security_governance": 0,
        "broken_tests": 1,
        "runtime_bug": 2,
        "evidence_gap": 3,
        "architecture_debt": 4,
        "missing_tests": 5,
        "performance": 6,
        "documentation_drift": 7,
        "research": 8,
        "optional_feature": 9,
    }

    @classmethod
    def sort_key(cls, item: WorkItem) -> tuple[int, int, str]:
        category_rank = cls.CATEGORY_ORDER.get(item.category, 99)
        return int(item.priority), category_rank, item.work_id

    @classmethod
    def select_next(cls, items: tuple[WorkItem, ...]) -> WorkItem | None:
        candidates = [item for item in items if item.state is WorkState.QUEUED]
        if not candidates:
            return None
        return min(candidates, key=cls.sort_key)

    @staticmethod
    def validate_work(item: WorkItem) -> tuple[str, ...]:
        reasons: list[str] = []
        if len(item.subject_sha) != 40:
            reasons.append("invalid_subject_sha")
        if item.production_mutation:
            reasons.append("production_mutation_not_delegable")
        if item.credential_access:
            reasons.append("credential_access_not_delegable")
        if not item.objective.strip():
            reasons.append("objective_required")
        return tuple(reasons)

    @classmethod
    def dispatch(cls, item: WorkItem, workers: tuple[WorkerProfile, ...]) -> DispatchDecision:
        reasons = cls.validate_work(item)
        if reasons:
            return DispatchDecision(False, None, reasons)
        if item.state is not WorkState.QUEUED:
            return DispatchDecision(False, None, ("work_not_queued",))

        eligible = [
            worker
            for worker in workers
            if worker.idle
            and not worker.production_authority
            and not worker.credential_authority
            and item.required_capabilities.issubset(worker.capabilities)
        ]
        if not eligible:
            return DispatchDecision(False, None, ("no_idle_capability_match",))

        selected = min(eligible, key=lambda worker: worker.worker_id)
        return DispatchDecision(True, selected.worker_id, ())

    @staticmethod
    def reconcile_completion(
        item: WorkItem,
        *,
        worker_id: str,
        current_subject_sha: str,
        evidence: tuple[str, ...],
        independent_verified: bool,
    ) -> CompletionDecision:
        if current_subject_sha != item.subject_sha:
            return CompletionDecision(
                False,
                WorkState.BLOCKED,
                TruthClass.STALE,
                ("stale_subject",),
            )
        if item.blockers:
            return CompletionDecision(
                False,
                WorkState.BLOCKED,
                TruthClass.NOT_VERIFIED,
                ("unresolved_blockers",),
            )
        if not evidence:
            return CompletionDecision(
                False,
                WorkState.VERIFYING,
                TruthClass.NOT_VERIFIED,
                ("evidence_required",),
            )
        if item.requires_independent_verification and not independent_verified:
            return CompletionDecision(
                False,
                WorkState.VERIFYING,
                TruthClass.NOT_VERIFIED,
                ("independent_verification_required",),
            )
        if not worker_id.strip():
            return CompletionDecision(
                False,
                WorkState.BLOCKED,
                TruthClass.NOT_VERIFIED,
                ("worker_identity_required",),
            )
        return CompletionDecision(True, WorkState.COMPLETE, TruthClass.VERIFIED, ())


class NotificationFilter:
    """Only surface meaningful worker-pool changes to the human owner."""

    IMPORTANT_EVENTS = {"BLOCKER", "RESULT", "COMPLETE", "SECURITY_FINDING"}

    @classmethod
    def should_notify(cls, event: NotificationEvent) -> bool:
        return (
            event.priority in {WorkPriority.P0, WorkPriority.P1}
            or event.security_finding
            or event.test_failed
            or event.human_approval_required
            or event.evidence_ready
            or (event.state_changed and event.event_type in cls.IMPORTANT_EVENTS)
        )
