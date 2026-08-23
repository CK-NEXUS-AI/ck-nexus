from datetime import datetime, timedelta, timezone

import pytest

from creator_app.agnes.runtime import (
    DurableRun,
    DurableRunState,
    ExecutionReceipt,
    MemoryQualityEntry,
    MemoryQualityStatus,
    SandboxSession,
    SandboxSessionState,
    VerificationState,
    WorkloadIdentity,
)


def test_durable_checkpoint_restore_round_trip() -> None:
    run = DurableRun("run-1")
    run.start()
    checkpoint = run.advance({"step": "a", "value": 1})
    run.advance({"value": 2})
    run.restore(checkpoint)
    assert run.state is DurableRunState.PAUSED
    assert run.logical_state == {"step": "a", "value": 1}


def test_sandbox_lifecycle_is_explicit() -> None:
    session = SandboxSession("sb-1", "container", "strict")
    session.activate()
    snap = session.snapshot({"cwd": "/workspace"})
    assert snap
    session.pause()
    assert session.state is SandboxSessionState.PAUSED
    session.activate()
    session.stop()
    assert session.state is SandboxSessionState.STOPPED


def test_workload_identity_digest_binds_attestation() -> None:
    plain = WorkloadIdentity("subject", "node", 12, "python", ("read",))
    attested = WorkloadIdentity("subject", "node", 12, "python", ("read",), "evd123")
    assert not plain.attested
    assert attested.attested
    assert plain.identity_digest != attested.identity_digest


def test_memory_quality_detects_stale_and_contradicted() -> None:
    now = datetime.now(timezone.utc)
    stale = MemoryQualityEntry("m1", now - timedelta(days=2), "src", now - timedelta(days=1), verified_by="v")
    assert stale.status(now) is MemoryQualityStatus.STALE
    contradicted = MemoryQualityEntry("m2", now, "src", contradictory_with=["m1"], verified_by="v")
    assert contradicted.status(now) is MemoryQualityStatus.CONTRADICTED


def test_execution_receipt_cannot_self_verify() -> None:
    receipt = ExecutionReceipt("e1", "subject", "builder", "evidence")
    assert receipt.verification_state is VerificationState.MEASURED_NOT_VERIFIED
    with pytest.raises(ValueError):
        receipt.attach_independent_verification("builder", "verify-evidence")
    receipt.attach_independent_verification("independent-verifier", "verify-evidence")
    assert receipt.verification_state is VerificationState.VERIFIED
