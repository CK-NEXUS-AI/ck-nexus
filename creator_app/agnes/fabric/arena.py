"""Multi-model comparison and independent judging contracts for AGNES."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ArenaMode(StrEnum):
    SIDE_BY_SIDE = "side_by_side"
    BEST_OF_N = "best_of_n"
    CONSENSUS = "consensus"
    DISSENT = "dissent"


@dataclass(frozen=True, slots=True)
class ArenaCandidate:
    provider_id: str
    model_id: str
    output_digest: str
    latency_ms: int | None = None
    estimated_cost: float | None = None


@dataclass(frozen=True, slots=True)
class ArenaScore:
    provider_id: str
    model_id: str
    correctness: float
    relevance: float
    evidence_quality: float
    safety: float
    overall: float
    judge_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("correctness", self.correctness),
            ("relevance", self.relevance),
            ("evidence_quality", self.evidence_quality),
            ("safety", self.safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ArenaDecision:
    mode: ArenaMode
    winner_provider_id: str | None
    winner_model_id: str | None
    scores: tuple[ArenaScore, ...]
    consensus_digest: str | None = None
    disagreement_detected: bool = False
    verification_required: bool = True
