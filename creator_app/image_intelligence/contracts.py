"""Typed contracts for image-derived intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ClaimKind(StrEnum):
    FACT = "fact"
    TOOL = "tool"
    WORKFLOW = "workflow"
    METRIC = "metric"
    PROMPT_PATTERN = "prompt_pattern"
    PRIVACY = "privacy"
    PRODUCT = "product"
    PRICING = "pricing"
    CAPABILITY = "capability"
    OTHER = "other"


class CandidateDecision(StrEnum):
    REUSE = "reuse"
    DUPLICATE = "duplicate"
    VERIFY = "verify"
    BENCHMARK = "benchmark"
    DEV_CANDIDATE = "dev_candidate"
    QUARANTINE = "quarantine"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ImageAssetRef:
    asset_id: str
    sha256: str
    source_ref: str
    media_type: str = "image"
    collection: str = ""
    sequence: int | None = None

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise ValueError("asset_id must not be empty")
        if len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256
        ):
            raise ValueError("sha256 must be lowercase SHA-256 hex")
        if not self.source_ref.strip():
            raise ValueError("source_ref must not be empty")


@dataclass(frozen=True, slots=True)
class ExtractedClaim:
    text: str
    kind: ClaimKind
    confidence: float
    source_asset_id: str
    requires_external_verification: bool = True
    vendor_or_entity: str = ""
    numeric_claim: bool = False
    freshness_sensitive: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("claim text must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not self.source_asset_id.strip():
            raise ValueError("source_asset_id must not be empty")


@dataclass(frozen=True, slots=True)
class ImageInsight:
    asset: ImageAssetRef
    summary: str
    claims: tuple[ExtractedClaim, ...] = ()
    tags: tuple[str, ...] = ()
    extracted_text_digest: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("summary must not be empty")
        if self.extracted_text_digest is not None:
            value = self.extracted_text_digest
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise ValueError(
                    "extracted_text_digest must be lowercase SHA-256 hex"
                )


@dataclass(frozen=True, slots=True)
class CapabilityCandidate:
    candidate_id: str
    title: str
    description: str
    source_assets: tuple[str, ...]
    decision: CandidateDecision
    evidence_needed: tuple[str, ...] = ()
    existing_capability_refs: tuple[str, ...] = ()
    benchmark_required: bool = True
    security_review_required: bool = True
    human_review_required: bool = True
    production_effect: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be empty")
        if not self.title.strip() or not self.description.strip():
            raise ValueError("candidate title and description must not be empty")
        if self.production_effect:
            raise ValueError(
                "image-derived development candidates cannot affect production"
            )
