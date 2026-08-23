from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .events import TriadRole
from .pulse import PulsePhase


class WorkMode(str, Enum):
    PARALLEL = "PARALLEL"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    CONSOLIDATE = "CONSOLIDATE"
    CHECKPOINT = "CHECKPOINT"
    IDLE = "IDLE"


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    role: TriadRole
    mode: WorkMode
    task: str


class TriadParallelScheduler:
    """Pure planning layer; grants no execution authority."""

    def plan(self, phase: PulsePhase, *, candidate_available: bool) -> tuple[RoleAssignment, ...]:
        if phase is PulsePhase.ACTIVE_PARALLEL:
            evaluator_mode = WorkMode.EVENT_DRIVEN if candidate_available else WorkMode.IDLE
            return (
                RoleAssignment(TriadRole.BUILDER, WorkMode.PARALLEL, "develop candidate alternatives"),
                RoleAssignment(TriadRole.CRITIC, WorkMode.PARALLEL, "challenge claims and risks"),
                RoleAssignment(TriadRole.EVALUATOR, evaluator_mode, "measure candidate evidence"),
            )
        if phase is PulsePhase.DISCOVERY_CONSOLIDATION:
            return (
                RoleAssignment(TriadRole.BUILDER, WorkMode.CONSOLIDATE, "consolidate discoveries"),
                RoleAssignment(TriadRole.CRITIC, WorkMode.CONSOLIDATE, "consolidate failure lessons"),
                RoleAssignment(TriadRole.EVALUATOR, WorkMode.CONSOLIDATE, "prepare measurement gaps"),
            )
        if phase is PulsePhase.CHECKPOINT:
            return (RoleAssignment(TriadRole.GOVERNOR, WorkMode.CHECKPOINT, "seal cycle checkpoint"),)
        return (RoleAssignment(TriadRole.GOVERNOR, WorkMode.IDLE, "wait for new governed work"),)
