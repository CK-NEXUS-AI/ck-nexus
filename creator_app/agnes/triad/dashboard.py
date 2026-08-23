from __future__ import annotations

from dataclasses import dataclass

from .artifacts import CandidateArtifact, ClaimState
from .events import TriadEventBus, TriadRole
from .metrics import TriadMetrics


@dataclass(frozen=True, slots=True)
class TriadDashboardState:
    cycle_id: str
    builder_events: int
    critic_events: int
    evaluator_events: int
    governor_events: int
    candidates: int
    measured_not_verified: int
    verified: int
    rejected: int
    evidence_gain: int
    progress_score: float
    loop_risk: str


class TriadDashboardProjector:
    def project(
        self,
        *,
        cycle_id: str,
        event_bus: TriadEventBus,
        candidates: list[CandidateArtifact],
        metrics: TriadMetrics,
    ) -> TriadDashboardState:
        events = event_bus.by_cycle(cycle_id)
        role_counts = {role: 0 for role in TriadRole}
        for event in events:
            role_counts[event.actor] += 1

        return TriadDashboardState(
            cycle_id=cycle_id,
            builder_events=role_counts[TriadRole.BUILDER],
            critic_events=role_counts[TriadRole.CRITIC],
            evaluator_events=role_counts[TriadRole.EVALUATOR],
            governor_events=role_counts[TriadRole.GOVERNOR],
            candidates=len(candidates),
            measured_not_verified=sum(c.state is ClaimState.MEASURED_NOT_VERIFIED for c in candidates),
            verified=sum(c.state is ClaimState.VERIFIED for c in candidates),
            rejected=sum(c.state is ClaimState.REJECTED for c in candidates),
            evidence_gain=metrics.evidence_gain,
            progress_score=metrics.progress_score,
            loop_risk=metrics.loop_risk,
        )
