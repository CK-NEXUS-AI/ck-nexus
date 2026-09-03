from creator_app.image_intelligence import (
    CandidateDecision,
    ClaimKind,
    ExtractedClaim,
    ImageAssetRef,
    ImageInsight,
    ImageIntelligencePipeline,
    ImageIntelligencePolicy,
)


def _asset() -> ImageAssetRef:
    return ImageAssetRef(
        asset_id="pin-001",
        sha256="a" * 64,
        source_ref="user-album:pins/001",
        collection="Pins",
        sequence=1,
    )


def test_pricing_claim_must_be_verified() -> None:
    claim = ExtractedClaim(
        text="Tool X is 100% free",
        kind=ClaimKind.PRICING,
        confidence=0.9,
        source_asset_id="pin-001",
        vendor_or_entity="Tool X",
        freshness_sensitive=True,
    )
    pipeline = ImageIntelligencePipeline()
    assert pipeline.decision_for_claim(claim) == CandidateDecision.VERIFY


def test_viral_metric_must_not_auto_adopt() -> None:
    claim = ExtractedClaim(
        text="This hook increases views by 487%",
        kind=ClaimKind.METRIC,
        confidence=0.8,
        source_asset_id="pin-001",
        numeric_claim=True,
    )
    pipeline = ImageIntelligencePipeline()
    assert pipeline.decision_for_claim(claim) == CandidateDecision.VERIFY


def test_reusable_existing_capability_wins() -> None:
    claim = ExtractedClaim(
        text="Content repurposing workflow",
        kind=ClaimKind.WORKFLOW,
        confidence=0.8,
        source_asset_id="pin-001",
    )
    pipeline = ImageIntelligencePipeline()
    assert (
        pipeline.decision_for_claim(
            claim,
            reusable_existing_capability=True,
        )
        == CandidateDecision.REUSE
    )


def test_capability_only_stages_development_candidate() -> None:
    insight = ImageInsight(
        asset=_asset(),
        summary="Image suggests an analytics feedback loop.",
    )
    claim = ExtractedClaim(
        text="Creator analytics feedback loop",
        kind=ClaimKind.CAPABILITY,
        confidence=0.75,
        source_asset_id="pin-001",
        requires_external_verification=False,
    )
    candidate = ImageIntelligencePipeline().candidate_from_claim(insight, claim)
    assert candidate.decision == CandidateDecision.DEV_CANDIDATE
    assert candidate.production_effect is False
    assert candidate.human_review_required is True
    assert candidate.security_review_required is True


def test_policy_rejects_auto_merge_and_publish() -> None:
    for kwargs in ({"auto_merge": True}, {"auto_publish": True}):
        try:
            ImageIntelligencePolicy(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe automatic authority must fail closed")
