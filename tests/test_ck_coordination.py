from __future__ import annotations

import pytest

from creator_app.ai_team.ck_coordination import (
    CKRole,
    CandidateReport,
    CoordinationPolicy,
    CoordinationState,
    ReportResult,
    WorkPacket,
    build_ck_v3_packet,
)


def _packet() -> WorkPacket:
    return build_ck_v3_packet(
        task_id="CK3-001",
        target="repo:main",
        objective="Prepare a bounded development proposal.",
        source_commit="a" * 40,
        allowed_actions=("read source", "run tests", "prepare candidate report"),
        expected_evidence=("exact source commit", "test result"),
    )


def _report(*, risks: tuple[str, ...] = ()) -> CandidateReport:
    return CandidateReport(
        task_id="CK3-001",
        role=CKRole.CK_V3,
        observed=("source inspected",),
        actions=("tests executed",),
        evidence=("run:123",),
        risks=risks,
        result=ReportResult.PASS_CANDIDATE,
        source_commit="a" * 40,
    )


def test_ck_v3_packet_has_hard_non_authority_boundaries() -> None:
    packet = _packet()

    assert packet.assignee is CKRole.CK_V3
    assert packet.production_mutation is False
    assert packet.credential_access is False
    assert packet.external_write is False
    assert "production mutation" in packet.denied_actions
    assert "credential access/export" in packet.denied_actions


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("production_mutation", "production_mutation_not_delegable"),
        ("credential_access", "credential_access_not_delegable"),
        ("external_write", "external_write_not_delegable"),
    ],
)
def test_helper_packet_cannot_receive_authority(field: str, reason: str) -> None:
    kwargs = {
        "task_id": "CK3-002",
        "assignee": CKRole.CK_V3,
        "target": "repo:main",
        "objective": "test",
        "allowed_actions": ("read",),
        "denied_actions": (),
        "expected_evidence": ("evidence",),
        "source_commit": "a" * 40,
        "production_mutation": False,
        "credential_access": False,
        "external_write": False,
    }
    kwargs[field] = True
    packet = WorkPacket(**kwargs)

    with pytest.raises(ValueError, match=reason):
        CoordinationPolicy.validate_packet(packet)


def test_candidate_report_cannot_self_promote_without_independent_verification() -> None:
    decision = CoordinationPolicy.reconcile_report(
        packet=_packet(),
        report=_report(),
        independent_evidence_verified=False,
        current_source_commit="a" * 40,
    )

    assert decision.accepted is True
    assert decision.state is CoordinationState.DONE_CANDIDATE
    assert "independent_verification_required" in decision.reasons


def test_independently_reconciled_report_can_be_verified() -> None:
    decision = CoordinationPolicy.reconcile_report(
        packet=_packet(),
        report=_report(),
        independent_evidence_verified=True,
        current_source_commit="a" * 40,
    )

    assert decision.accepted is True
    assert decision.state is CoordinationState.VERIFIED


def test_unresolved_risk_keeps_report_candidate() -> None:
    decision = CoordinationPolicy.reconcile_report(
        packet=_packet(),
        report=_report(risks=("runtime artifact unavailable",)),
        independent_evidence_verified=True,
        current_source_commit="a" * 40,
    )

    assert decision.state is CoordinationState.DONE_CANDIDATE
    assert "unresolved_risks_present" in decision.reasons


def test_stale_source_report_is_rejected() -> None:
    decision = CoordinationPolicy.reconcile_report(
        packet=_packet(),
        report=_report(),
        independent_evidence_verified=True,
        current_source_commit="b" * 40,
    )

    assert decision.accepted is False
    assert decision.state is CoordinationState.REJECTED
    assert decision.reasons == ("stale_source_commit",)


def test_task_or_role_mismatch_is_rejected() -> None:
    wrong_role = CandidateReport(
        task_id="CK3-001",
        role=CKRole.CK_V2,
        observed=(),
        actions=(),
        evidence=("run:123",),
        risks=(),
        result=ReportResult.PASS_CANDIDATE,
        source_commit="a" * 40,
    )
    decision = CoordinationPolicy.reconcile_report(
        packet=_packet(),
        report=wrong_role,
        independent_evidence_verified=True,
        current_source_commit="a" * 40,
    )

    assert decision.accepted is False
    assert decision.reasons == ("report_role_mismatch",)
