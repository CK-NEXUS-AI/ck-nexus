from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from contracts.governance.capability_lease import Budget, CapabilityLease
from contracts.governance.authority_snapshot import AuthoritySnapshot, BudgetSnapshot
from contracts.execution.sandbox import ExecutionSpec, ResourceLimits
from contracts.evidence.evidence_event import EvidenceEvent


NOW = datetime.now(timezone.utc)
DIGEST = "sha256:" + "a" * 64


def lease(**kwargs):
    return CapabilityLease(
        lease_id=uuid4(), tenant_id="tenant", principal_id="principal",
        capability="sandbox.execute.python", resource="oci:" + DIGEST,
        budgets=Budget(max_calls=2, max_mutations=0, max_cost_usd=Decimal("0.10"),
                       max_cpu_ms=1000, max_memory_mb=256, max_wall_ms=5000),
        issued_at=NOW, expires_at=kwargs.pop("expires_at", None), **kwargs,
    )


def test_expired_lease_is_inactive():
    l = lease(expires_at=NOW + timedelta(seconds=1))
    assert l.active(NOW) is True
    assert l.active(NOW + timedelta(seconds=1)) is False


def test_revoked_lease_is_inactive():
    l = lease(revoked_at=NOW + timedelta(seconds=1))
    assert l.active(NOW) is True
    assert l.active(NOW + timedelta(seconds=1)) is False


def test_budget_ceiling_is_enforced():
    l = lease()
    assert l.within_budget(calls=2, cost_usd=Decimal("0.10"))
    assert not l.within_budget(calls=3)
    assert not l.within_budget(mutations=1)


def test_sandbox_requires_digest_and_safe_defaults():
    spec = ExecutionSpec(
        spec_id="spec", run_id="run", execution_id="exec", lease_id="lease",
        language="python", runtime_version="3.12", image_digest=DIGEST,
        source_artifact_hash=DIGEST, command=("python", "/input/main.py"),
        limits=ResourceLimits(timeout_ms=1000, memory_mb=128, cpu_ms=500,
                               pids_max=16, output_bytes_max=1024),
    )
    assert spec.network_policy == "deny_all"
    assert spec.security.no_new_privileges is True
    assert spec.security.cap_drop == ("ALL",)
    assert spec.filesystem_policy.root == "read_only"


def test_invalid_digest_rejected():
    with pytest.raises(ValidationError):
        ExecutionSpec(
            spec_id="s", run_id="r", execution_id="e", lease_id="l",
            language="python", runtime_version="3.12", image_digest="latest",
            source_artifact_hash=DIGEST, command=("python", "x"),
            limits=ResourceLimits(timeout_ms=1, memory_mb=1, cpu_ms=1,
                                   pids_max=1, output_bytes_max=1),
        )


def test_authority_snapshot_is_immutable():
    snap = AuthoritySnapshot(
        lease=lease(), policy_decision={"allow": True}, sandbox_policy={"network": "deny_all"},
        budget_remaining=BudgetSnapshot(remaining_calls=2, remaining_mutations=0,
                                        remaining_cost_usd=Decimal("0.10"), remaining_cpu_ms=1000,
                                        remaining_memory_mb=256), authorized_at=NOW,
        snapshot_hash=DIGEST,
    )
    with pytest.raises(ValidationError):
        snap.snapshot_hash = "changed"  # type: ignore[misc]


def test_evidence_requires_correlated_execution_identity():
    event = EvidenceEvent(
        event_id="evt", run_id="run", execution_id="exec", correlation_id="corr",
        attempt=0, event_type="authorized", content_hash=DIGEST,
        occurred_at=NOW,
    )
    assert event.run_id == "run"
