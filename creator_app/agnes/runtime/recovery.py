from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .durable import DurableRun, DurableRunState
from .execution_receipt import ExecutionReceipt
from .persistence import DurableCheckpointStore
from .progress_guard import NoProgressGuard, ProgressDecision, ProgressSample


@dataclass(frozen=True, slots=True)
class RecoveryObservation:
    decision: ProgressDecision
    run_id: str
    step_index: int
    state_digest: str
    action_digest: str

    @property
    def evidence_digest(self) -> str:
        payload = {
            "decision": self.decision.value,
            "run_id": self.run_id,
            "step_index": self.step_index,
            "state_digest": self.state_digest,
            "action_digest": self.action_digest,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(slots=True)
class GovernedRecoveryCoordinator:
    """Coordinates recovery evidence without authorizing external mutation.

    The coordinator may restore local durable state and produce a measured
    receipt. It never self-verifies and never executes compensating actions.
    """

    store: DurableCheckpointStore
    guard: NoProgressGuard

    def restore_latest(self, run: DurableRun) -> bool:
        checkpoint = self.store.load(run.run_id)
        if checkpoint is None:
            return False
        run.restore(checkpoint)
        return True

    def observe(self, run: DurableRun, action: dict[str, Any]) -> RecoveryObservation:
        sample = ProgressSample.create(run.step_index, run.logical_state, action)
        decision = self.guard.observe(sample)
        if decision is ProgressDecision.CIRCUIT_BREAK and run.state is DurableRunState.RUNNING:
            run.pause()
        return RecoveryObservation(
            decision=decision,
            run_id=run.run_id,
            step_index=sample.step_index,
            state_digest=sample.state_digest,
            action_digest=sample.action_digest,
        )

    @staticmethod
    def measured_receipt(
        observation: RecoveryObservation,
        *,
        subject: str,
        producer_id: str,
    ) -> ExecutionReceipt:
        return ExecutionReceipt(
            execution_id=f"recovery:{observation.run_id}:{observation.step_index}",
            subject=subject,
            producer_id=producer_id,
            evidence_digest=observation.evidence_digest,
        )
