"""Exact CK-NEXUS trusted verifier image registry.

Digest pinning alone is not trust. Images enter this registry only after a source-
controlled build, isolated runtime smoke and published-digest verification.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrustedVerifierImage:
    image_ref: str
    source_commit: str
    discovery_run_id: int
    profile: str


TRUSTED_VERIFIER_IMAGES: tuple[TrustedVerifierImage, ...] = (
    TrustedVerifierImage(
        image_ref=(
            "ghcr.io/spinlnw10-art/ck-nexus-verifier-python@sha256:"
            "f495574f3076eea84467f486ee6eb3ebb0136d7e41322429eb0bc435561ad751"
        ),
        source_commit="4e7a4eb37ad332a312f236e9b83b7f72f063b74f",
        discovery_run_id=32302752416,
        profile="python_quality",
    ),
)


def trusted_verifier_image(image_ref: str, profile: str) -> TrustedVerifierImage | None:
    """Return the exact reviewed registry entry or ``None`` fail-closed."""
    return next(
        (
            item
            for item in TRUSTED_VERIFIER_IMAGES
            if item.image_ref == image_ref and item.profile == profile
        ),
        None,
    )
