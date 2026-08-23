from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable


class AdmissionStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    IDENTITY_CHECKED = "IDENTITY_CHECKED"
    PROVENANCE_CHECKED = "PROVENANCE_CHECKED"
    LICENSE_CHECKED = "LICENSE_CHECKED"
    COST_CHECKED = "COST_CHECKED"
    PRIVACY_CHECKED = "PRIVACY_CHECKED"
    QUARANTINED = "QUARANTINED"
    SANDBOX_TESTED = "SANDBOX_TESTED"
    VERIFIED = "VERIFIED"
    APPROVED = "APPROVED"
    CONNECTED = "CONNECTED"
    REJECTED = "REJECTED"


class CandidateClass(str, Enum):
    AUTO_SAFE_RESEARCH = "AUTO_SAFE_RESEARCH"
    LOCAL_EVALUATE = "LOCAL_EVALUATE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PAID_OR_UNKNOWN_COST = "PAID_OR_UNKNOWN_COST"
    REJECT = "REJECT"


@dataclass(frozen=True)
class MCPServerCandidate:
    name: str
    version: str | None
    publisher_namespace: str
    source_repository: str | None
    package_type: str | None
    package_identifier: str | None
    license_id: str | None
    publisher_identity_verified: bool
    source_provenance_verified: bool
    license_verified: bool
    cost_known_free: bool
    cost_known_paid: bool
    privacy_reviewed: bool
    data_leaves_ck_boundary: bool
    requests_write_capability: bool
    requests_credentials: bool
    auto_install_requested: bool = False
    registry_deleted: bool = False


@dataclass(frozen=True)
class AdmissionAssessment:
    stage: AdmissionStage
    classification: CandidateClass
    activation_allowed: bool
    reasons: tuple[str, ...]
    candidate_digest: str


class MCPAdmissionController:
    """Deterministic, network-free admission policy for discovered MCP servers.

    This controller never installs, connects, executes, or authenticates to a server.
    It evaluates supplied evidence only. External activation remains a separate CK-NEXUS
    approval/execution concern.
    """

    def assess(self, candidate: MCPServerCandidate) -> AdmissionAssessment:
        reasons: list[str] = []
        digest = self._digest(candidate)

        if candidate.registry_deleted:
            return self._reject(digest, "registry_entry_deleted")
        if candidate.auto_install_requested:
            return self._reject(digest, "automatic_installation_forbidden")
        if not candidate.name or not candidate.publisher_namespace:
            return self._reject(digest, "identity_metadata_missing")

        stage = AdmissionStage.DISCOVERED
        if not candidate.publisher_identity_verified:
            reasons.append("publisher_identity_unverified")
            return AdmissionAssessment(
                stage=stage,
                classification=CandidateClass.AUTO_SAFE_RESEARCH,
                activation_allowed=False,
                reasons=tuple(reasons),
                candidate_digest=digest,
            )

        stage = AdmissionStage.IDENTITY_CHECKED
        if not candidate.source_repository or not candidate.source_provenance_verified:
            reasons.append("source_provenance_unverified")
            return AdmissionAssessment(
                stage=stage,
                classification=CandidateClass.LOCAL_EVALUATE,
                activation_allowed=False,
                reasons=tuple(reasons),
                candidate_digest=digest,
            )

        stage = AdmissionStage.PROVENANCE_CHECKED
        if not candidate.license_id or not candidate.license_verified:
            reasons.append("license_unverified")
            return AdmissionAssessment(
                stage=stage,
                classification=CandidateClass.APPROVAL_REQUIRED,
                activation_allowed=False,
                reasons=tuple(reasons),
                candidate_digest=digest,
            )

        stage = AdmissionStage.LICENSE_CHECKED
        if candidate.cost_known_paid or not candidate.cost_known_free:
            reasons.append("paid_or_unknown_cost")
            return AdmissionAssessment(
                stage=stage,
                classification=CandidateClass.PAID_OR_UNKNOWN_COST,
                activation_allowed=False,
                reasons=tuple(reasons),
                candidate_digest=digest,
            )

        stage = AdmissionStage.COST_CHECKED
        if not candidate.privacy_reviewed:
            reasons.append("privacy_review_required")
            return AdmissionAssessment(
                stage=stage,
                classification=CandidateClass.APPROVAL_REQUIRED,
                activation_allowed=False,
                reasons=tuple(reasons),
                candidate_digest=digest,
            )

        stage = AdmissionStage.PRIVACY_CHECKED
        if candidate.data_leaves_ck_boundary:
            reasons.append("external_data_transfer_requires_approval")
        if candidate.requests_write_capability:
            reasons.append("write_capability_requires_approval")
        if candidate.requests_credentials:
            reasons.append("credential_scope_requires_broker_review")

        if reasons:
            return AdmissionAssessment(
                stage=AdmissionStage.QUARANTINED,
                classification=CandidateClass.APPROVAL_REQUIRED,
                activation_allowed=False,
                reasons=tuple(reasons),
                candidate_digest=digest,
            )

        return AdmissionAssessment(
            stage=AdmissionStage.QUARANTINED,
            classification=CandidateClass.LOCAL_EVALUATE,
            activation_allowed=False,
            reasons=("sandbox_verification_required_before_activation",),
            candidate_digest=digest,
        )

    @staticmethod
    def can_advance(current: AdmissionStage, target: AdmissionStage) -> bool:
        order: Iterable[AdmissionStage] = (
            AdmissionStage.DISCOVERED,
            AdmissionStage.IDENTITY_CHECKED,
            AdmissionStage.PROVENANCE_CHECKED,
            AdmissionStage.LICENSE_CHECKED,
            AdmissionStage.COST_CHECKED,
            AdmissionStage.PRIVACY_CHECKED,
            AdmissionStage.QUARANTINED,
            AdmissionStage.SANDBOX_TESTED,
            AdmissionStage.VERIFIED,
            AdmissionStage.APPROVED,
            AdmissionStage.CONNECTED,
        )
        positions = {stage: index for index, stage in enumerate(order)}
        if current not in positions or target not in positions:
            return False
        return positions[target] == positions[current] + 1

    @staticmethod
    def _digest(candidate: MCPServerCandidate) -> str:
        payload = json.dumps(
            asdict(candidate), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    @staticmethod
    def _reject(digest: str, reason: str) -> AdmissionAssessment:
        return AdmissionAssessment(
            stage=AdmissionStage.REJECTED,
            classification=CandidateClass.REJECT,
            activation_allowed=False,
            reasons=(reason,),
            candidate_digest=digest,
        )
