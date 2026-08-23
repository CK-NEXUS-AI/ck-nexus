from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum
from hashlib import sha256


class Priority(IntEnum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


class TriadRole(StrEnum):
    BUILDER = "BUILDER"
    CRITIC = "CRITIC"
    EVIDENCE_EVALUATOR = "EVIDENCE_EVALUATOR"


@dataclass(frozen=True, slots=True)
class WorkItem:
    work_id: str
    capability: str
    priority: Priority
    dependencies: tuple[str, ...] = ()
    reliability_gain: int = 0
    evidence_gain: int = 0
    unblock_gain: int = 0
    novelty_gain: int = 0
    risk_penalty: int = 0
    production_mutation: bool = False
    paid_or_unknown_cost: bool = False
    secret_required: bool = False
    external_write: bool = False

    def auto_safe(self) -> bool:
        return not (
            self.production_mutation
            or self.paid_or_unknown_cost
            or self.secret_required
            or self.external_write
        )


@dataclass(frozen=True, slots=True)
class TriadAssignment:
    work_id: str
    capability: str
    priority: Priority
    score: int
    roles: tuple[TriadRole, ...]
    verification_ceiling: str = "MEASURED_NOT_VERIFIED"


@dataclass(frozen=True, slots=True)
class SchedulePlan:
    subject_sha: str
    assignments: tuple[TriadAssignment, ...]
    blocked_work_ids: tuple[str, ...]
    deferred_work_ids: tuple[str, ...]
    target_min_streams: int
    target_max_streams: int
    underfilled: bool
    plan_digest: str


class TriadParallelScheduler:
    """Deterministic, bounded scheduler for AGNES Triad development workstreams.

    The scheduler selects only auto-safe work, honors dependency completion,
    prevents duplicate capability work, and never fabricates work to satisfy
    the minimum stream target. Duplicate candidates are ranked before one is
    selected, so input order cannot defeat a better candidate. Builder, Critic,
    and Evidence Evaluator are assigned together, but the evaluator cannot
    produce VERIFIED state.
    """

    def __init__(self, subject_sha: str, *, min_streams: int = 5, max_streams: int = 9) -> None:
        if not subject_sha:
            raise ValueError("subject_sha required")
        if min_streams < 1 or max_streams < min_streams:
            raise ValueError("invalid stream bounds")
        self.subject_sha = subject_sha
        self.min_streams = min_streams
        self.max_streams = max_streams

    def plan(
        self,
        work_items: tuple[WorkItem, ...],
        *,
        completed_capabilities: frozenset[str] = frozenset(),
        active_capabilities: frozenset[str] = frozenset(),
    ) -> SchedulePlan:
        blocked: list[str] = []
        deferred: list[str] = []
        candidates: list[WorkItem] = []
        seen_work_ids: set[str] = set()

        for item in work_items:
            if not item.work_id or not item.capability:
                raise ValueError("work identity missing")
            if item.work_id in seen_work_ids:
                raise ValueError(f"duplicate work_id:{item.work_id}")
            seen_work_ids.add(item.work_id)

            if not item.auto_safe():
                blocked.append(item.work_id)
                continue
            if any(dep not in completed_capabilities for dep in item.dependencies):
                blocked.append(item.work_id)
                continue
            if item.capability in completed_capabilities or item.capability in active_capabilities:
                deferred.append(item.work_id)
                continue
            candidates.append(item)

        ranked = sorted(candidates, key=self._rank_key)
        unique_ranked: list[WorkItem] = []
        selected_capabilities: set[str] = set()
        for item in ranked:
            if item.capability in selected_capabilities:
                deferred.append(item.work_id)
                continue
            selected_capabilities.add(item.capability)
            unique_ranked.append(item)

        selected = unique_ranked[: self.max_streams]
        deferred.extend(item.work_id for item in unique_ranked[self.max_streams :])

        assignments = tuple(
            TriadAssignment(
                work_id=item.work_id,
                capability=item.capability,
                priority=item.priority,
                score=self._score(item),
                roles=(
                    TriadRole.BUILDER,
                    TriadRole.CRITIC,
                    TriadRole.EVIDENCE_EVALUATOR,
                ),
            )
            for item in selected
        )
        digest = self._digest(assignments, blocked, deferred)
        return SchedulePlan(
            subject_sha=self.subject_sha,
            assignments=assignments,
            blocked_work_ids=tuple(sorted(blocked)),
            deferred_work_ids=tuple(sorted(deferred)),
            target_min_streams=self.min_streams,
            target_max_streams=self.max_streams,
            underfilled=len(assignments) < self.min_streams,
            plan_digest=digest,
        )

    @classmethod
    def _rank_key(cls, item: WorkItem) -> tuple[int, int, str, str]:
        # Priority is a hard scheduling boundary: no amount of lower-priority gain
        # may leapfrog unfinished higher-priority work. Score only ranks peers.
        return (int(item.priority), -cls._score(item), item.capability, item.work_id)

    @staticmethod
    def _score(item: WorkItem) -> int:
        priority_weight = (5 - int(item.priority)) * 100
        return (
            priority_weight
            + item.unblock_gain * 10
            + item.reliability_gain * 6
            + item.evidence_gain * 5
            + item.novelty_gain * 3
            - item.risk_penalty * 8
        )

    def _digest(
        self,
        assignments: tuple[TriadAssignment, ...],
        blocked: list[str],
        deferred: list[str],
    ) -> str:
        payload = {
            "subject_sha": self.subject_sha,
            "assignments": [asdict(item) for item in assignments],
            "blocked_work_ids": sorted(blocked),
            "deferred_work_ids": sorted(deferred),
            "target_min_streams": self.min_streams,
            "target_max_streams": self.max_streams,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()
