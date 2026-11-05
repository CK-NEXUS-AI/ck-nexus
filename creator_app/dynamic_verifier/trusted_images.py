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
            "ghcr.io/ck-nexus-ai/ck-nexus-verifier-python@sha256:"
            "fee488944575873dd7e1e42e355f5272953cba8bf6342e9ea043f8e257c1d60c"
        ),
        source_commit="942ef54229b5e46334820a94affa09ca14110820",
        discovery_run_id=41941102071,
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
