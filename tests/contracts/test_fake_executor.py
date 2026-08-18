from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from runtime.executor.fake import FakeExecutor

from contracts.execution.sandbox import ExecutionSpec, ResourceLimits
from contracts.governance.capability_lease import Budget, CapabilityLease


DIGEST = "sha256:" + "b" * 64
NOW = datetime.now(UTC)


def make_lease(expires_at=None):
    return CapabilityLease(
        lease_id=uuid4(),
        tenant_id="t",
        principal_id="p",
        capability="sandbox.execute.python",
        resource="oci:" + DIGEST,
        budgets=Budget(
            max_calls=1,
            max_mutations=0,
            max_cost_usd=Decimal("0.01"),
            max_cpu_ms=1000,
            max_memory_mb=128,
            max_wall_ms=1000,
        ),
        issued_at=NOW,
        expires_at=expires_at,
        idempotency_key="test-1",
    )


def make_spec():
    return ExecutionSpec(
        spec_id="s",
        run_id="r",
        execution_id="e",
        lease_id="l",
        language="python",
        runtime_version="3.12",
        image_digest=DIGEST,
        source_artifact_hash=DIGEST,
        command=("python", "/input/main.py"),
        limits=ResourceLimits(
            timeout_ms=100,
            memory_mb=64,
            cpu_ms=50,
            pids_max=8,
            output_bytes_max=512,
        ),
    )


def test_fake_executor_never_executes_host_command():
    result = FakeExecutor().execute(make_spec(), make_lease())
    assert result.status == "success"
    assert result.stdout == "FAKE_EXECUTION_ONLY"
    assert result.runner_version.startswith("fake-")


def test_fake_executor_denies_expired_lease():
    lease = make_lease(expires_at=NOW - timedelta(seconds=1))
    result = FakeExecutor().execute(make_spec(), lease)
    assert result.status == "policy_denied"
