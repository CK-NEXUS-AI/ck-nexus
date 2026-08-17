from datetime import datetime, timedelta, timezone
import pytest

from backend.claims import compile_public_claims, production_ready
from backend.connectors import IllegalConnectorTransition, transition
from backend.evidence import AppendOnlyEvidenceStore, EvidenceConflict, can_relabel_verification, same_subject
from backend.execution import ExecutionDenied, authorize_execution
from backend.models import (
    ApprovalDecision, ApprovalRecord, CapabilityLease, ConnectorRecord, ConnectorState,
    EvidenceRecord, EvidenceStatus, ExecutionEnvelope, ReleaseSnapshot, ReversibilityClass,
    VerificationLevel,
)
from backend.verifier import verify_effects

NOW = datetime.now(timezone.utc)


def make_evidence(eid="e1", control="Q10", subject="s1", status=EvidenceStatus.PASS, stale_after=None, supersedes=None):
    return EvidenceRecord(
        evidence_id=eid, subject=subject, source_commit="c", tree_sha="t", environment="local",
        verification_level=VerificationLevel.LOCAL, control_id=control, status=status,
        observed_at=NOW, stale_after=stale_after, supersedes=supersedes,
    )


def test_evidence_is_append_only_and_unique():
    store = AppendOnlyEvidenceStore()
    store.append(make_evidence())
    with pytest.raises(EvidenceConflict):
        store.append(make_evidence())


def test_expired_evidence_fails_closed():
    store = AppendOnlyEvidenceStore()
    store.append(make_evidence(stale_after=NOW + timedelta(seconds=1)))
    current = store.current("Q10", now=NOW + timedelta(seconds=2))
    assert current and current.status is EvidenceStatus.EXPIRED


def test_verification_level_cannot_be_relabel_promoted():
    assert can_relabel_verification(VerificationLevel.LOCAL, VerificationLevel.LOCAL)
    assert not can_relabel_verification(VerificationLevel.LOCAL, VerificationLevel.STAGING)
    assert not can_relabel_verification(VerificationLevel.STAGING, VerificationLevel.PRODUCTION)


def test_subject_reconciliation():
    assert same_subject((make_evidence("e1"), make_evidence("e2")))
    assert not same_subject((make_evidence("e1", subject="s1"), make_evidence("e2", subject="s2")))


def test_connector_cannot_fake_activation():
    record = ConnectorRecord(connector_id="github", name="GitHub", protocol="OAuth2", updated_at=NOW)
    record = transition(record, ConnectorState.DISCOVERED)
    record = transition(record, ConnectorState.INSPECTED)
    record = transition(record, ConnectorState.SCANNED)
    record = transition(record, ConnectorState.PENDING_AUTH)
    with pytest.raises(IllegalConnectorTransition):
        transition(record, ConnectorState.ACTIVE_READONLY)
    ro = transition(record, ConnectorState.ACTIVE_READONLY, evidence_id="oauth-e1", credential_ref="secret://github")
    with pytest.raises(IllegalConnectorTransition):
        transition(ro, ConnectorState.ACTIVE_READWRITE, evidence_id="oauth-e2", credential_ref="secret://github")


def test_connector_write_needs_approval():
    record = ConnectorRecord(
        connector_id="github", name="GitHub", protocol="OAuth2", updated_at=NOW,
        state=ConnectorState.ACTIVE_READONLY, activation="READ_ONLY", credential_ref="secret://github", last_evidence_id="e1"
    )
    rw = transition(record, ConnectorState.ACTIVE_READWRITE, evidence_id="e2", credential_ref="secret://github", approval_id="a1")
    assert rw.state is ConnectorState.ACTIVE_READWRITE


def test_production_claims_fail_closed():
    snap = ReleaseSnapshot(subject="s")
    claims = compile_public_claims(snap)
    assert claims["production_classification"] == "NO_GO"
    assert "Production Ready" in claims["blocked_claims"]
    assert not production_ready(snap)


def test_production_claims_only_when_all_conditions_hold():
    snap = ReleaseSnapshot(
        subject="s", q10=EvidenceStatus.PASS, q11=EvidenceStatus.PASS, q12=EvidenceStatus.PASS,
        reconciliation=EvidenceStatus.PASS, final_package_success=True, artifact_checksum_verified=True
    )
    assert production_ready(snap)


def test_execution_high_risk_requires_approval():
    lease = CapabilityLease(
        lease_id="l1", subject_agent="agent", tenant="t", allowed_actions=("issue.close",),
        resource_scope=("github://repo/issues",), issued_at=NOW - timedelta(minutes=1), expires_at=NOW + timedelta(minutes=10)
    )
    env = ExecutionEnvelope(
        execution_id="x", tenant="t", principal="human", agent_id="agent", action="issue.close",
        resource="github://repo/issues/19", tool_id="github", subject="s", policy_hash="p",
        reversibility=ReversibilityClass.R3_EXTERNAL_WRITE, capability_lease_id="l1", approval_id="a1", created_at=NOW
    )
    with pytest.raises(ExecutionDenied):
        authorize_execution(env, lease, None)
    approval = ApprovalRecord(
        approval_id="a1", tenant="t", principal="human", action="issue.close", resource="github://repo/issues/19",
        reversibility=ReversibilityClass.R3_EXTERNAL_WRITE, decision=ApprovalDecision.APPROVED,
        created_at=NOW - timedelta(minutes=1), expires_at=NOW + timedelta(minutes=5), decided_at=NOW
    )
    authorize_execution(env, lease, approval)


def test_verifier_detects_false_completion():
    result = verify_effects(("issue.closed", "comment.created"), ("comment.created",))
    assert not result.passed
    assert result.missing_effects == ("issue.closed",)
