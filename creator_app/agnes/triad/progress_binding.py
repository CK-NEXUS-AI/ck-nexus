from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_app.agnes.runtime.progress_guard import (
    NoProgressGuard,
    ProgressDecision,
    ProgressSample,
)


@dataclass(slots=True)
class TriadProgressBinding:
    """Bind Triad cycle progress to the existing runtime no-progress guard.

    This adapter observes deterministic state/action digests only. It never
    authorizes recovery or performs execution side effects.
    """

    guard: NoProgressGuard

    def observe(
        self,
        *,
        step_index: int,
        state: dict[str, Any],
        action: dict[str, Any],
    ) -> ProgressDecision:
        sample = ProgressSample.create(step_index, state, action)
        return self.guard.observe(sample)

    def reset(self) -> None:
        self.guard.reset()
