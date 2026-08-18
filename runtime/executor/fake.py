from __future__ import annotations

from datetime import datetime, timezone

from contracts.execution.sandbox import ExecutionResult, ExecutionSpec
from contracts.governance.capability_lease import CapabilityLease


class FakeExecutor:
    """Deterministic executor used only for contract/integration tests.

    It never launches a process, touches the host filesystem, opens a network
    connection, or interprets the command. A real executor must implement the
    same boundary after the governance contracts are proven.
    """

    runner_version = "fake-0.1"

    def execute(self, spec: ExecutionSpec, lease: CapabilityLease) -> ExecutionResult:
        now = datetime.now(timezone.utc)
        if not lease.active(now):
            return ExecutionResult(
                status="policy_denied",
                cleanup_status="success",
                runner_version=self.runner_version,
                image_digest=spec.image_digest,
                policy_decision_id=spec.policy_decision_id,
            )
        if not lease.within_budget(calls=1):
            return ExecutionResult(
                status="policy_denied",
                cleanup_status="success",
                runner_version=self.runner_version,
                image_digest=spec.image_digest,
                policy_decision_id=spec.policy_decision_id,
            )
        return ExecutionResult(
            status="success",
            exit_code=0,
            stdout="FAKE_EXECUTION_ONLY",
            stdout_bytes=len("FAKE_EXECUTION_ONLY"),
            duration_ms=0,
            cleanup_status="success",
            runner_version=self.runner_version,
            image_digest=spec.image_digest,
            policy_decision_id=spec.policy_decision_id,
        )
