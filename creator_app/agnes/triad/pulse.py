from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PulsePhase(str, Enum):
    ACTIVE_PARALLEL = "ACTIVE_PARALLEL"
    DISCOVERY_CONSOLIDATION = "DISCOVERY_CONSOLIDATION"
    CHECKPOINT = "CHECKPOINT"
    IDLE = "IDLE"


@dataclass(frozen=True, slots=True)
class PulsePlan:
    active_minutes: int = 15
    discovery_minutes: int = 20
    idle_after_empty_cycles: int = 3

    def __post_init__(self) -> None:
        if self.active_minutes <= 0 or self.discovery_minutes <= 0:
            raise ValueError("pulse durations must be positive")
        if self.idle_after_empty_cycles < 1:
            raise ValueError("idle_after_empty_cycles must be >= 1")

    @property
    def cycle_minutes(self) -> int:
        return self.active_minutes + self.discovery_minutes


@dataclass(slots=True)
class AdaptivePulseController:
    plan: PulsePlan = PulsePlan()
    empty_cycles: int = 0

    def phase_at(self, elapsed_minutes: int) -> PulsePhase:
        if elapsed_minutes < 0:
            raise ValueError("elapsed_minutes must be non-negative")
        if elapsed_minutes < self.plan.active_minutes:
            return PulsePhase.ACTIVE_PARALLEL
        if elapsed_minutes < self.plan.cycle_minutes:
            return PulsePhase.DISCOVERY_CONSOLIDATION
        if elapsed_minutes == self.plan.cycle_minutes:
            return PulsePhase.CHECKPOINT
        return PulsePhase.IDLE

    def record_cycle(self, *, progress_made: bool) -> PulsePhase:
        if progress_made:
            self.empty_cycles = 0
            return PulsePhase.ACTIVE_PARALLEL
        self.empty_cycles += 1
        if self.empty_cycles >= self.plan.idle_after_empty_cycles:
            return PulsePhase.IDLE
        return PulsePhase.DISCOVERY_CONSOLIDATION
