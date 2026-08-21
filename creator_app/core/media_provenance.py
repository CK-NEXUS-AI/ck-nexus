from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ProvenanceMechanism(StrEnum):
    CONTENT_CREDENTIALS = "content_credentials"
    C2PA = "c2pa"
    SYNTHID = "synthid"
    WATERMARK = "watermark"
    SIGNATURE = "signature"
    OTHER = "other"


class ProvenanceStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    INVALID = "invalid"


class MediaProvenanceReceipt(BaseModel):
    media_sha256: str
    mechanism: ProvenanceMechanism
    verifier_id: str = Field(min_length=1, max_length=128)
    verifier_version: str = Field(min_length=1, max_length=128)
    status: ProvenanceStatus
    signer_digest: str | None = None
    issuer_digest: str | None = None
    network_used: bool = False
    external_verification_approval_id: str | None = None
    evidence_ids: tuple[str, ...] = ()


class MediaProvenanceDecision(BaseModel):
    verified: bool
    reason: str
    media_sha256: str
    evidence_ids: tuple[str, ...] = ()
    production_activation_allowed: bool = False


class MediaProvenancePolicy:
    """Verify provenance receipts without treating absent markers as proof of authenticity."""

    @staticmethod
    def evaluate(receipt: MediaProvenanceReceipt) -> MediaProvenanceDecision:
        reason = "provenance_verified"
        verified = True
        if not _SHA256.fullmatch(receipt.media_sha256):
            verified = False
            reason = "media_digest_invalid"
        elif receipt.verifier_version.strip().lower() in {"latest", "main", "head"}:
            verified = False
            reason = "verifier_version_not_pinned"
        elif not receipt.evidence_ids:
            verified = False
            reason = "provenance_evidence_missing"
        elif receipt.network_used and not receipt.external_verification_approval_id:
            verified = False
            reason = "external_verification_not_approved"
        elif receipt.status != ProvenanceStatus.VERIFIED:
            verified = False
            reason = f"provenance_{receipt.status.value}"
        elif receipt.mechanism in {
            ProvenanceMechanism.CONTENT_CREDENTIALS,
            ProvenanceMechanism.C2PA,
            ProvenanceMechanism.SIGNATURE,
        } and not receipt.signer_digest:
            verified = False
            reason = "signer_identity_missing"
        return MediaProvenanceDecision(
            verified=verified,
            reason=reason,
            media_sha256=receipt.media_sha256,
            evidence_ids=receipt.evidence_ids,
            production_activation_allowed=False,
        )
