"""Fail-closed classification for image-derived CK-NEXUS candidates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .contracts import (
    CandidateDecision,
    CapabilityCandidate,
    ClaimKind,
    ExtractedClaim,
    ImageInsight,
)


@dataclass(frozen=True, slots=True)
class ImageIntelligencePolicy:
    auto_stage_development_candidate: bool = True
    auto_merge: bool = False
    auto_publish: bool = False
    require_verification_for_vendor_claims: bool = True
    require_verification_for_numeric_claims: bool = True

    def __post_init__(self) -> None:
        if self.auto_merge:
            raise ValueError("image intelligence cannot auto-merge canonical code")
        if self.auto_publish:
            raise ValueError("image intelligence cannot auto-publish externally")


class ImageIntelligencePipeline:
    """Turn normalized image observations into gated development proposals."""

    def __init__(self, policy: ImageIntelligencePolicy | None = None) -> None:
        self.policy = policy or ImageIntelligencePolicy()

    def decision_for_claim(
        self,
        claim: ExtractedClaim,
        *,
        duplicate_found: bool = False,
        reusable_existing_capability: bool = False,
    ) -> CandidateDecision:
        if reusable_existing_capability:
            return CandidateDecision.REUSE
        if duplicate_found:
            return CandidateDecision.DUPLICATE

        if claim.kind in {
            ClaimKind.FACT,
            ClaimKind.PRIVACY,
            ClaimKind.PRICING,
            ClaimKind.METRIC,
            ClaimKind.PRODUCT,
        }:
            return CandidateDecision.VERIFY

        if claim.numeric_claim and self.policy.require_verification_for_numeric_claims:
            return CandidateDecision.VERIFY
        if claim.vendor_or_entity and self.policy.require_verification_for_vendor_claims:
            return CandidateDecision.VERIFY
        if claim.freshness_sensitive:
            return CandidateDecision.VERIFY

        if claim.kind in {ClaimKind.WORKFLOW, ClaimKind.PROMPT_PATTERN}:
            return CandidateDecision.BENCHMARK

        if claim.kind == ClaimKind.CAPABILITY:
            if self.policy.auto_stage_development_candidate:
                return CandidateDecision.DEV_CANDIDATE
            return CandidateDecision.BENCHMARK

        return CandidateDecision.BENCHMARK

    def candidate_from_claim(
        self,
        insight: ImageInsight,
        claim: ExtractedClaim,
        *,
        duplicate_found: bool = False,
        reusable_existing_capability: bool = False,
        existing_capability_refs: tuple[str, ...] = (),
    ) -> CapabilityCandidate:
        decision = self.decision_for_claim(
            claim,
            duplicate_found=duplicate_found,
            reusable_existing_capability=reusable_existing_capability,
        )

        evidence: list[str] = []
        if decision == CandidateDecision.VERIFY:
            evidence.extend(("official_source", "checked_at", "source_digest"))
        if decision in {
            CandidateDecision.BENCHMARK,
            CandidateDecision.DEV_CANDIDATE,
        }:
            evidence.extend(("baseline", "delta", "benchmark_result"))
        evidence.extend(("security_review", "independent_verification"))

        material = "|".join(
            (
                insight.asset.sha256,
                claim.kind.value,
                claim.text.strip(),
            )
        ).encode("utf-8")
        candidate_id = "imgcap-" + hashlib.sha256(material).hexdigest()[:20]

        return CapabilityCandidate(
            candidate_id=candidate_id,
            title=claim.text.strip()[:120],
            description=(
                "Image-derived proposal. Treat the source image as discovery "
                "evidence, not canonical authority."
            ),
            source_assets=(insight.asset.asset_id,),
            decision=decision,
            evidence_needed=tuple(dict.fromkeys(evidence)),
            existing_capability_refs=existing_capability_refs,
            benchmark_required=decision
            not in {CandidateDecision.REUSE, CandidateDecision.DUPLICATE},
            security_review_required=True,
            human_review_required=True,
            production_effect=False,
            metadata={
                "claim_kind": claim.kind.value,
                "confidence": claim.confidence,
                "requires_external_verification": (
                    claim.requires_external_verification
                ),
                "authority_effect": "NONE",
                "release_evidence": False,
            },
        )
