from creator_app.image_intelligence import (
    CandidateDecision,
    CapabilityGap,
    ClaimKind,
    ContentClaim,
    ContentEvidenceState,
    ContentIntelligencePipeline,
    ContentRecord,
)


def _record(*, claims=()) -> ContentRecord:
    return ContentRecord(
        source_id="pin-560979697359859828",
        source_url="https://www.pinterest.com/pin/560979697359859828/",
        title="Best websites for computer science and AI courses",
        description="Digital tools and AI learning resources",
        headings=("Computer learning course",),
        keywords=("AI courses", "digital tools", "computer science"),
        entities=("NVIDIA",),
        architecture_patterns=("multi-agent orchestration",),
        concepts=("AI governance evidence",),
        claims=claims,
        evidence_state=ContentEvidenceState.CONTENT_EXTRACTED,
    )


def test_research_queries_preserve_full_phrases_and_deduplicate() -> None:
    record = _record()
    queries = ContentIntelligencePipeline().research_queries(record)
    values = [item.query for item in queries]
    assert "Best websites for computer science and AI courses" in values
    assert "Computer learning course" in values
    assert "multi-agent orchestration architecture" in values
    assert len(values) == len({value.casefold() for value in values})


def test_pricing_or_vendor_claim_requires_verification() -> None:
    claim = ContentClaim(
        text="Tool X is free forever",
        kind=ClaimKind.PRICING,
        source_id="pin-560979697359859828",
        requires_external_verification=False,
        vendor_or_entity="Tool X",
    )
    assert (
        ContentIntelligencePipeline().decision_for_claim(claim)
        == CandidateDecision.VERIFY
    )


def test_unverified_capability_can_only_be_development_candidate() -> None:
    claim = ContentClaim(
        text="Evidence-aware provider routing",
        kind=ClaimKind.CAPABILITY,
        source_id="pin-560979697359859828",
        requires_external_verification=False,
    )
    record = _record(claims=(claim,))
    gap = ContentIntelligencePipeline().gap_from_claim(
        record,
        claim,
        priority="P1",
    )
    assert isinstance(gap, CapabilityGap)
    assert gap.decision == CandidateDecision.DEV_CANDIDATE
    assert gap.production_effect is False
    assert gap.security_review_required is True
    assert gap.human_review_required is True


def test_external_verification_flag_is_fail_closed() -> None:
    claim = ContentClaim(
        text="Vendor X provides audit-ready attestation",
        kind=ClaimKind.CAPABILITY,
        source_id="pin-560979697359859828",
        requires_external_verification=True,
    )
    assert (
        ContentIntelligencePipeline().decision_for_claim(claim)
        == CandidateDecision.VERIFY
    )


def test_content_record_rejects_claim_from_another_source() -> None:
    claim = ContentClaim(
        text="Mismatched source",
        kind=ClaimKind.WORKFLOW,
        source_id="pin-other",
        requires_external_verification=False,
    )
    try:
        _record(claims=(claim,))
    except ValueError as exc:
        assert "source_id" in str(exc)
    else:
        raise AssertionError("mismatched provenance must fail closed")


def test_reuse_wins_over_development_candidate() -> None:
    claim = ContentClaim(
        text="Existing CK-NEXUS workflow",
        kind=ClaimKind.CAPABILITY,
        source_id="pin-560979697359859828",
        requires_external_verification=False,
    )
    assert (
        ContentIntelligencePipeline().decision_for_claim(
            claim,
            reusable_existing_capability=True,
        )
        == CandidateDecision.REUSE
    )
