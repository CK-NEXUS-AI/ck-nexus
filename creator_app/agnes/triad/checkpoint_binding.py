from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_app.agnes.runtime.durable import DurableCheckpoint, DurableRun, DurableRunState


@dataclass(slots=True)
class TriadCheckpointBinding:
    """Bind Triad cycle state to the existing durable runtime checkpoint model."""

    run: DurableRun

    def checkpoint(self, *, cycle_id: str, state: dict[str, Any]) -> DurableCheckpoint:
        if self.run.state is DurableRunState.PENDING:
            self.run.start()
        elif self.run.state is DurableRunState.PAUSED:
            self.run.start()
        if self.run.state is not DurableRunState.RUNNING:
            raise ValueError("durable run must be RUNNING")
        payload = {"triad_cycle_id": cycle_id, "triad_state": state}
        return self.run.advance(payload)

    def pause(self) -> DurableCheckpoint:
        if self.run.state is not DurableRunState.RUNNING:
            raise ValueError("durable run must be RUNNING before pause")
        return self.run.pause()

    def restore(self, checkpoint: DurableCheckpoint) -> dict[str, Any]:
        self.run.restore(checkpoint)
        state = self.run.logical_state.get("triad_state", {})
        if not isinstance(state, dict):
            raise ValueError("restored triad state is invalid")
        return dict(state)
