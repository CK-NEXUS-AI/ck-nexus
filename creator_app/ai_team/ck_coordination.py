"""Fail-closed coordination contracts for CK_v1, CK_v2, and CK_v3.

CK-NEXUS remains the authority for state, policy, permissions, and execution. The CK roles are
advisory/execution-planning roles only. Reports never self-promote into verified state without an
independent reconciliation decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CKRole(StrEnum):
    CK_V1 = "CK_v1"
    CK_V2 = "CK_v2"
    CK_V3 = "CK_v3"


class CoordinationState(StrEnum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE_CANDIDATE = "DONE_CANDIDATE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ReportResult(StrEnum):
    PASS_CANDIDATE = "PASS_CANDIDATE"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class WorkPacket:
    """One bounded task delegated by CK_v1 to a helper role."""

    task_id: str
    assignee: CKRole
    target: str
    objective: str
    allowed_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    source_commit: str | None = None
    production_mutation: bool = False
    credential_access: bool = False
    external_write: bool = False


@dataclass(frozen=True, slots=True)
class CandidateReport:
    """Untrusted helper report until CK_v1 independently reconciles it."""

    task_id: str
    role: CKRole
    observed: tuple[str, ...]
    actions: tuple[str, ...]
    evidence: tuple[str, ...]
    risks: tuple[str, ...]
    result: ReportResult
    source_commit: str | None = None


@dataclass(frozen=True, slots=True)
class CoordinationDecision:
    accepted: bool
    state: CoordinationState
    reasons: tuple[str, ...]


class CoordinationPolicy:
    """CK-NEXUS-side validation for CK helper work packets and reports."""

    @staticmethod
    def validate_packet(packet: WorkPacket) -> None:
        if not packet.task_id.strip():
            raise ValueError("task_id_required")
        if not packet.target.strip():
            raise ValueError("target_required")
        if not packet.objective.strip():
            raise ValueError("objective_required")
        if packet.assignee is CKRole.CK_V1:
            raise ValueError("helper_assignee_required")
        if not packet.expected_evidence:
            raise ValueError("expected_evidence_required")

        if packet.production_mutation:
            raise ValueError("production_mutation_not_delegable")
        if packet.credential_access:
            raise ValueError("credential_access_not_delegable")
        if packet.external_write:
            raise ValueError("external_write_not_delegable")

    @staticmethod
    def reconcile_report(
        *,
        packet: WorkPacket,
        report: CandidateReport,
        independent_evidence_verified: bool,
        current_source_commit: str | None = None,
    ) -> CoordinationDecision:
        CoordinationPolicy.validate_packet(packet)

        reasons: list[str] = []
        if report.task_id != packet.task_id:
            return CoordinationDecision(
                accepted=False,
                state=CoordinationState.REJECTED,
                reasons=("task_id_mismatch",),
            )
        if report.role is not packet.assignee:
            return CoordinationDecision(
                accepted=False,
                state=CoordinationState.REJECTED,
                reasons=("report_role_mismatch",),
            )
        if packet.source_commit and report.source_commit != packet.source_commit:
            return CoordinationDecision(
                accepted=False,
                state=CoordinationState.REJECTED,
                reasons=("source_commit_mismatch",),
            )
        if current_source_commit and report.source_commit != current_source_commit:
            return CoordinationDecision(
                accepted=False,
                state=CoordinationState.REJECTED,
                reasons=("stale_source_commit",),
            )

        if report.result is ReportResult.FAIL:
            return CoordinationDecision(
                accepted=True,
                state=CoordinationState.REJECTED,
                reasons=("helper_reported_fail",),
            )
        if report.result is ReportResult.BLOCKED:
            return CoordinationDecision(
                accepted=True,
                state=CoordinationState.BLOCKED,
                reasons=("helper_reported_blocked",),
            )

        if not report.evidence:
            reasons.append("candidate_evidence_missing")
        if report.risks:
            reasons.append("unresolved_risks_present")
        if not independent_evidence_verified:
            reasons.append("independent_verification_required")

        if reasons:
            return CoordinationDecision(
                accepted=True,
                state=CoordinationState.DONE_CANDIDATE,
                reasons=tuple(reasons),
            )

        return CoordinationDecision(
            accepted=True,
            state=CoordinationState.VERIFIED,
            reasons=("independent_evidence_reconciled",),
        )


def build_ck_v3_packet(
    *,
    task_id: str,
    target: str,
    objective: str,
    source_commit: str,
    allowed_actions: tuple[str, ...],
    expected_evidence: tuple[str, ...],
) -> WorkPacket:
    """Create a CK_v3 work packet with hard non-authority boundaries."""
    packet = WorkPacket(
        task_id=task_id,
        assignee=CKRole.CK_V3,
        target=target,
        objective=objective,
        allowed_actions=allowed_actions,
        denied_actions=(
            "production mutation",
            "credential access/export",
            "external write/deploy",
            "policy or permission override",
            "merge protected production closure work",
        ),
        expected_evidence=expected_evidence,
        source_commit=source_commit,
    )
    CoordinationPolicy.validate_packet(packet)
    return packet
