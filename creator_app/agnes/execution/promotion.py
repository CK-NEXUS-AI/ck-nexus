from __future__ import annotations

from enum import StrEnum


class ArtifactPromotionState(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    SCANNED = "scanned"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"


_PROMOTION_TRANSITIONS = {
    ArtifactPromotionState.CANDIDATE: {ArtifactPromotionState.VERIFIED, ArtifactPromotionState.REJECTED},
    ArtifactPromotionState.VERIFIED: {ArtifactPromotionState.SCANNED, ArtifactPromotionState.REJECTED},
    ArtifactPromotionState.SCANNED: {ArtifactPromotionState.APPROVED, ArtifactPromotionState.REJECTED},
    ArtifactPromotionState.APPROVED: {ArtifactPromotionState.PROMOTED, ArtifactPromotionState.REJECTED},
    ArtifactPromotionState.PROMOTED: set(),
    ArtifactPromotionState.REJECTED: set(),
}


def can_promote(current: ArtifactPromotionState, target: ArtifactPromotionState) -> bool:
    return target in _PROMOTION_TRANSITIONS[current]


class CodePatchState(StrEnum):
    BASELINE_LOCKED = "baseline_locked"
    WORKSPACE_CREATED = "workspace_created"
    PATCH_PROPOSED = "patch_proposed"
    PATCH_APPLIED = "patch_applied"
    COMPILE = "compile"
    TEST = "test"
    SECURITY_SCAN = "security_scan"
    DIFF_REVIEW = "diff_review"
    EVIDENCE_COMPLETE = "evidence_complete"
    WAITING_APPROVAL = "waiting_approval"
    CANDIDATE_READY = "candidate_ready"
    ROLLBACK = "rollback"
    DISCARD_WORKSPACE = "discard_workspace"
