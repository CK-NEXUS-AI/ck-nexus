"""Bounded ensemble aggregation that cannot override CK-NEXUS safety authority."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandidateAnswer:
    worker_id: str
    output: str
    quality_score: float
    confidence: float
    safety_veto: bool = False

    def __post_init__(self) -> None:
        if not self.worker_id.strip() or not self.output.strip():
            raise ValueError("worker_id and output must not be empty")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class EnsembleResult:
    state: str
    selected_worker: str | None
    output: str | None
    aggregate_confidence: float
    veto_workers: tuple[str, ...]


def choose_candidate(candidates: tuple[CandidateAnswer, ...]) -> EnsembleResult:
    """Pick the best bounded candidate unless any independent safety veto exists."""
    if not candidates:
        raise ValueError("at least one candidate is required")
    veto_workers = tuple(sorted(item.worker_id for item in candidates if item.safety_veto))
    if veto_workers:
        return EnsembleResult(
            state="BLOCKED_SAFETY_VETO",
            selected_worker=None,
            output=None,
            aggregate_confidence=0.0,
            veto_workers=veto_workers,
        )
    ranked = sorted(
        candidates,
        key=lambda item: (-item.quality_score, -item.confidence, item.worker_id),
    )
    selected = ranked[0]
    aggregate_confidence = sum(item.confidence for item in candidates) / len(candidates)
    return EnsembleResult(
        state="SELECTED",
        selected_worker=selected.worker_id,
        output=selected.output,
        aggregate_confidence=aggregate_confidence,
        veto_workers=(),
    )
